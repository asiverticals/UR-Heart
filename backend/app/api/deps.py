from typing import Optional
from uuid import UUID
from fastapi import Depends, Security, status
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
    return user
