import uuid
from datetime import timedelta
import pytest

from backend.app.core.security import (
    create_access_token,
    create_magic_link_token,
    create_refresh_token,
    decode_access_token,
    decode_magic_link_token,
    resolve_auth_uuid,
)

def test_access_token_creation_and_claims():
    """Test 1: Access token creates valid HS256 JWT with subject, expiration, and access type."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload
    assert payload["exp"] > payload["iat"]

def test_token_expiration_rejection():
    """Test 2: Expired access token is rejected and returns None."""
    user_id = uuid.uuid4()
    expired_token = create_access_token(user_id, expires_delta=timedelta(seconds=-10))
    payload = decode_access_token(expired_token)
    assert payload is None

def test_refresh_token_separation():
    """Test 3: Refresh tokens have type='refresh' and cannot be decoded as access tokens."""
    user_id = uuid.uuid4()
    refresh_token = create_refresh_token(user_id)
    # decode_access_token must reject tokens without type='access'
    payload = decode_access_token(refresh_token)
    assert payload is None

def test_resolve_auth_uuid_deterministic_v5():
    """Test 4: resolve_auth_uuid deterministically maps raw string IDs to RFC-4122 UUID v5."""
    raw_sub = "google_oauth_sub_1092837465"
    uuid1 = resolve_auth_uuid(raw_sub)
    uuid2 = resolve_auth_uuid(raw_sub)
    uuid_different = resolve_auth_uuid("google_oauth_sub_9999999999")

    assert isinstance(uuid1, uuid.UUID)
    assert uuid1 == uuid2
    assert uuid1 != uuid_different
    assert uuid1.version == 5

def test_magic_link_token_lifecycle():
    """Test 5: Magic link tokens have type='magic_link', 15m TTL, and cross-type isolation."""
    email = "seeker@urheart.app"
    token = create_magic_link_token(email)

    payload = decode_magic_link_token(token)
    assert payload is not None
    assert payload["sub"] == email
    assert payload["type"] == "magic_link"

    # Cannot be decoded as access token
    assert decode_access_token(token) is None

    # Expired magic link token returns None
    expired = create_magic_link_token(email, expires_delta=timedelta(seconds=-1))
    assert decode_magic_link_token(expired) is None

def test_tampered_token_rejection():
    """Test 6: Tampering with the middle of the signature rejects token."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    parts = token.split(".")
    assert len(parts) == 3

    # Tamper directly in the middle of the signature segment
    sig = parts[2]
    mid = len(sig) // 2
    flipped_char = "B" if sig[mid] == "A" else "A"
    tampered_sig = sig[:mid] + flipped_char + sig[mid + 1 :]
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"
    assert decode_access_token(tampered_token) is None


@pytest.mark.asyncio
async def test_verify_google_id_token_missing_client_id_raises_503(monkeypatch):
    """Test 7: verify_google_id_token fails closed with 503 when GOOGLE_SERVER_CLIENT_ID is unset."""
    from unittest.mock import AsyncMock, patch
    from backend.app.core.config import settings
    from backend.app.core.exceptions import SanctuaryException
    from backend.app.core.security import verify_google_id_token

    monkeypatch.setattr(settings, "GOOGLE_SERVER_CLIENT_ID", "")
    with patch("jwt.get_unverified_header", return_value={"kid": "mock_kid"}):
        with patch("backend.app.core.security._get_google_public_keys", new_callable=AsyncMock, return_value={"mock_kid": "mock_key"}):
            with pytest.raises(SanctuaryException) as exc_info:
                await verify_google_id_token("mock.google.id_token")
            assert exc_info.value.status_code == 503
            assert exc_info.value.error_code == "GOOGLE_AUTH_UNAVAILABLE"


@pytest.mark.asyncio
async def test_verify_google_id_token_missing_kid_raises_401():
    """Test 8: verify_google_id_token raises 401 when token header lacks kid."""
    from unittest.mock import patch
    from backend.app.core.exceptions import SanctuaryException
    from backend.app.core.security import verify_google_id_token

    with patch("jwt.get_unverified_header", return_value={}):
        with pytest.raises(SanctuaryException) as exc_info:
            await verify_google_id_token("mock.google.id_token")
        assert exc_info.value.status_code == 401
        assert exc_info.value.error_code == "INVALID_GOOGLE_TOKEN"


@pytest.mark.asyncio
async def test_get_google_public_keys_does_not_leak_internal_error_details():
    """Test 9: Network failure during JWKS fetch raises 503 without leaking raw exception in details."""
    from unittest.mock import AsyncMock, patch
    import httpx
    from backend.app.core.exceptions import SanctuaryException
    from backend.app.core.security import _get_google_public_keys, _google_oauth_keys_cache

    _google_oauth_keys_cache["keys"] = {}
    _google_oauth_keys_cache["expires_at"] = 0.0

    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Private internal socket failure")):
        with pytest.raises(SanctuaryException) as exc_info:
            await _get_google_public_keys(force_refresh=True)
        assert exc_info.value.status_code == 503
        assert exc_info.value.error_code == "GOOGLE_AUTH_UNAVAILABLE"
        # Must NOT leak internal exception text in details!
        assert exc_info.value.details is None or "Private internal socket failure" not in str(exc_info.value.details)



