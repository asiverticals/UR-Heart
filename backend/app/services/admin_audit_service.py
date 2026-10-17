"""
Centralized Admin Audit Logging Service
UR-Heart Sanctuary Administration
Digital Personal Data Protection (DPDP) Act 2023 & IT Rules 2021 Compliance

Logs immutable administrative actions performed by superadmin to `admin_audit_logs`.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.domain.admin_telemetry import AdminAuditLog

logger = logging.getLogger("urheart.admin_audit")


async def log_admin_action(
    session: AsyncSession,
    admin_email: str,
    action: str,
    target_type: str,
    target_id: str,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AdminAuditLog:
    """Records an immutable administrative audit entry in public.admin_audit_logs.

    Args:
        session: Active database AsyncSession.
        admin_email: Email address of the administrative actor (e.g. asiverticals@gmail.com).
        action: Canonical action verb (e.g. 'kyc_approve', 'user_ban', 'resolve_grievance').
        target_type: Category of target entity (e.g. 'kyc_escalation', 'user', 'grievance', 'payment').
        target_id: String representation of target entity primary key / UUID.
        details: Supplementary structured metadata (reasons, state deltas, status).
        ip_address: Client IPv4/IPv6 address of the originating admin session.

    Returns:
        The instantiated AdminAuditLog record added to the current session.
    """
    clean_email = (admin_email or "asiverticals@gmail.com").strip().lower()
    clean_ip = (ip_address or "127.0.0.1").strip()
    if not clean_ip:
        clean_ip = "127.0.0.1"

    entry = AdminAuditLog(
        admin_email=clean_email,
        action=action.strip(),
        target_type=target_type.strip(),
        target_id=str(target_id).strip(),
        details=details if details is not None else {},
        ip_address=clean_ip,
        created_at=datetime.now(timezone.utc),
    )
    session.add(entry)

    logger.info(
        "AdminAudit: email=%s action=%s target_type=%s target_id=%s ip=%s",
        clean_email,
        action,
        target_type,
        target_id,
        clean_ip,
    )
    return entry
