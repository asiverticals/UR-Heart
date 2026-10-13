from typing import Optional
from uuid import UUID
from fastapi import Depends, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from ..core.config import settings
from ..core.database import get_db
from ..core.exceptions import SanctuaryException
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
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise SanctuaryException(
                error_code="INVALID_TOKEN",
                message="Bearer session invalid or expired.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        user_id = UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
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
