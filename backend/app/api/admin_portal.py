"""
UR-Heart Production Web Admin Portal & Gatekeeper Engine
FastAPI Router for Superadmin Operations at `/admin`

Exclusively accessible to `asiverticals@gmail.com`.
Complies with India DPDP Act 2023, IT Rules 2021, and BNS 2023.
"""

import hmac
import json
import logging
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

import jwt
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_db
from ..core.exceptions import SanctuaryException
from ..core.limiter import get_trusted_client_ip, limiter
from ..models.domain.admin_telemetry import (
    AdminAuditLog,
    AdminKycEscalation,
    DeviceFcmToken,
)
from ..models.domain.legal import (
    ConsentAuditLog,
    DataExportRequest,
    DataNominee,
    GrievanceDossier,
    UnderageQuarantineRegistry,
)
from ..models.domain.monetization import (
    InAppPurchase,
    PendingWebEntitlement,
)
from ..models.domain.user import User
from ..services.admin_audit_service import log_admin_action
from ..services.admin_service import AdminService
from ..services.billing_entitlement_service import billing_entitlement_service

logger = logging.getLogger("urheart.admin_portal")

router = APIRouter(tags=["AdminPortal"])

SESSION_COOKIE_NAME = "sanctuary_admin_session"
SESSION_EXPIRATION_SECONDS = 43200  # 12 hours
SUPERADMIN_EMAIL_CANONICAL = "asiverticals@gmail.com"


# ==============================================================================
# Pydantic Schemas for Admin Portal APIs
# ==============================================================================

class AdminLoginRequest(BaseModel):
    email: str = Field(..., description="Superadmin authorized email (asiverticals@gmail.com)")
    secret_key: str = Field(..., description="Superadmin secret key configured in .env")


class KycAdjudicateRequest(BaseModel):
    decision: Literal["approve", "reject"] = Field(..., description="Adjudication decision")
    notes: Optional[str] = Field(None, max_length=500, description="Optional reviewer notes")


class GrievanceResolveRequest(BaseModel):
    status: Literal["actioned", "dismissed", "investigating", "closed", "under_review", "acknowledged"] = Field(
        ..., description="Updated statutory status"
    )
    resolution_summary: Optional[str] = Field(None, max_length=2000, description="Statutory resolution notes")


class UserBanToggleRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500, description="Administrative reason for ban/unban")


class QuarantineReleaseRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500, description="Appeal justification for release")


class GrantSparksRequest(BaseModel):
    sparks_amount: int = Field(..., description="Amount of Sparks to credit (or debit if negative)")
    reason: str = Field(..., min_length=3, max_length=500, description="Mandatory reason for ledger entry")


class GrantPassRequest(BaseModel):
    sku: str = Field(..., description="SKU identifier (e.g. pass_monthly, pass_weekly, pass_infinity)")
    reason: str = Field(..., min_length=3, max_length=500, description="Mandatory reason for pass grant")


# ==============================================================================
# Cryptographic Session & Gatekeeper Helpers
# ==============================================================================

_revoked_admin_tokens: set[str] = set()

def revoke_admin_token(token_or_jti: str) -> None:
    """Blacklists an admin session token or its JTI upon logout."""
    if token_or_jti:
        _revoked_admin_tokens.add(token_or_jti.strip())

def is_admin_token_revoked(jti: Optional[str] = None, token: Optional[str] = None) -> bool:
    """Checks whether an admin session token or its JTI has been revoked."""
    if jti and jti in _revoked_admin_tokens:
        return True
    if token and token.strip() in _revoked_admin_tokens:
        return True
    return False

