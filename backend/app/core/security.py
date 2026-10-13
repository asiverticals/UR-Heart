import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from .config import settings
from .exceptions import SanctuaryException

_google_oauth_keys_cache: Dict[str, Any] = {
    "keys": {},
    "expires_at": 0.0,
}
GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"

def resolve_auth_uuid(raw_id: str) -> uuid.UUID:
    """Maps arbitrary external string identifier deterministically to RFC-4122 UUID v5."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, raw_id)

def create_access_token(
    subject: Union[str, uuid.UUID],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Signs HS256 JWT access token with 60-minute default TTL."""
    now = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = now + delta
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(
    subject: Union[str, uuid.UUID],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Signs HS256 JWT refresh token with 30-day default TTL."""
    now = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expire = now + delta
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_magic_link_token(
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Signs HS256 single-use magic link token with 15-minute TTL and unique JTI."""
    now = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(minutes=15)
    expire = now + delta
    payload = {
        "sub": email,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "magic_link",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes access token, validating expiration and asserting type == 'access'."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            return None
        return payload
    except (jwt.PyJWTError, ValueError):
        return None

def decode_magic_link_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes magic link token, validating expiration and asserting type == 'magic_link'."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "magic_link":
            return None
        return payload
    except (jwt.PyJWTError, ValueError):
        return None

def _get_google_public_keys(force_refresh: bool = False) -> Dict[str, Any]:
    """Fetches Google public JWKs caching in-memory according to Cache-Control max-age."""
    global _google_oauth_keys_cache
    now = time.time()
    if not force_refresh and _google_oauth_keys_cache["keys"] and now < _google_oauth_keys_cache["expires_at"]:
        return _google_oauth_keys_cache["keys"]

    try:
        resp = httpx.get(GOOGLE_CERTS_URL, timeout=5.0)
        resp.raise_for_status()
        jwks = resp.json()
        max_age = 3600
        cache_control = resp.headers.get("Cache-Control", "")
        for part in cache_control.split(","):
            if "max-age=" in part:
                try:
                    max_age = int(part.split("=")[1].strip())
                except ValueError:
                    pass
        keys = {}
        for jwk in jwks.get("keys", []):
            kid = jwk.get("kid")
            if kid:
                keys[kid] = RSAAlgorithm.from_jwk(jwk)
        _google_oauth_keys_cache["keys"] = keys
        _google_oauth_keys_cache["expires_at"] = now + max_age
        return keys
    except Exception as e:
        if not force_refresh and _google_oauth_keys_cache["keys"]:
            return _google_oauth_keys_cache["keys"]
        raise SanctuaryException(
            error_code="GOOGLE_AUTH_UNAVAILABLE",
            message="Failed to retrieve Google public authentication keys.",
            status_code=503,
            details={"error": str(e)},
        )

def verify_google_id_token(id_token: str) -> Dict[str, Any]:
    """Verifies RS256 Google ID token against cached Google x509 certs with audience check."""
    try:
        header = jwt.get_unverified_header(id_token)
    except Exception:
        raise SanctuaryException(
            error_code="INVALID_GOOGLE_TOKEN",
            message="Malformed Google token header.",
            status_code=401,
        )

    kid = header.get("kid")
    keys = _get_google_public_keys()
    public_key = keys.get(kid)
    if not public_key:
        # Key rotation fallback: force-refresh JWKS cache once on unknown kid
        keys = _get_google_public_keys(force_refresh=True)
        public_key = keys.get(kid)

    if not public_key:
        raise SanctuaryException(
            error_code="INVALID_GOOGLE_TOKEN",
            message="Google signing key not found or expired.",
            status_code=401,
        )

    expected_aud = settings.GOOGLE_SERVER_CLIENT_ID or (
        "test-client-id.apps.googleusercontent.com" if settings.ENVIRONMENT in ("test", "development") else None
    )
    if not expected_aud:
        raise SanctuaryException(
            error_code="GOOGLE_AUTH_UNCONFIGURED",
            message="Google server client ID is unconfigured.",
            status_code=500,
        )

    try:
        claims = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": True},
            audience=expected_aud,
        )
    except jwt.PyJWTError as e:
        raise SanctuaryException(
            error_code="INVALID_GOOGLE_TOKEN",
            message=f"Google token validation failed: {str(e)}",
            status_code=401,
        )

    iss = claims.get("iss")
    if iss not in ["accounts.google.com", "https://accounts.google.com"]:
        raise SanctuaryException(
            error_code="INVALID_GOOGLE_TOKEN",
            message="Invalid token issuer.",
            status_code=401,
        )

    if not claims.get("email_verified", False):
        raise SanctuaryException(
            error_code="GOOGLE_EMAIL_UNVERIFIED",
            message="Google email address has not been verified.",
            status_code=400,
        )

    return {
        "sub": claims["sub"],
        "email": claims.get("email"),
        "name": claims.get("name", "Seeker"),
        "picture": claims.get("picture"),
    }
