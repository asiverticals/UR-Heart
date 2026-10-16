import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.exceptions import SanctuaryException
from ..core.security import (
    create_access_token,
    create_magic_link_token,
    create_refresh_token,
    decode_magic_link_token,
    resolve_auth_uuid,
    verify_google_id_token,
)
from ..models.domain.legal import ConsumedMagicToken, UnderageQuarantineRegistry
from ..models.domain.user import User
from ..schemas.auth import TokenResponse
from .email_service import email_service

logger = logging.getLogger(__name__)

class AuthService:
    """Authentication and identity domain service managing seeker onboarding and sessions."""

    @staticmethod
    async def record_underage_quarantine(
        device_fingerprint: str,
        dob: date,
        age: int,
        session: AsyncSession,
    ) -> UnderageQuarantineRegistry:
        """Records or extends statutory 365-day hardware quarantine idempotently."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(UnderageQuarantineRegistry)
            .where(UnderageQuarantineRegistry.device_hash == device_fingerprint)
            .limit(1)
        )
        res = await session.execute(stmt)
        record = res.scalars().first()
        if record:
            record.attempted_dob = dob
            record.quarantine_until = max(record.quarantine_until, now + timedelta(days=365))
            record.attempt_metadata = {"attempted_age": age}
        else:
            record = UnderageQuarantineRegistry(
                device_hash=device_fingerprint,
                attempted_dob=dob,
                quarantine_until=now + timedelta(days=365),
                attempt_metadata={"attempted_age": age},
            )
            session.add(record)
        await session.commit()
        return record

    @staticmethod
    async def verify_registration_eligibility(
        dob: date,
        device_fingerprint: str,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Validates 18+ age criteria and intercepts quarantined hardware fingerprints."""
        now = datetime.now(timezone.utc)

        # Check existing active quarantine
        stmt = (
            select(UnderageQuarantineRegistry)
            .where(
                UnderageQuarantineRegistry.device_hash == device_fingerprint,
                UnderageQuarantineRegistry.quarantine_until > now,
            )
            .order_by(UnderageQuarantineRegistry.quarantine_until.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        quarantined = result.scalars().first()
        if quarantined:
            raise SanctuaryException(
                error_code="UNDERAGE_QUARANTINE_TRIGGERED",
                message="Device is currently quarantined due to underage registration attempt.",
                status_code=403,
                details={"quarantine_until": quarantined.quarantine_until.isoformat()},
            )

        # Calculate exact chronological age
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            await AuthService.record_underage_quarantine(device_fingerprint, dob, age, session)
            raise SanctuaryException(
                error_code="UNDERAGE_QUARANTINE_TRIGGERED",
                message="Seeker is under the legal age threshold.",
                status_code=403,
                details={"age": age},
            )

        return {"eligible": True, "message": "Age criteria satisfied."}

    @staticmethod
    async def authenticate_google_user(
        id_token: str,
        installation_uuid: Optional[str],
        session: AsyncSession,
    ) -> TokenResponse:
        """Exchanges verified Google RS256 token claims for an authenticated Sanctuary session."""
        claims = await verify_google_id_token(id_token)
        auth_id = resolve_auth_uuid(claims["sub"])
        email = claims.get("email")

        # Authoritative lookup by Google auth_id first
        stmt = select(User).where(User.auth_id == auth_id).limit(1)
        result = await session.execute(stmt)
        user = result.scalars().first()

        # Verify email is verified before proceeding
        if not claims.get("email_verified"):
            raise SanctuaryException(
                error_code="GOOGLE_EMAIL_UNVERIFIED",
                message="Google email address has not been verified.",
                status_code=400,
            )

        # If not found by auth_id, check for pre-existing account by verified email
        if not user and email:
            stmt_email = select(User).where(User.email == email).limit(1)
            res_email = await session.execute(stmt_email)
            existing_email_user = res_email.scalars().first()
            if existing_email_user:
                user = existing_email_user
                user.auth_id = auth_id
                await session.commit()

        if not user:
            # Bootstrap initial uncompleted seeker account
            user = User(
                auth_id=auth_id,
                email=email,
                full_name=claims.get("name") or "Seeker",
                dob=date(2000, 1, 1),
                gender="Other",
                interested_in="Everyone",
                contact_bridge_type="whatsapp",
                contact_bridge_encrypted="",
                referral_code=f"SANCTUARY-{uuid.uuid4().hex[:12].upper()}",
                avatar_url=claims.get("picture"),
                is_profile_completed=False,
                last_installation_uuid=installation_uuid,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            if installation_uuid and user.last_installation_uuid != installation_uuid:
                user.last_installation_uuid = installation_uuid
                await session.commit()

        user_tv = getattr(user, "token_version", 1)
        access_token = create_access_token(user.id, token_version=user_tv)
        refresh_token = create_refresh_token(user.id, token_version=user_tv)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id,
            is_profile_completed=user.is_profile_completed,
            role=user.role,
        )

    @staticmethod
    async def send_magic_link_email(
        email: str,
        session: AsyncSession,
    ) -> bool:
        """Generates single-use cryptographic token and dispatches magic link."""
        token = create_magic_link_token(email)
        import urllib.parse
        encoded_token = urllib.parse.quote(token)
        link_url = f"https://urheart.app/auth/verify-magic?token={encoded_token}"
        dispatched = await email_service.send_magic_link(email, link_url)
        if not dispatched:
            logger.warning("Failed to dispatch magic link")
            return False
        logger.debug("Magic link dispatched.")
        return True

    @staticmethod
    async def verify_magic_link_token(
        token: str,
        session: AsyncSession,
    ) -> TokenResponse:
        """Verifies single-use magic link token and establishes active session."""
        payload = decode_magic_link_token(token)
        if not payload or not payload.get("sub"):
            raise SanctuaryException(
                error_code="INVALID_MAGIC_LINK",
                message="Magic link is invalid or has expired.",
                status_code=401,
            )

        # Enforce single-use token consumption via persistent database ledger
        jti = payload.get("jti")
        if not jti:
            raise SanctuaryException(
                error_code="INVALID_MAGIC_LINK",
                message="Magic link token missing unique identifier.",
                status_code=401,
            )

        stmt_jti = select(ConsumedMagicToken).where(ConsumedMagicToken.jti == jti).limit(1)
        res_jti = await session.execute(stmt_jti)
        if res_jti.scalars().first():
            raise SanctuaryException(
                error_code="TOKEN_ALREADY_USED",
                message="Magic link token has already been used.",
                status_code=401,
            )

        email = payload["sub"]
        auth_id = resolve_auth_uuid(email)

        # Persist consumed JTI record into database
        exp_ts = payload.get("exp")
        exp_dt = (
            datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            if exp_ts
            else datetime.now(timezone.utc) + timedelta(minutes=15)
        )
        consumed_entry = ConsumedMagicToken(
            jti=jti,
            email=email,
            expires_at=exp_dt,
        )
        session.add(consumed_entry)

        # Lookup strictly by verified unique email
        stmt = select(User).where(User.email == email).limit(1)
        result = await session.execute(stmt)
        user = result.scalars().first()

        if not user:
            user = User(
                auth_id=auth_id,
                email=email,
                full_name=email.split("@")[0].capitalize(),
                dob=date(2000, 1, 1),
                gender="Other",
                interested_in="Everyone",
                contact_bridge_type="whatsapp",
                contact_bridge_encrypted="",
                referral_code=f"SANCTUARY-{uuid.uuid4().hex[:12].upper()}",
                is_profile_completed=False,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            await session.commit()

        user_tv = getattr(user, "token_version", 1)
        access_token = create_access_token(user.id, token_version=user_tv)
        refresh_token = create_refresh_token(user.id, token_version=user_tv)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id,
            is_profile_completed=user.is_profile_completed,
            role=user.role,
        )

    @staticmethod
    async def refresh_user_token(
        refresh_token: str,
        session: AsyncSession,
    ) -> TokenResponse:
        """Validates HS256 refresh token and issues fresh access and refresh tokens."""
        import jwt
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            if payload.get("type") != "refresh":
                raise SanctuaryException(
                    error_code="INVALID_REFRESH_TOKEN",
                    message="Token is not a valid refresh token.",
                    status_code=401,
                )
            user_id_raw = payload.get("sub")
            if not user_id_raw:
                raise SanctuaryException(
                    error_code="INVALID_REFRESH_TOKEN",
                    message="Token subject missing.",
                    status_code=401,
                )
            user_id = uuid.UUID(user_id_raw)
        except (jwt.PyJWTError, ValueError):
            raise SanctuaryException(
                error_code="INVALID_REFRESH_TOKEN",
                message="Invalid or expired refresh token.",
                status_code=401,
            )

        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        res = await session.execute(stmt)
        user = res.scalars().first()
        if not user:
            raise SanctuaryException(
                error_code="SEEKER_NOT_FOUND",
                message="Seeker account associated with token not found.",
                status_code=404,
            )

        # Validate token version revocation (SEC-02, CodeRabbit Issue #1)
        token_version = payload.get("token_version", 1)
        if isinstance(token_version, bool) or not isinstance(token_version, int) or token_version < getattr(user, "token_version", 1):
            raise SanctuaryException(
                error_code="INVALID_REFRESH_TOKEN",
                message="Refresh token has been revoked.",
                status_code=401,
            )

        user_tv = getattr(user, "token_version", 1)
        new_access_token = create_access_token(user.id, token_version=user_tv)
        new_refresh_token = create_refresh_token(user.id, token_version=user_tv)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id,
            is_profile_completed=user.is_profile_completed,
            role=user.role,
        )

auth_service = AuthService()