def create_admin_session_token(email: str, expires_seconds: int = SESSION_EXPIRATION_SECONDS) -> str:
    """Creates an HMAC-signed JWT session token for the authenticated superadmin with unique JTI."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email.strip().lower(),
        "role": "superadmin",
        "type": "admin_session",
        "jti": secrets.token_hex(16),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_seconds)).timestamp()),
    }
    secret = settings.JWT_SECRET_KEY or settings.SECRET_KEY
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_admin_session_token(token: str) -> Optional[str]:
    """Verifies HMAC-signed JWT session token, ensures asiverticals@gmail.com, and checks revocation."""
    if not token:
        return None
    try:
        secret = settings.JWT_SECRET_KEY or settings.SECRET_KEY
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        if payload.get("type") != "admin_session":
            return None
        jti = payload.get("jti")
        if is_admin_token_revoked(jti=jti, token=token):
            return None
        email = (payload.get("sub") or "").strip().lower()
        if email != SUPERADMIN_EMAIL_CANONICAL:
            return None
        return email
    except Exception:
        return None


def get_request_client_ip(request: Request) -> str:
    """Extracts true client IP honoring trusted reverse proxy headers only when originating from trusted proxy."""
    return get_trusted_client_ip(request)


async def get_current_admin(
    request: Request,
) -> str:
    """Strict Gatekeeper Dependency for all /admin/api/* endpoints.

    Authenticates via:
    1. Signed HttpOnly cookie `sanctuary_admin_session`
    2. Header `Authorization: Bearer <admin_token>`
    3. Header `X-Superadmin-Key: <SUPERADMIN_SECRET_KEY>`
    """
    # 1. Cookie check
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        email = verify_admin_session_token(cookie_token)
        if email:
            return email

    # 2. Authorization Bearer check
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        email = verify_admin_session_token(token)
        if email:
            return email

    # 3. Superadmin secret header check
    admin_key = request.headers.get("X-Superadmin-Key", "").strip()
    expected_secret = (settings.SUPERADMIN_SECRET_KEY or "").strip()
    if admin_key and expected_secret and hmac.compare_digest(admin_key, expected_secret):
        return SUPERADMIN_EMAIL_CANONICAL

    raise SanctuaryException(
        error_code="ADMIN_UNAUTHORIZED",
        message="Superadmin authentication required.",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


# ==============================================================================
# Authentication & Web Page Endpoints
# ==============================================================================

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Gatekeeper protected Admin Dashboard view.

    Unauthenticated visitors are redirected to `/admin/login` (HTTP 303).
    """
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    email = verify_admin_session_token(cookie_token) if cookie_token else None

    if not email:
        # Check header fallback for automated tooling
        admin_key = request.headers.get("X-Superadmin-Key", "").strip()
        expected_secret = (settings.SUPERADMIN_SECRET_KEY or "").strip()
        if not (admin_key and expected_secret and hmac.compare_digest(admin_key, expected_secret)):
            return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    return HTMLResponse(content=render_dashboard_html(), status_code=200)


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_view(request: Request):
    """Sanctuary Dark-Gold branded Login Portal at `/admin/login`.

    If already authenticated, redirects to `/admin`.
    """
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token and verify_admin_session_token(cookie_token):
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    return HTMLResponse(content=render_login_html(), status_code=200)


@router.post("/admin/api/login")
@limiter.limit("5/minute")
async def admin_api_login(
    request: Request,
    payload: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Strictly authenticates asiverticals@gmail.com and SUPERADMIN_SECRET_KEY from .env.

    Sets signed HttpOnly session cookie and logs an audit record.
    """
    client_ip = get_request_client_ip(request)
    email = (payload.email or "").strip().lower()
    secret_key = (payload.secret_key or "").strip()
    expected_secret = (settings.SUPERADMIN_SECRET_KEY or "").strip()

    dummy_secret = expected_secret or "dummy_secret_padding_constant_time_32_bytes"
    secret_candidate = expected_secret if expected_secret else dummy_secret

    email_bytes = email.encode("utf-8")
    canonical_email_bytes = SUPERADMIN_EMAIL_CANONICAL.encode("utf-8")
    is_valid_email = hmac.compare_digest(email_bytes, canonical_email_bytes)

    secret_bytes = secret_key.encode("utf-8")
    expected_secret_bytes = secret_candidate.encode("utf-8")
    is_valid_secret = bool(expected_secret and hmac.compare_digest(secret_bytes, expected_secret_bytes))

    # Rule 1: Exclusively asiverticals@gmail.com
    if not is_valid_email:
        await log_admin_action(
            session=db,
            admin_email=email or "unknown",
            action="admin_login_failed",
            target_type="admin_auth",
            target_id=email or "unknown",
            details={"reason": "unauthorized_email_rejected"},
            ip_address=client_ip,
        )
        await db.commit()
        raise SanctuaryException(
            error_code="INVALID_ADMIN_CREDENTIALS",
            message="Invalid administrative credentials.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Rule 2: Strictly validate secret key
    if not is_valid_secret:
        await log_admin_action(
            session=db,
            admin_email=email,
            action="admin_login_failed",
            target_type="admin_auth",
            target_id=email,
            details={"reason": "invalid_secret_key"},
            ip_address=client_ip,
        )
        await db.commit()
        raise SanctuaryException(
            error_code="INVALID_ADMIN_CREDENTIALS",
            message="Invalid administrative credentials.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Success: record audit log
    await log_admin_action(
        session=db,
        admin_email=email,
        action="admin_login_success",
        target_type="admin_auth",
        target_id=email,
        details={"status": "session_created"},
        ip_address=client_ip,
    )
    await db.commit()

    token = create_admin_session_token(email)
    response = JSONResponse(
        content={"success": True, "redirect_url": "/admin", "message": "Authentication successful."},
        status_code=200,
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_EXPIRATION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=(settings.ENVIRONMENT == "production"),
        path="/",
    )
    return response


@router.post("/admin/api/logout")
async def admin_api_logout(
    request: Request,
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Terminates active administrative session and clears HttpOnly cookie."""
    client_ip = get_request_client_ip(request)

    # Invalidate session token server-side (SEC: VULN-AUTH-01)
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    auth_header = request.headers.get("Authorization", "")
    token = cookie_token or (auth_header[7:].strip() if auth_header.startswith("Bearer ") else None)
    if token:
        try:
            secret = settings.JWT_SECRET_KEY or settings.SECRET_KEY
            payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_exp": False})
            jti = payload.get("jti")
            if jti:
                revoke_admin_token(jti)
            revoke_admin_token(token)
        except Exception:
            revoke_admin_token(token)

    await log_admin_action(
        session=db,
        admin_email=admin_email,
        action="admin_logout",
        target_type="admin_auth",
        target_id=admin_email,
        details={"status": "session_cleared"},
        ip_address=client_ip,
    )
    await db.commit()

    response = JSONResponse(
        content={"success": True, "redirect_url": "/admin/login", "message": "Logged out successfully."},
        status_code=200,
    )
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/admin/logout")
async def admin_web_logout(request: Request):
    """Convenience redirect for browser link logouts."""
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        try:
            secret = settings.JWT_SECRET_KEY or settings.SECRET_KEY
            payload = jwt.decode(cookie_token, secret, algorithms=["HS256"], options={"verify_exp": False})
            jti = payload.get("jti")
            if jti:
                revoke_admin_token(jti)
            revoke_admin_token(cookie_token)
        except Exception:
            revoke_admin_token(cookie_token)
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return response


# ==============================================================================
# Admin Backend APIs (/admin/api/*)
# ==============================================================================

@router.get("/admin/api/telemetry")
async def get_telemetry_kpis(
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Real-time system operational KPIs for Tab 1 Operations Hub."""
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    month_ago = now - timedelta(days=30)

    # 1. Total Seekers
    total_seekers = (
        await db.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None)))
    ) or 0

    # 2. DAU (last 24 hours active)
    dau = (
        await db.scalar(
            select(func.count(User.id)).where(
                User.deleted_at.is_(None),
                User.updated_at >= day_ago,
            )
        )
    ) or 0

    # 3. MAU (last 30 days active)
    mau = (
        await db.scalar(
            select(func.count(User.id)).where(
                User.deleted_at.is_(None),
                User.updated_at >= month_ago,
            )
        )
    ) or 0

    # 4. Pending KYC Escalation Queue
    pending_kyc = (
        await db.scalar(
            select(func.count(AdminKycEscalation.id)).where(AdminKycEscalation.status == "pending")
        )
    ) or 0

    # 5. 24h NCII & Emergency Takedown Tickets
    ncii_tickets = (
        await db.scalar(
            select(func.count(GrievanceDossier.id)).where(
                GrievanceDossier.violation_category.in_(["ncii", "explicit_content"]),
                GrievanceDossier.status.in_(["under_review", "acknowledged", "investigating"]),
            )
        )
    ) or 0

    # 6. 24h Completed Revenue
    revenue_24h = (
        await db.scalar(
            select(func.coalesce(func.sum(InAppPurchase.amount_gross), Decimal("0.00"))).where(
                InAppPurchase.status == "completed",
                InAppPurchase.purchased_at >= day_ago,
            )
        )
    ) or Decimal("0.00")

    # 7. Active FCM Devices
    active_fcm = (
        await db.scalar(
            select(func.count(DeviceFcmToken.id)).where(DeviceFcmToken.is_active.is_(True))
        )
    ) or 0

    return {
        "total_seekers": int(total_seekers),
        "dau": int(dau),
        "mau": int(mau),
        "pending_kyc_count": int(pending_kyc),
        "emergency_ncii_count": int(ncii_tickets),
        "revenue_24h": float(revenue_24h),
        "active_fcm_devices": int(active_fcm),
        "timestamp": now.isoformat(),
    }


@router.get("/admin/api/kyc/pending")
async def get_pending_kyc_escalations(
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lists pending KYC escalations with 15-minute presigned review URLs."""
    admin_service = AdminService()
    items = await admin_service.get_pending_escalations(db)
    return [item.model_dump() for item in items]


@router.post("/admin/api/kyc/{escalation_id}/decide")
async def decide_kyc_escalation(
    escalation_id: str,
    payload: KycAdjudicateRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Adjudicates KYC escalation (approve/reject), purges ephemeral frames, and records audit log."""
    client_ip = get_request_client_ip(request)

    # Resolve or create reviewer representation
    reviewer = await db.scalar(select(User).where(User.email == admin_email))
    if not reviewer:
        # Pseudo reviewer for superadmin if not in users table
        reviewer = User(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email=admin_email,
            full_name="Superadmin Sentinel",
            role="superadmin",
        )

    admin_service = AdminService()
    result = await admin_service.decide_escalation(
        session=db,
        escalation_id=escalation_id,
        decision=payload.decision,
        reviewer=reviewer,
        background_tasks=background_tasks,
        notes=payload.notes,
        ip_address=client_ip,
    )

    return result.model_dump()


@router.get("/admin/api/grievances")
async def list_grievances(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lists grievance dossiers sorted by statutory SLA countdown (IT Rules 2021 24h tickets first)."""
    now = datetime.now(timezone.utc)
    stmt = select(GrievanceDossier)

    if status:
        stmt = stmt.where(GrievanceDossier.status == status)
    if category:
        stmt = stmt.where(GrievanceDossier.violation_category == category)

    # Sort priority: emergency takedown tickets with non-null sla_deadline_at first, then ascending deadline
    stmt = stmt.order_by(
        case((GrievanceDossier.sla_deadline_at.isnot(None), 0), else_=1),
        GrievanceDossier.sla_deadline_at.asc(),
        GrievanceDossier.created_at.desc(),
    ).limit(limit).offset(offset)

    result = await db.execute(stmt)
    dossiers = result.scalars().all()

    items = []
    for d in dossiers:
        ref_deadline = d.sla_deadline_at or d.statutory_resolution_due_at
        if ref_deadline and ref_deadline.tzinfo is None:
            ref_deadline = ref_deadline.replace(tzinfo=timezone.utc)
        remaining_seconds = int((ref_deadline - now).total_seconds()) if ref_deadline else None

        items.append({
            "id": d.id,
            "dossier_reference_id": d.dossier_reference_id,
            "reporter_id": str(d.reporter_id) if d.reporter_id else None,
            "reported_user_id": str(d.reported_user_id) if d.reported_user_id else None,
            "violation_category": d.violation_category,
            "evidence_text": d.evidence_text,
            "statutory_notes": d.statutory_notes or "",
            "status": d.status,
            "acknowledgment_sent_at": d.acknowledgment_sent_at.isoformat() if d.acknowledgment_sent_at else None,
            "statutory_resolution_due_at": d.statutory_resolution_due_at.isoformat() if d.statutory_resolution_due_at else None,
            "sla_deadline_at": d.sla_deadline_at.isoformat() if d.sla_deadline_at else None,
            "remaining_sla_seconds": remaining_seconds,
            "resolution_summary": d.resolution_summary or "",
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "actioned_at": d.actioned_at.isoformat() if d.actioned_at else None,
            "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
        })

    return items


@router.post("/admin/api/grievances/{dossier_id}/resolve")
async def resolve_grievance(
    dossier_id: str,
    payload: GrievanceResolveRequest,
    request: Request,
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Resolves or updates grievance status, strictly validating status constraints and recording audit log."""
    client_ip = get_request_client_ip(request)
    now = datetime.now(timezone.utc)

    # Locate dossier by integer ID or dossier_reference_id
    stmt = select(GrievanceDossier)
    if dossier_id.isdigit():
        stmt = stmt.where(GrievanceDossier.id == int(dossier_id))
    else:
        stmt = stmt.where(GrievanceDossier.dossier_reference_id == dossier_id)

    dossier = await db.scalar(stmt)
    if not dossier:
        raise SanctuaryException(
            error_code="GRIEVANCE_NOT_FOUND",
            message="Grievance dossier not found.",
            status_code=404,
        )

    # Update state
    dossier.status = payload.status
    if payload.resolution_summary:
        dossier.resolution_summary = payload.resolution_summary

    if payload.status in ("actioned", "dismissed", "closed"):
        dossier.resolved_at = now
    if payload.status == "actioned":
        dossier.actioned_at = now

    # Record audit log
    await log_admin_action(
        session=db,
        admin_email=admin_email,
        action="resolve_grievance",
        target_type="grievance",
        target_id=str(dossier.id),
        details={
            "dossier_reference_id": dossier.dossier_reference_id,
            "status": payload.status,
            "resolution_summary": payload.resolution_summary or "",
        },
        ip_address=client_ip,
    )
    await db.commit()
    await db.refresh(dossier)

    return {
        "success": True,
        "dossier_reference_id": dossier.dossier_reference_id,
        "status": dossier.status,
        "resolution_summary": dossier.resolution_summary,
        "resolved_at": dossier.resolved_at.isoformat() if dossier.resolved_at else None,
    }


@router.get("/admin/api/users")
async def list_seekers(
    query: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Searches seekers by email, full name, handle, or UUID with masked contact bridge."""
    stmt = select(User)

    if status_filter == "banned":
        stmt = stmt.where(User.deleted_at.isnot(None))
    elif status_filter == "active":
        stmt = stmt.where(User.deleted_at.is_(None))

    if query:
        q = query.strip()
        conditions = [
            User.email.ilike(f"%{q}%"),
            User.full_name.ilike(f"%{q}%"),
            User.referral_code.ilike(f"%{q}%"),
        ]
        try:
            target_uuid = UUID(q)
            conditions.append(User.id == target_uuid)
        except ValueError:
            pass
        stmt = stmt.where(or_(*conditions))

    stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    users = result.scalars().all()

    items = []
    for u in users:
        items.append({
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "dob": u.dob.isoformat() if u.dob else None,
            "gender": u.gender,
            "role": u.role,
            "kyc_status": u.kyc_status,
            "subscription_tier": u.subscription_tier,
            "reward_balance": u.reward_balance or 0,
            "swipes_remaining": u.swipes_remaining or 0,
            "is_banned": u.deleted_at is not None,
            "deleted_at": u.deleted_at.isoformat() if u.deleted_at else None,
            "masked_contact_bridge": f"{u.contact_bridge_type}: [PROTECTED_AES_BRIDGE]",
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })

    return items


@router.post("/admin/api/users/{user_id}/toggle-ban")
async def toggle_user_ban(
    user_id: UUID,
    payload: UserBanToggleRequest,
    request: Request,
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Toggles user soft-delete/ban status, increments token_version to revoke active sessions, and logs audit."""
    client_ip = get_request_client_ip(request)
    user = await db.get(User, user_id)
    if not user:
        raise SanctuaryException(
            error_code="SEEKER_NOT_FOUND",
            message="Seeker account not found.",
            status_code=404,
        )

    if user.deleted_at is None:
        user.deleted_at = datetime.now(timezone.utc)
        user.token_version = (user.token_version or 1) + 1  # Revoke all JWT sessions
        action = "user_banned"
        is_banned = True
    else:
        user.deleted_at = None
        action = "user_unbanned"
        is_banned = False

    await log_admin_action(
        session=db,
        admin_email=admin_email,
        action=action,
        target_type="user",
        target_id=str(user.id),
        details={"reason": payload.reason or "", "is_banned": is_banned, "token_version": user.token_version},
        ip_address=client_ip,
    )
    await db.commit()

    return {
        "success": True,
        "user_id": str(user.id),
        "is_banned": is_banned,
        "action": action,
        "token_version": user.token_version,
    }


@router.get("/admin/api/quarantine")
async def list_quarantine_records(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lists entries from underage_quarantine_registry with active countdowns."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(UnderageQuarantineRegistry)
        .order_by(UnderageQuarantineRegistry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    items = []
    for r in records:
        items.append({
            "id": str(r.id),
            "device_hash": r.device_hash,
            "attempted_dob": r.attempted_dob.isoformat() if r.attempted_dob else None,
            "quarantine_until": r.quarantine_until.isoformat() if r.quarantine_until else None,
            "is_active": r.quarantine_until > now if r.quarantine_until else False,
            "attempt_metadata": r.attempt_metadata or {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return items


@router.post("/admin/api/quarantine/{quarantine_id}/release")
async def release_quarantine_record(
    quarantine_id: str,
    payload: QuarantineReleaseRequest,
    request: Request,
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Releases device hardware quarantine override for valid appeals and logs audit record."""
    client_ip = get_request_client_ip(request)
    try:
        qid = UUID(quarantine_id)
        record = await db.get(UnderageQuarantineRegistry, qid)
    except ValueError:
        record = None

    if not record:
        raise SanctuaryException(
            error_code="QUARANTINE_NOT_FOUND",
            message="Quarantine record not found.",
            status_code=404,
        )

    # Release by expiring quarantine immediately
    record.quarantine_until = datetime.now(timezone.utc)

    await log_admin_action(
        session=db,
        admin_email=admin_email,
        action="release_quarantine",
        target_type="underage_quarantine",
        target_id=str(record.id),
        details={"reason": payload.reason or "", "device_hash": record.device_hash},
        ip_address=client_ip,
    )
    await db.commit()

    return {"success": True, "message": "Quarantine successfully released.", "id": str(record.id)}


@router.get("/admin/api/payments")
async def list_payments(
    store: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Queries transaction ledger from in_app_purchases and pending web entitlements."""
    stmt = select(InAppPurchase)
    if store:
        stmt = stmt.where(InAppPurchase.store == store)
    if status_filter:
        stmt = stmt.where(InAppPurchase.status == status_filter)

    stmt = stmt.order_by(InAppPurchase.purchased_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    purchases = result.scalars().all()

    items = []
    for p in purchases:
        items.append({
            "id": p.id,
            "user_id": str(p.user_id) if p.user_id else None,
            "transaction_reference": p.transaction_reference,
            "product_identifier": p.product_identifier,
            "store": p.store,
            "currency": p.currency,
            "amount_gross": float(p.amount_gross),
            "amount_net": float(p.amount_net),
            "status": p.status,
            "purchased_at": p.purchased_at.isoformat() if p.purchased_at else None,
        })
    return items


@router.post("/admin/api/users/{user_id}/grant-sparks")
async def grant_sparks_to_user(
    user_id: UUID,
    payload: GrantSparksRequest,
    request: Request,
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Credits Sparks directly to User.reward_balance for customer support and records audit log."""
    client_ip = get_request_client_ip(request)
    user = await db.get(User, user_id)
    if not user:
        raise SanctuaryException(
            error_code="SEEKER_NOT_FOUND",
            message="Seeker account not found.",
            status_code=404,
        )

    prev_balance = user.reward_balance or 0
    new_balance = max(0, prev_balance + payload.sparks_amount)
    user.reward_balance = new_balance

    await log_admin_action(
        session=db,
        admin_email=admin_email,
        action="grant_sparks",
        target_type="user",
        target_id=str(user.id),
        details={
            "delta": payload.sparks_amount,
            "previous_balance": prev_balance,
            "new_balance": new_balance,
            "reason": payload.reason,
        },
        ip_address=client_ip,
    )
    await db.commit()

    return {
        "success": True,
        "user_id": str(user.id),
        "previous_balance": prev_balance,
        "reward_balance": new_balance,
        "sparks_amount": payload.sparks_amount,
    }


@router.post("/admin/api/users/{user_id}/grant-pass")
async def grant_pass_to_user(
    user_id: UUID,
    payload: GrantPassRequest,
    request: Request,
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Credits pass or micro-perk directly to seeker and records audit log."""
    client_ip = get_request_client_ip(request)
    user = await db.get(User, user_id)
    if not user:
        raise SanctuaryException(
            error_code="SEEKER_NOT_FOUND",
            message="Seeker account not found.",
            status_code=404,
        )

    await billing_entitlement_service.provision_user_entitlements(user, payload.sku, db)

    await log_admin_action(
        session=db,
        admin_email=admin_email,
        action="grant_pass",
        target_type="user",
        target_id=str(user.id),
        details={"sku": payload.sku, "reason": payload.reason, "tier": user.subscription_tier},
        ip_address=client_ip,
    )
    await db.commit()

    return {
        "success": True,
        "user_id": str(user.id),
        "subscription_tier": user.subscription_tier,
        "swipes_remaining": user.swipes_remaining,
        "sku": payload.sku,
    }


@router.get("/admin/api/dpdp")
async def get_dpdp_compliance_records(
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Queries DPDP Act 2023 compliance records (SAR exports, nominees, and affirmative consent logs)."""
    # 1. Recent export requests
    export_stmt = select(DataExportRequest).order_by(DataExportRequest.created_at.desc()).limit(20)
    exports = (await db.execute(export_stmt)).scalars().all()

    # 2. Recent nominees
    nominee_stmt = select(DataNominee).order_by(DataNominee.designated_at.desc()).limit(20)
    nominees = (await db.execute(nominee_stmt)).scalars().all()

    # 3. Recent consent logs
    consent_stmt = select(ConsentAuditLog).order_by(ConsentAuditLog.created_at.desc()).limit(20)
    consents = (await db.execute(consent_stmt)).scalars().all()

    return {
        "export_requests": [
            {
                "id": str(e.id),
                "user_id": str(e.user_id),
                "status": e.status,
                "checksum_sha256": e.checksum_sha256,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "expires_at": e.expires_at.isoformat() if e.expires_at else None,
            }
            for e in exports
        ],
        "nominees": [
            {
                "user_id": str(n.user_id),
                "nominee_name": n.nominee_name,
                "relationship": n.relationship,
                "verification_status": n.verification_status,
                "designated_at": n.designated_at.isoformat() if n.designated_at else None,
            }
            for n in nominees
        ],
        "consent_logs": [
            {
                "id": c.id,
                "user_id": str(c.user_id),
                "purpose": c.consent_purpose_id,
                "ip_hash": c.ip_hash[:16] + "...",
                "installation_uuid": c.installation_uuid[:16] + "...",
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in consents
        ],
    }


@router.get("/admin/api/audit-logs")
async def list_audit_logs(
    action: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_email: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Queries public.admin_audit_logs with pagination and filtering."""
    stmt = select(AdminAuditLog)
    if action:
        stmt = stmt.where(AdminAuditLog.action == action)
    if target_type:
        stmt = stmt.where(AdminAuditLog.target_type == target_type)

    stmt = stmt.order_by(AdminAuditLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return [
        {
            "id": l.id,
            "admin_email": l.admin_email,
            "action": l.action,
            "target_type": l.target_type,
            "target_id": l.target_id,
            "details": l.details,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]


# ==============================================================================
# Production-Grade Sanctuary Dark-Gold HTML Renderers
# ==============================================================================

def render_login_html() -> str:
    """Renders Sanctuary Dark-Gold Login Portal HTML."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>UR-Heart Sanctuary | Superadmin Sentinel</title>
  <style>
    :root {
      --bg-deep: #07080B;
      --bg-card: rgba(20, 25, 35, 0.92);
      --border-gold: rgba(212, 175, 55, 0.28);
      --border-gold-glow: rgba(212, 175, 55, 0.7);
      --text-main: #F3F4F6;
      --text-muted: #9CA3AF;
      --gold-primary: #D4AF37;
      --gold-light: #F3E5AB;
      --gold-dark: #997D29;
      --danger-crimson: #EF4444;
      --danger-bg: rgba(239, 68, 68, 0.12);
      --danger-border: rgba(239, 68, 68, 0.4);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-deep);
      background-image: 
        radial-gradient(ellipse 80% 50% at 50% -15%, rgba(212, 175, 55, 0.16) 0%, rgba(7, 8, 11, 0) 70%),
        radial-gradient(circle 600px at 80% 85%, rgba(212, 175, 55, 0.06) 0%, rgba(7, 8, 11, 0) 60%);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }
    .login-card {
      background: var(--bg-card);
      border: 1px solid var(--border-gold);
      border-radius: 14px;
      backdrop-filter: blur(16px);
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.75), 0 0 24px rgba(212, 175, 55, 0.08);
      width: 100%;
      max-width: 440px;
      padding: 2.5rem 2rem;
    }
    .brand-header {
      text-align: center;
      margin-bottom: 2rem;
    }
    .brand-crest {
      font-size: 2.4rem;
      color: var(--gold-primary);
      margin-bottom: 0.5rem;
      filter: drop-shadow(0 0 10px rgba(212, 175, 55, 0.4));
    }
    .brand-title {
      font-size: 1.45rem;
      font-weight: 700;
      color: var(--gold-light);
      letter-spacing: 0.04em;
    }
    .brand-sub {
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 0.35rem;
      letter-spacing: 0.02em;
    }
    .error-box {
      display: none;
      background: var(--danger-bg);
      border: 1px solid var(--danger-border);
      color: #FCA5A5;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      font-size: 0.85rem;
      margin-bottom: 1.25rem;
    }
    .form-group {
      margin-bottom: 1.25rem;
    }
    label {
      display: block;
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--gold-light);
      margin-bottom: 0.45rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    input[type="email"], input[type="password"] {
      width: 100%;
      padding: 0.85rem 1rem;
      background: rgba(10, 14, 20, 0.8);
      border: 1px solid rgba(212, 175, 55, 0.3);
      border-radius: 8px;
      color: var(--text-main);
      font-size: 0.95rem;
      outline: none;
      transition: all 0.2s ease;
    }
    input:focus {
      border-color: var(--gold-primary);
      box-shadow: 0 0 12px rgba(212, 175, 55, 0.35);
      background: rgba(15, 20, 28, 0.95);
    }
    .btn-submit {
      width: 100%;
      padding: 0.95rem;
      background: linear-gradient(135deg, #D4AF37 0%, #997D29 100%);
      color: #07080B;
      font-weight: 700;
      font-size: 0.95rem;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.25s ease;
      letter-spacing: 0.03em;
      margin-top: 0.5rem;
    }
    .btn-submit:hover {
      box-shadow: 0 0 18px rgba(212, 175, 55, 0.55);
      transform: translateY(-1px);
    }
    .btn-submit:disabled {
      opacity: 0.6;
      cursor: not-allowed;
      transform: none;
    }
    .footer-note {
      text-align: center;
      margin-top: 1.75rem;
      font-size: 0.75rem;
      color: var(--text-muted);
      line-height: 1.4;
    }
  </style>
</head>
<body>
  <div class="login-card">
    <div class="brand-header">
      <div class="brand-crest">⚜️</div>
      <div class="brand-title">UR-Heart Sanctuary</div>
      <div class="brand-sub">Superadmin Sentinel Gatekeeper</div>
    </div>

    <div id="errorBox" class="error-box"></div>

    <form id="loginForm">
      <div class="form-group">
        <label for="adminEmail">Authorized Email</label>
        <input type="email" id="adminEmail" required value="asiverticals@gmail.com" readonly style="opacity:0.85;cursor:default;">
      </div>
      <div class="form-group">
        <label for="adminSecret">Superadmin Secret Key</label>
        <input type="password" id="adminSecret" placeholder="Enter SUPERADMIN_SECRET_KEY" required autofocus>
      </div>
      <button type="submit" id="submitBtn" class="btn-submit">Authenticate Sentinel</button>
    </form>

    <div class="footer-note">
      India DPDP Act 2023 & IT Rules 2021 Statutory Security Grid.<br>
      Strictly restricted to ASI Verticals Private Limited.
    </div>
  </div>

  <script>
    const form = document.getElementById('loginForm');
    const errorBox = document.getElementById('errorBox');
    const submitBtn = document.getElementById('submitBtn');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorBox.style.display = 'none';
      submitBtn.disabled = true;
      submitBtn.textContent = 'Verifying Sentinel Clearance...';

      const email = document.getElementById('adminEmail').value.trim();
      const secret_key = document.getElementById('adminSecret').value.trim();

      try {
        const res = await fetch('/admin/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, secret_key })
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.message || data.detail || 'Authentication failed.');
        }
        window.location.href = data.redirect_url || '/admin';
      } catch (err) {
        errorBox.textContent = err.message;
        errorBox.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Authenticate Sentinel';
      }
    });
  </script>
</body>
</html>"""


def render_dashboard_html() -> str:
    """Renders Responsive Production Web Admin Dashboard HTML with 7 Sanctuary Dark-Gold tabs."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>UR-Heart Sanctuary | Web Admin Portal</title>
  <style>
    :root {
      --bg-deep: #07080B;
      --bg-surface: #0E121A;
      --bg-card: rgba(20, 25, 35, 0.88);
      --bg-card-hover: rgba(28, 35, 48, 0.95);
      --border-gold: rgba(212, 175, 55, 0.22);
      --border-gold-glow: rgba(212, 175, 55, 0.6);
      --text-main: #F3F4F6;
      --text-muted: #9CA3AF;
      --gold-primary: #D4AF37;
      --gold-light: #F3E5AB;
      --gold-dark: #997D29;
      --danger-crimson: #EF4444;
      --danger-bg: rgba(239, 68, 68, 0.12);
      --success-emerald: #10B981;
      --success-bg: rgba(16, 185, 129, 0.12);
      --warning-amber: #F59E0B;
      --warning-bg: rgba(245, 158, 11, 0.12);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-deep);
      background-image: 
        radial-gradient(ellipse 90% 40% at 50% -10%, rgba(212, 175, 55, 0.12) 0%, rgba(7, 8, 11, 0) 70%),
        radial-gradient(circle 800px at 85% 90%, rgba(212, 175, 55, 0.04) 0%, rgba(7, 8, 11, 0) 60%);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: rgba(10, 13, 19, 0.92);
      border-bottom: 1px solid var(--border-gold);
      backdrop-filter: blur(12px);
      padding: 0.9rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .header-brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .brand-crest {
      font-size: 1.6rem;
      color: var(--gold-primary);
    }
    .brand-title {
      font-weight: 700;
      font-size: 1.15rem;
      color: var(--gold-light);
      letter-spacing: 0.03em;
    }
    .header-actions {
      display: flex;
      align-items: center;
      gap: 1.25rem;
    }
    .admin-badge {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(212, 175, 55, 0.12);
      border: 1px solid var(--border-gold);
      padding: 0.35rem 0.85rem;
      border-radius: 9999px;
      font-size: 0.8rem;
      color: var(--gold-light);
    }
    .pulse-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--success-emerald);
      box-shadow: 0 0 8px var(--success-emerald);
    }
    .btn-logout {
      background: transparent;
      border: 1px solid rgba(239, 68, 68, 0.4);
      color: #F87171;
      padding: 0.38rem 0.85rem;
      border-radius: 6px;
      font-size: 0.8rem;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.2s ease;
    }
    .btn-logout:hover {
      background: var(--danger-bg);
      border-color: var(--danger-crimson);
      color: #fff;
    }
    .nav-bar {
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-gold);
      padding: 0 2rem;
      display: flex;
      gap: 0.5rem;
      overflow-x: auto;
      white-space: nowrap;
    }
    .tab-btn {
      background: transparent;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--text-muted);
      padding: 0.95rem 1.1rem;
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.2s ease;
    }
    .tab-btn:hover {
      color: var(--gold-light);
    }
    .tab-btn.active {
      color: var(--gold-primary);
      border-bottom-color: var(--gold-primary);
      text-shadow: 0 0 10px rgba(212, 175, 55, 0.3);
    }
    main {
      flex: 1;
      padding: 2rem;
      max-width: 1440px;
      margin: 0 auto;
      width: 100%;
    }
    .tab-pane {
      display: none;
    }
    .tab-pane.active {
      display: block;
      animation: fadeIn 0.2s ease-in;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.25rem;
      margin-bottom: 2rem;
    }
    .kpi-card {
      background: var(--bg-card);
      border: 1px solid var(--border-gold);
      border-radius: 10px;
      padding: 1.25rem 1.4rem;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    }
    .kpi-label {
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 0.4rem;
    }
    .kpi-value {
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--gold-light);
    }
    .kpi-note {
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-top: 0.35rem;
    }
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
    }
    .section-title {
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--gold-light);
    }
    .table-container {
      background: var(--bg-card);
      border: 1px solid var(--border-gold);
      border-radius: 10px;
      overflow-x: auto;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.88rem;
    }
    th {
      background: rgba(14, 18, 26, 0.95);
      border-bottom: 1px solid var(--border-gold);
      padding: 0.85rem 1rem;
      font-weight: 600;
      color: var(--gold-light);
      text-transform: uppercase;
      font-size: 0.75rem;
      letter-spacing: 0.04em;
    }
    td {
      padding: 0.85rem 1rem;
      border-bottom: 1px solid rgba(212, 175, 55, 0.08);
      color: var(--text-main);
    }
    tr:hover td {
      background: rgba(212, 175, 55, 0.03);
    }
    .badge {
      display: inline-block;
      padding: 0.2rem 0.55rem;
      border-radius: 9999px;
      font-size: 0.72rem;
      font-weight: 600;
      letter-spacing: 0.03em;
    }
    .badge-danger { background: var(--danger-bg); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-success { background: var(--success-bg); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-warning { background: var(--warning-bg); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-neutral { background: rgba(156, 163, 175, 0.15); color: #D1D5DB; border: 1px solid rgba(156, 163, 175, 0.3); }
    .btn-action {
      background: var(--bg-surface);
      border: 1px solid var(--border-gold);
      color: var(--gold-light);
      padding: 0.35rem 0.75rem;
      border-radius: 6px;
      font-size: 0.78rem;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.2s;
    }
    .btn-action:hover {
      background: rgba(212, 175, 55, 0.15);
      border-color: var(--gold-primary);
    }
    .btn-danger {
      border-color: rgba(239, 68, 68, 0.4);
      color: #F87171;
    }
    .btn-danger:hover {
      background: var(--danger-bg);
      border-color: var(--danger-crimson);
    }
    .btn-success {
      border-color: rgba(16, 185, 129, 0.4);
      color: #34D399;
    }
    .btn-success:hover {
      background: var(--success-bg);
      border-color: var(--success-emerald);
    }
    .filter-bar {
      display: flex;
      gap: 1rem;
      margin-bottom: 1.25rem;
      flex-wrap: wrap;
    }
    .filter-input {
      background: rgba(12, 16, 24, 0.85);
      border: 1px solid var(--border-gold);
      color: var(--text-main);
      padding: 0.55rem 0.85rem;
      border-radius: 6px;
      font-size: 0.85rem;
      outline: none;
    }
    .filter-input:focus {
      border-color: var(--gold-primary);
      box-shadow: 0 0 10px rgba(212, 175, 55, 0.25);
    }
    .modal-overlay {
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.82);
      backdrop-filter: blur(8px);
      z-index: 100;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }
    .modal-card {
      background: #0E121A;
      border: 1px solid var(--border-gold);
      border-radius: 12px;
      width: 100%;
      max-width: 600px;
      padding: 1.75rem;
      box-shadow: 0 20px 50px rgba(0,0,0,0.8);
      max-height: 90vh;
      overflow-y: auto;
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
      border-bottom: 1px solid var(--border-gold);
      padding-bottom: 0.75rem;
    }
    .modal-title {
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--gold-light);
    }
    .close-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 1.3rem;
      cursor: pointer;
    }
    .toast {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      padding: 0.85rem 1.4rem;
      border-radius: 8px;
      font-size: 0.88rem;
      font-weight: 600;
      z-index: 200;
      box-shadow: 0 8px 24px rgba(0,0,0,0.5);
      display: none;
      animation: toastIn 0.25s ease;
    }
    @keyframes toastIn {
      from { transform: translateY(20px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
  </style>
</head>
<body>
  <header>
    <div class="header-brand">
      <div class="brand-crest">⚜️</div>
      <div class="brand-title">UR-Heart Sanctuary Administration</div>
    </div>
    <div class="header-actions">
      <div class="admin-badge">
        <div class="pulse-dot"></div>
        <span>asiverticals@gmail.com</span>
      </div>
      <button class="btn-logout" onclick="handleLogout()">Logout</button>
    </div>
  </header>

  <nav class="nav-bar">
    <button class="tab-btn active" onclick="switchTab('tab-telemetry')">📊 Operations Hub</button>
    <button class="tab-btn" onclick="switchTab('tab-kyc')">🛡️ Biometric KYC</button>
    <button class="tab-btn" onclick="switchTab('tab-grievances')">⚖️ Grievances & NCII</button>
    <button class="tab-btn" onclick="switchTab('tab-users')">👥 Seeker Console</button>
    <button class="tab-btn" onclick="switchTab('tab-monetization')">💳 Monetization Desk</button>
    <button class="tab-btn" onclick="switchTab('tab-dpdp')">📜 DPDP Privacy Vault</button>
    <button class="tab-btn" onclick="switchTab('tab-audit')">🔍 System Audit Log</button>
  </nav>

  <main>
    <!-- TAB 1: OPERATIONS HUB -->
    <div id="tab-telemetry" class="tab-pane active">
      <div class="section-header">
        <h2 class="section-title">Live Operational Telemetry</h2>
        <button class="btn-action" onclick="loadTelemetry()">🔄 Refresh KPIs</button>
      </div>
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Total Seekers</div>
          <div id="kpi-total-seekers" class="kpi-value">—</div>
          <div class="kpi-note">Registered profiles</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Daily Active (DAU)</div>
          <div id="kpi-dau" class="kpi-value">—</div>
          <div class="kpi-note">Active past 24h</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Monthly Active (MAU)</div>
          <div id="kpi-mau" class="kpi-value">—</div>
          <div class="kpi-note">Active past 30d</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Pending KYC Queue</div>
          <div id="kpi-kyc-queue" class="kpi-value">—</div>
          <div class="kpi-note">Biometric escalations</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Emergency 24h NCII</div>
          <div id="kpi-ncii" class="kpi-value" style="color:#F87171;">—</div>
          <div class="kpi-note">Rule 3(2)(b) SLA tickets</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">24h Gross Revenue</div>
          <div id="kpi-revenue" class="kpi-value">—</div>
          <div class="kpi-note">Completed transactions</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Active FCM Devices</div>
          <div id="kpi-fcm" class="kpi-value">—</div>
          <div class="kpi-note">Push delivery tokens</div>
        </div>
      </div>
    </div>

    <!-- TAB 2: BIOMETRIC KYC -->
    <div id="tab-kyc" class="tab-pane">
      <div class="section-header">
        <h2 class="section-title">Biometric KYC Adjudication Desk</h2>
        <button class="btn-action" onclick="loadKyc()">🔄 Refresh Queue</button>
      </div>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Escalation ID</th>
              <th>Seeker Name</th>
              <th>Declared Age</th>
              <th>Groq Match Score</th>
              <th>Anchor vs Live Frame</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="kyc-table-body">
            <tr><td colspan="6" style="text-align:center;color:var(--text-muted);">Loading pending escalations...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 3: GRIEVANCES & NCII -->
    <div id="tab-grievances" class="tab-pane">
      <div class="section-header">
        <h2 class="section-title">Grievances & Emergency NCII Moderation Desk</h2>
        <button class="btn-action" onclick="loadGrievances()">🔄 Refresh Dossiers</button>
      </div>
      <div class="filter-bar">
        <select id="grv-status-filter" class="filter-input" onchange="loadGrievances()">
          <option value="">All Statuses</option>
          <option value="under_review">Under Review</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="investigating">Investigating</option>
          <option value="actioned">Actioned</option>
          <option value="dismissed">Dismissed</option>
          <option value="closed">Closed</option>
        </select>
        <select id="grv-cat-filter" class="filter-input" onchange="loadGrievances()">
          <option value="">All Categories</option>
          <option value="ncii">Emergency NCII (24h)</option>
          <option value="explicit_content">Explicit Content (24h)</option>
          <option value="impersonation">Impersonation (24h)</option>
          <option value="underage">Underage (24h)</option>
          <option value="harassment">Harassment (15d)</option>
          <option value="fraud">Fraud (15d)</option>
          <option value="other">Other (15d)</option>
        </select>
      </div>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Dossier Ref</th>
              <th>Category</th>
              <th>Remaining SLA</th>
              <th>Status</th>
              <th>Evidence Summary</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="grievances-table-body">
            <tr><td colspan="6" style="text-align:center;color:var(--text-muted);">Loading grievances...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 4: SEEKER MANAGEMENT -->
    <div id="tab-users" class="tab-pane">
      <div class="section-header">
        <h2 class="section-title">Seeker User Management Console</h2>
        <button class="btn-action" onclick="loadUsers()">🔄 Refresh Seekers</button>
      </div>
      <div class="filter-bar">
        <input type="text" id="user-search-query" class="filter-input" placeholder="Search by email, name, or UUID..." style="width:320px;" onkeydown="if(event.key==='Enter')loadUsers()">
        <select id="user-status-filter" class="filter-input" onchange="loadUsers()">
          <option value="all">All Seekers</option>
          <option value="active">Active Only</option>
          <option value="banned">Banned Only</option>
        </select>
        <button class="btn-action" onclick="loadUsers()">Search</button>
      </div>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Seeker ID / Name</th>
              <th>Email</th>
              <th>Role / Tier</th>
              <th>Sparks Balance</th>
              <th>Status</th>
              <th>Contact Bridge</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="users-table-body">
            <tr><td colspan="7" style="text-align:center;color:var(--text-muted);">Loading seekers...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 5: MONETIZATION DESK -->
    <div id="tab-monetization" class="tab-pane">
      <div class="section-header">
        <h2 class="section-title">Monetization & Entitlements Desk</h2>
        <button class="btn-action" onclick="loadPayments()">🔄 Refresh Ledger</button>
      </div>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Transaction Ref</th>
              <th>Seeker ID</th>
              <th>SKU Identifier</th>
              <th>Store</th>
              <th>Gross Amount</th>
              <th>Status</th>
              <th>Purchased At</th>
            </tr>
          </thead>
          <tbody id="payments-table-body">
            <tr><td colspan="7" style="text-align:center;color:var(--text-muted);">Loading payments...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 6: DPDP PRIVACY VAULT -->
    <div id="tab-dpdp" class="tab-pane">
      <div class="section-header">
        <h2 class="section-title">DPDP Privacy & Compliance Vault</h2>
        <button class="btn-action" onclick="loadDpdp()">🔄 Refresh Vault</button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:1.5rem;">
        <div>
          <h3 style="color:var(--gold-light);font-size:1rem;margin-bottom:0.75rem;">Subject Access Requests (SAR § 11)</h3>
          <div class="table-container">
            <table>
              <thead><tr><th>ID</th><th>User</th><th>Status</th><th>Date</th></tr></thead>
              <tbody id="dpdp-exports-body"><tr><td colspan="4">Loading...</td></tr></tbody>
            </table>
          </div>
        </div>
        <div>
          <h3 style="color:var(--gold-light);font-size:1rem;margin-bottom:0.75rem;">Digital Nominees (§ 14)</h3>
          <div class="table-container">
            <table>
              <thead><tr><th>User</th><th>Nominee Name</th><th>Relation</th><th>Designated</th></tr></thead>
              <tbody id="dpdp-nominees-body"><tr><td colspan="4">Loading...</td></tr></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 7: AUDIT LOG -->
    <div id="tab-audit" class="tab-pane">
      <div class="section-header">
        <h2 class="section-title">Real-Time System Audit Log</h2>
        <button class="btn-action" onclick="loadAuditLogs()">🔄 Refresh Audit Trail</button>
      </div>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Admin Email</th>
              <th>Action Verb</th>
              <th>Target Type</th>
              <th>Target ID</th>
              <th>IP Address</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody id="audit-table-body">
            <tr><td colspan="7" style="text-align:center;color:var(--text-muted);">Loading audit trail...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </main>

  <!-- MODAL: KYC Adjudication -->
  <div id="kycModal" class="modal-overlay">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title">Adjudicate KYC Escalation</div>
        <button class="close-btn" onclick="closeModal('kycModal')">&times;</button>
      </div>
      <div id="kycModalContent" style="margin-bottom:1.25rem;"></div>
      <div style="margin-bottom:1.25rem;">
        <label style="display:block;font-size:0.8rem;color:var(--gold-light);margin-bottom:0.4rem;">Statutory Reason / Reviewer Notes</label>
        <input type="text" id="kycDecisionNotes" class="filter-input" style="width:100%;" placeholder="Enter reason (optional for approval, required for rejection)">
      </div>
      <div style="display:flex;justify-content:flex-end;gap:0.75rem;">
        <button class="btn-action btn-danger" onclick="submitKycDecision('reject')">Reject Seeker</button>
        <button class="btn-action btn-success" onclick="submitKycDecision('approve')">Approve Seeker</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Grievance Resolution -->
  <div id="grvModal" class="modal-overlay">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title">Statutory Grievance Resolution</div>
        <button class="close-btn" onclick="closeModal('grvModal')">&times;</button>
      </div>
      <div id="grvModalContent" style="margin-bottom:1.25rem;"></div>
      <div style="margin-bottom:1rem;">
        <label style="display:block;font-size:0.8rem;color:var(--gold-light);margin-bottom:0.4rem;">Update Status</label>
        <select id="grvUpdateStatus" class="filter-input" style="width:100%;">
          <option value="actioned">Actioned (Takedown / Content Removed)</option>
          <option value="dismissed">Dismissed (No Statutory Violation Found)</option>
          <option value="investigating">Investigating (Under Deep Review)</option>
          <option value="closed">Closed</option>
        </select>
      </div>
      <div style="margin-bottom:1.25rem;">
        <label style="display:block;font-size:0.8rem;color:var(--gold-light);margin-bottom:0.4rem;">Statutory Resolution Summary</label>
        <textarea id="grvResolutionSummary" class="filter-input" style="width:100%;height:80px;" placeholder="Statutory notes recorded under IT Rules 2021..."></textarea>
      </div>
      <div style="display:flex;justify-content:flex-end;gap:0.75rem;">
        <button class="btn-action" onclick="closeModal('grvModal')">Cancel</button>
        <button class="btn-action btn-success" onclick="submitGrievanceResolution()">Save Resolution</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Sparks Grant -->
  <div id="sparksModal" class="modal-overlay">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title">Customer Support: Grant Sparks</div>
        <button class="close-btn" onclick="closeModal('sparksModal')">&times;</button>
      </div>
      <input type="hidden" id="sparksUserId">
      <div style="margin-bottom:1rem;">
        <label style="display:block;font-size:0.8rem;color:var(--gold-light);margin-bottom:0.4rem;">Sparks Amount</label>
        <input type="number" id="sparksAmount" class="filter-input" style="width:100%;" value="100">
      </div>
      <div style="margin-bottom:1.25rem;">
        <label style="display:block;font-size:0.8rem;color:var(--gold-light);margin-bottom:0.4rem;">Dispute Resolution Reason</label>
        <input type="text" id="sparksReason" class="filter-input" style="width:100%;" placeholder="e.g. Compensation for dropped blind date connection">
      </div>
      <div style="display:flex;justify-content:flex-end;gap:0.75rem;">
        <button class="btn-action" onclick="closeModal('sparksModal')">Cancel</button>
        <button class="btn-action btn-success" onclick="submitSparksGrant()">Credit Sparks</button>
      </div>
    </div>
  </div>

  <div id="toast" class="toast"></div>

  <script>
    let activeKycId = null;
    let activeGrievanceId = null;

    function showToast(msg, isError = false) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.style.background = isError ? 'rgba(239, 68, 68, 0.95)' : 'rgba(16, 185, 129, 0.95)';
      t.style.color = '#fff';
      t.style.display = 'block';
      setTimeout(() => { t.style.display = 'none'; }, 3500);
    }

    function switchTab(tabId) {
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById(tabId).classList.add('active');
      event.currentTarget.classList.add('active');

      if (tabId === 'tab-telemetry') loadTelemetry();
      if (tabId === 'tab-kyc') loadKyc();
      if (tabId === 'tab-grievances') loadGrievances();
      if (tabId === 'tab-users') loadUsers();
      if (tabId === 'tab-monetization') loadPayments();
      if (tabId === 'tab-dpdp') loadDpdp();
      if (tabId === 'tab-audit') loadAuditLogs();
    }

    function closeModal(modalId) {
      document.getElementById(modalId).style.display = 'none';
    }

    async function handleLogout() {
      try {
        await fetch('/admin/api/logout', { method: 'POST' });
        window.location.href = '/admin/login';
      } catch (e) {
        window.location.href = '/admin/login';
      }
    }

    async function loadTelemetry() {
      try {
        const res = await fetch('/admin/api/telemetry');
        if (res.status === 401) { window.location.href = '/admin/login'; return; }
        const data = await res.json();
        document.getElementById('kpi-total-seekers').textContent = (data.total_seekers || 0).toLocaleString();
        document.getElementById('kpi-dau').textContent = (data.dau || 0).toLocaleString();
        document.getElementById('kpi-mau').textContent = (data.mau || 0).toLocaleString();
        document.getElementById('kpi-kyc-queue').textContent = (data.pending_kyc_count || 0).toLocaleString();
        document.getElementById('kpi-ncii').textContent = (data.emergency_ncii_count || 0).toLocaleString();
        document.getElementById('kpi-revenue').textContent = '₹' + (data.revenue_24h || 0).toLocaleString(undefined, {minimumFractionDigits:2});
        document.getElementById('kpi-fcm').textContent = (data.active_fcm_devices || 0).toLocaleString();
      } catch (e) {
        showToast('Failed to load telemetry', true);
      }
    }

    async function loadKyc() {
      try {
        const res = await fetch('/admin/api/kyc/pending');
        const items = await res.json();
        const tbody = document.getElementById('kyc-table-body');
        if (!items || items.length === 0) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">No pending KYC escalations. Queue is clean.</td></tr>';
          return;
        }
        tbody.innerHTML = items.map(item => `
          <tr>
            <td><code>${item.id}</code></td>
            <td><strong>${item.full_name || 'Seeker'}</strong></td>
            <td>${item.declared_age ? item.declared_age + ' yrs' : '—'}</td>
            <td><span class="badge ${item.groq_match_score >= 60 ? 'badge-warning' : 'badge-danger'}">${item.groq_match_score}%</span></td>
            <td>
              <div style="display:flex;gap:0.5rem;align-items:center;">
                ${item.anchor_photo_url ? `<a href="${item.anchor_photo_url}" target="_blank" style="color:var(--gold-primary);text-decoration:none;">Anchor Photo ↗</a>` : '<span style="color:var(--text-muted)">No anchor</span>'}
                <span>|</span>
                ${item.live_frame_url ? `<a href="${item.live_frame_url}" target="_blank" style="color:var(--gold-light);text-decoration:none;">Live Frame ↗</a>` : '<span style="color:var(--text-muted)">No frame</span>'}
              </div>
            </td>
            <td>
              <button class="btn-action" onclick="openKycModal('${item.id}', '${item.full_name}', ${item.groq_match_score})">Adjudicate</button>
            </td>
          </tr>
        `).join('');
      } catch (e) {
        showToast('Failed to load KYC queue', true);
      }
    }

    function openKycModal(id, name, score) {
      activeKycId = id;
      document.getElementById('kycModalContent').innerHTML = `
        <div style="font-size:0.9rem;color:var(--text-main);line-height:1.6;">
          <strong>Seeker:</strong> ${name}<br>
          <strong>Groq Biometric Match Score:</strong> ${score}%<br>
          <p style="font-size:0.75rem;color:var(--text-muted);margin-top:0.5rem;">
            Adjudicating will immediately update seeker's KYC verification status and trigger DPDP Section 8 mandatory ephemeral frame deletion from R2 storage.
          </p>
        </div>
      `;
      document.getElementById('kycDecisionNotes').value = '';
      document.getElementById('kycModal').style.display = 'flex';
    }

    async function submitKycDecision(decision) {
      if (!activeKycId) return;
      const notes = document.getElementById('kycDecisionNotes').value.trim();
      try {
        const res = await fetch(`/admin/api/kyc/${activeKycId}/decide`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision, notes })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.message || 'Adjudication failed');
        showToast(`KYC successfully adjudicated as ${decision}`);
        closeModal('kycModal');
        loadKyc();
      } catch (e) {
        showToast(e.message, true);
      }
    }

    async function loadGrievances() {
      const status = document.getElementById('grv-status-filter').value;
      const category = document.getElementById('grv-cat-filter').value;
      let url = '/admin/api/grievances?limit=50';
      if (status) url += `&status=${status}`;
      if (category) url += `&category=${category}`;

      try {
        const res = await fetch(url);
        const items = await res.json();
        const tbody = document.getElementById('grievances-table-body');
        if (!items || items.length === 0) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">No matching grievance dossiers found.</td></tr>';
          return;
        }
        tbody.innerHTML = items.map(d => {
          let slaBadge = '<span class="badge badge-neutral">Standard SLA</span>';
          if (d.remaining_sla_seconds !== null) {
            const hrs = Math.floor(d.remaining_sla_seconds / 3600);
            const mins = Math.floor((d.remaining_sla_seconds % 3600) / 60);
            if (d.remaining_sla_seconds < 0) {
              slaBadge = `<span class="badge badge-danger">EXPIRED (${Math.abs(hrs)}h ago)</span>`;
            } else if (d.remaining_sla_seconds <= 14400) {
              slaBadge = `<span class="badge badge-danger">🚨 ${hrs}h ${mins}m left</span>`;
            } else {
              slaBadge = `<span class="badge badge-warning">⏱️ ${hrs}h ${mins}m left</span>`;
            }
          }
          return `
            <tr>
              <td><code>${d.dossier_reference_id}</code></td>
              <td><span class="badge ${d.violation_category === 'ncii' ? 'badge-danger' : 'badge-neutral'}">${d.violation_category}</span></td>
              <td>${slaBadge}</td>
              <td><span class="badge ${d.status === 'actioned' ? 'badge-success' : 'badge-warning'}">${d.status}</span></td>
              <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${d.evidence_text}">${d.evidence_text}</td>
              <td>
                <button class="btn-action" onclick="openGrievanceModal('${d.id}', '${d.dossier_reference_id}', '${d.status}', '${d.violation_category}')">Resolve</button>
              </td>
            </tr>
          `;
        }).join('');
      } catch (e) {
        showToast('Failed to load grievances', true);
      }
    }

    function openGrievanceModal(id, ref, curStatus, cat) {
      activeGrievanceId = id;
      document.getElementById('grvModalContent').innerHTML = `
        <div style="font-size:0.9rem;color:var(--text-main);line-height:1.5;">
          <strong>Dossier Reference:</strong> <code>${ref}</code><br>
          <strong>Violation Category:</strong> ${cat}<br>
          <strong>Current Status:</strong> ${curStatus}
        </div>
      `;
      document.getElementById('grvUpdateStatus').value = curStatus === 'under_review' ? 'actioned' : curStatus;
      document.getElementById('grvResolutionSummary').value = '';
      document.getElementById('grvModal').style.display = 'flex';
    }

    async function submitGrievanceResolution() {
      if (!activeGrievanceId) return;
      const status = document.getElementById('grvUpdateStatus').value;
      const resolution_summary = document.getElementById('grvResolutionSummary').value.trim();

      try {
        const res = await fetch(`/admin/api/grievances/${activeGrievanceId}/resolve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status, resolution_summary })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.message || 'Resolution failed');
        showToast(`Grievance updated to ${status}`);
        closeModal('grvModal');
        loadGrievances();
      } catch (e) {
        showToast(e.message, true);
      }
    }

    async function loadUsers() {
      const q = document.getElementById('user-search-query').value.trim();
      const status = document.getElementById('user-status-filter').value;
      let url = '/admin/api/users?limit=50';
      if (q) url += `&query=${encodeURIComponent(q)}`;
      if (status && status !== 'all') url += `&status=${status}`;

      try {
        const res = await fetch(url);
        const users = await res.json();
        const tbody = document.getElementById('users-table-body');
        if (!users || users.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);">No seekers matching query.</td></tr>';
          return;
        }
        tbody.innerHTML = users.map(u => `
          <tr>
            <td>
              <strong>${u.full_name || 'Seeker'}</strong><br>
              <code style="font-size:0.75rem;color:var(--text-muted);">${u.id.substring(0,8)}...</code>
            </td>
            <td>${u.email || '<span style="color:var(--text-muted)">None</span>'}</td>
            <td><span class="badge badge-neutral">${u.role}</span> / <span class="badge badge-warning">${u.subscription_tier}</span></td>
            <td><strong>${(u.reward_balance || 0).toLocaleString()}</strong> Sparks</td>
            <td><span class="badge ${u.is_banned ? 'badge-danger' : 'badge-success'}">${u.is_banned ? 'Banned' : 'Active'}</span></td>
            <td style="font-size:0.8rem;color:var(--text-muted);">${u.masked_contact_bridge}</td>
            <td>
              <div style="display:flex;gap:0.4rem;">
                <button class="btn-action ${u.is_banned ? 'btn-success' : 'btn-danger'}" onclick="toggleBan('${u.id}', ${u.is_banned})">
                  ${u.is_banned ? 'Unban' : 'Ban'}
                </button>
                <button class="btn-action" onclick="openSparksModal('${u.id}')">+ Sparks</button>
              </div>
            </td>
          </tr>
        `).join('');
      } catch (e) {
        showToast('Failed to load seekers', true);
      }
    }

    async function toggleBan(userId, isCurrentlyBanned) {
      const verb = isCurrentlyBanned ? 'unban' : 'ban';
      const reason = prompt(`Reason for ${verb}ning seeker:`, isCurrentlyBanned ? 'Appeal approved' : 'Violation of community safety policies');
      if (reason === null) return;

      try {
        const res = await fetch(`/admin/api/users/${userId}/toggle-ban`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.message || 'Operation failed');
        showToast(`Seeker ${data.action.replace('_', ' ')} successfully`);
        loadUsers();
      } catch (e) {
        showToast(e.message, true);
      }
    }

    function openSparksModal(userId) {
      document.getElementById('sparksUserId').value = userId;
      document.getElementById('sparksAmount').value = '100';
      document.getElementById('sparksReason').value = '';
      document.getElementById('sparksModal').style.display = 'flex';
    }

    async function submitSparksGrant() {
      const userId = document.getElementById('sparksUserId').value;
      const amount = parseInt(document.getElementById('sparksAmount').value, 10);
      const reason = document.getElementById('sparksReason').value.trim();

      if (!reason) {
        alert('Reason is mandatory for ledger audit trail.');
        return;
      }

      try {
        const res = await fetch(`/admin/api/users/${userId}/grant-sparks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sparks_amount: amount, reason })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.message || 'Sparks grant failed');
        showToast(`Successfully granted ${amount} Sparks. New balance: ${data.reward_balance}`);
        closeModal('sparksModal');
        loadUsers();
      } catch (e) {
        showToast(e.message, true);
      }
    }

    async function loadPayments() {
      try {
        const res = await fetch('/admin/api/payments?limit=50');
        const items = await res.json();
        const tbody = document.getElementById('payments-table-body');
        if (!items || items.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);">No payment records in ledger.</td></tr>';
          return;
        }
        tbody.innerHTML = items.map(p => `
          <tr>
            <td><code>${p.transaction_reference}</code></td>
            <td><code style="font-size:0.75rem;">${p.user_id ? p.user_id.substring(0,8) + '...' : 'Anonymous/Guest'}</code></td>
            <td><strong>${p.product_identifier}</strong></td>
            <td><span class="badge badge-neutral">${p.store}</span></td>
            <td><strong>${p.currency} ${p.amount_gross.toFixed(2)}</strong></td>
            <td><span class="badge ${p.status === 'completed' ? 'badge-success' : 'badge-warning'}">${p.status}</span></td>
            <td style="font-size:0.75rem;color:var(--text-muted);">${p.purchased_at ? p.purchased_at.substring(0,19).replace('T', ' ') : '—'}</td>
          </tr>
        `).join('');
      } catch (e) {
        showToast('Failed to load payment ledger', true);
      }
    }

    async function loadDpdp() {
      try {
        const res = await fetch('/admin/api/dpdp');
        const data = await res.json();

        // Exports
        const expBody = document.getElementById('dpdp-exports-body');
        if (!data.export_requests || data.export_requests.length === 0) {
          expBody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);">No SAR requests</td></tr>';
        } else {
          expBody.innerHTML = data.export_requests.map(e => `
            <tr>
              <td><code>${e.id.substring(0,8)}...</code></td>
              <td><code>${e.user_id.substring(0,8)}...</code></td>
              <td><span class="badge ${e.status === 'ready' ? 'badge-success' : 'badge-neutral'}">${e.status}</span></td>
              <td style="font-size:0.75rem;">${e.created_at ? e.created_at.substring(0,10) : ''}</td>
            </tr>
          `).join('');
        }

        // Nominees
        const nomBody = document.getElementById('dpdp-nominees-body');
        if (!data.nominees || data.nominees.length === 0) {
          nomBody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);">No designated nominees</td></tr>';
        } else {
          nomBody.innerHTML = data.nominees.map(n => `
            <tr>
              <td><code>${n.user_id.substring(0,8)}...</code></td>
              <td><strong>${n.nominee_name}</strong></td>
              <td>${n.relationship}</td>
              <td style="font-size:0.75rem;">${n.designated_at ? n.designated_at.substring(0,10) : ''}</td>
            </tr>
          `).join('');
        }
      } catch (e) {
        showToast('Failed to load DPDP vault', true);
      }
    }

    async function loadAuditLogs() {
      try {
        const res = await fetch('/admin/api/audit-logs?limit=50');
        const logs = await res.json();
        const tbody = document.getElementById('audit-table-body');
        if (!logs || logs.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);">No audit records found.</td></tr>';
          return;
        }
        tbody.innerHTML = logs.map(l => `
          <tr>
            <td style="font-size:0.75rem;color:var(--text-muted);">${l.created_at ? l.created_at.substring(0,19).replace('T', ' ') : ''}</td>
            <td><code>${l.admin_email}</code></td>
            <td><span class="badge badge-warning">${l.action}</span></td>
            <td><span class="badge badge-neutral">${l.target_type}</span></td>
            <td><code>${l.target_id}</code></td>
            <td style="font-size:0.75rem;">${l.ip_address}</td>
            <td><code style="font-size:0.72rem;max-width:200px;overflow:hidden;display:inline-block;white-space:nowrap;" title='${JSON.stringify(l.details)}'>${JSON.stringify(l.details)}</code></td>
          </tr>
        `).join('');
      } catch (e) {
        showToast('Failed to load audit logs', true);
      }
    }

    // Initialize telemetry on dashboard open
    loadTelemetry();
  </script>
</body>
</html>"""
