import hmac
from typing import Optional
from uuid import UUID
from fastapi import Depends, Header, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from ..core.config import settings
from ..core.database import get_db
from ..core.exceptions import SanctuaryException
from ..core.security import decode_access_token
from ..models.domain.user import User

security_bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decodes JWT Bearer token and yields authenticated active seeker."""
    if not credentials or not credentials.credentials:
        raise SanctuaryException(
            error_code="UNAUTHORIZED",
            message="Bearer authentication token required.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise SanctuaryException(
            error_code="INVALID_TOKEN",
            message="Bearer session invalid or expired.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError):
        raise SanctuaryException(
            error_code="INVALID_TOKEN",
            message="Bearer session invalid or expired.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    user = await db.get(User, user_id)
    if not user or user.deleted_at is not None:
        raise SanctuaryException(
            error_code="USER_NOT_FOUND",
            message="Seeker account inactive or soft-deleted.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Server-side token revocation validation (SEC-02)
    token_version = payload.get("token_version", 1)
    if isinstance(token_version, bool) or not isinstance(token_version, int) or token_version < getattr(user, "token_version", 1):
        raise SanctuaryException(
            error_code="TOKEN_REVOKED",
            message="Authentication session has been revoked. Please sign in again.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return user

async def get_superadmin(
    x_superadmin_key: Optional[str] = Header(None, alias="X-Superadmin-Key"),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> bool:
    """Authenticates superadmin via secret gate key or authenticated superadmin user session."""
    clean_key = (x_superadmin_key or "").strip()
    clean_secret = (settings.SUPERADMIN_SECRET_KEY or "").strip()
    if clean_key and clean_secret and hmac.compare_digest(clean_key, clean_secret):
        return True

    if credentials and credentials.credentials:
        try:
            user = await get_current_user(credentials=credentials, db=db)
            admin_email = (settings.ADMIN_SUPERUSER_EMAIL or settings.SUPERADMIN_EMAIL or "").strip().lower()
            if user.role == "superadmin" or (
                admin_email and user.email and user.email.strip().lower() == admin_email
            ):
                return True
        except SanctuaryException:
            pass

    raise SanctuaryException(
        error_code="SUPERADMIN_FORBIDDEN",
        message="Superadmin Sentinel clearance required.",
        status_code=status.HTTP_403_FORBIDDEN,
    )


async def get_current_superadmin(
    current_user: User = Depends(get_current_user),
) -> User:
    """RBAC Superadmin guard: asserts current_user.email matches configured admin superuser email or current_user.role == 'superadmin'.
    
    Unauthorized requests raise HTTP 403 Forbidden with error_code 'FORBIDDEN_ADMIN_ACCESS'.
    """
    admin_superuser_email = (settings.ADMIN_SUPERUSER_EMAIL or settings.SUPERADMIN_EMAIL or "").strip().lower()
    is_superadmin = (
        current_user.role == "superadmin"
        or (
            admin_superuser_email
            and current_user.email
            and current_user.email.strip().lower() == admin_superuser_email
        )
    )
    if not is_superadmin:
        raise SanctuaryException(
            error_code="FORBIDDEN_ADMIN_ACCESS",
            message="Superadmin clearance required.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return current_user


