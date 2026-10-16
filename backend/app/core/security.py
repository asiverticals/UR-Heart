import base64
import hashlib
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
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
    token_version: int = 1,
) -> str:
    """Signs HS256 JWT access token with 60-minute default TTL and token version tracking."""
    now = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = now + delta
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
        "token_version": token_version,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(
    subject: Union[str, uuid.UUID],
    expires_delta: Optional[timedelta] = None,
    token_version: int = 1,
) -> str:
    """Signs HS256 JWT refresh token with 30-day default TTL and token version tracking."""
    now = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expire = now + delta
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "refresh",
        "token_version": token_version,
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

async def _get_google_public_keys(force_refresh: bool = False) -> Dict[str, Any]:
    """Fetches Google public JWKs caching in-memory according to Cache-Control max-age asynchronously."""
    global _google_oauth_keys_cache
    now = time.time()
    if not force_refresh and _google_oauth_keys_cache["keys"] and now < _google_oauth_keys_cache["expires_at"]:
        return _google_oauth_keys_cache["keys"]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(GOOGLE_CERTS_URL)
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
        import logging
        logging.getLogger(__name__).error("Failed to retrieve Google public authentication keys: %s", e)
        if not force_refresh and _google_oauth_keys_cache["keys"]:
            return _google_oauth_keys_cache["keys"]
        raise SanctuaryException(
            error_code="GOOGLE_AUTH_UNAVAILABLE",
            message="Failed to retrieve Google public authentication keys.",
            status_code=503,
        )

async def verify_google_id_token(id_token: str) -> Dict[str, Any]:
    """Verifies RS256 Google ID token against cached Google x509 certs with audience check asynchronously."""
    try:
        header = jwt.get_unverified_header(id_token)
    except Exception:
        raise SanctuaryException(
            error_code="INVALID_GOOGLE_TOKEN",
            message="Malformed Google token header.",
            status_code=401,
        )

    kid = header.get("kid")
    if not kid:
        raise SanctuaryException(
            error_code="INVALID_GOOGLE_TOKEN",
            message="Missing kid in Google token header.",
            status_code=401,
        )

    keys = await _get_google_public_keys()
    if kid not in keys:
        keys = await _get_google_public_keys(force_refresh=True)

    public_key = keys.get(kid)
    if not public_key:
        raise SanctuaryException(
            error_code="INVALID_GOOGLE_TOKEN",
            message="Google signing key not found or expired.",
            status_code=401,
        )

    if not settings.GOOGLE_SERVER_CLIENT_ID:
        raise SanctuaryException(
            error_code="GOOGLE_AUTH_UNAVAILABLE",
            message="Google sign-in is not configured.",
            status_code=503,
        )

    try:
        claims = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=settings.GOOGLE_SERVER_CLIENT_ID,
            options={"require": ["exp", "iat", "aud", "iss", "sub"]},
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
        "email_verified": bool(claims.get("email_verified", False)),
        "name": claims.get("name", "Seeker"),
        "picture": claims.get("picture"),
    }


def _get_contact_bridge_keys() -> list[bytes]:
    """Returns list of encryption keys for contact bridges: dedicated key first, then fallback keys."""
    keys: list[bytes] = []
    cb_key = getattr(settings, "CONTACT_BRIDGE_SECRET_KEY", None)
    if cb_key:
        keys.append(hashlib.sha256(cb_key.encode()).digest())
    secret_key = getattr(settings, "SECRET_KEY", None)
    if secret_key:
        k = hashlib.sha256(secret_key.encode()).digest()
        if k not in keys:
            keys.append(k)
    jwt_key = getattr(settings, "JWT_SECRET_KEY", None)
    if jwt_key:
        k = hashlib.sha256(jwt_key.encode()).digest()
        if k not in keys:
            keys.append(k)
    if not keys:
        keys.append(hashlib.sha256(b"ur-heart-default-bridge-key").digest())
    return keys


def encrypt_contact_bridge(raw_handle: str) -> str:
    """Encrypts raw contact bridge handle using AES-256-GCM with version prefix v1:."""
    if not raw_handle:
        return ""
    keys = _get_contact_bridge_keys()
    primary_key = keys[0]
    aesgcm = AESGCM(primary_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, raw_handle.encode(), None)
    encoded = base64.b64encode(nonce + ciphertext).decode()
    return f"v1:{encoded}"


def decrypt_contact_bridge(encrypted_handle: str) -> str:
    """Decrypts contact bridge handle encrypted with AES-256-GCM, supporting version prefixes and key rotation fallback."""
    if not encrypted_handle:
        return ""
    payload = encrypted_handle
    if payload.startswith("v1:"):
        payload = payload[3:]
    try:
        raw = base64.b64decode(payload)
        if len(raw) < 12:
            return encrypted_handle
        nonce, ciphertext = raw[:12], raw[12:]
        for key in _get_contact_bridge_keys():
            try:
                aesgcm = AESGCM(key)
                return aesgcm.decrypt(nonce, ciphertext, None).decode()
            except Exception:
                continue
        return encrypted_handle
    except Exception:
        return encrypted_handle

