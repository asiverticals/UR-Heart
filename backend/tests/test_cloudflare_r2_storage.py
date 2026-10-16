import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest
from botocore.stub import Stubber

from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.core.exceptions import SanctuaryException
from backend.app.main import app
from backend.app.models.domain.user import User
from backend.app.services.storage_service import (
    CloudflareR2StorageService,
    get_storage_service,
)

@pytest.fixture
def test_storage():
    """Generates a configured test CloudflareR2StorageService instance."""
    return CloudflareR2StorageService(
        account_id="test-account",
        access_key_id="test-key",
        secret_access_key="test-secret",
        bucket_name="ur-heart-media",
        public_domain="https://media.urheart.app",
    )

@pytest.fixture
def test_user():
    """Generates an authentic mock Seeker User instance."""
    user_id = uuid.uuid4()
    return User(
        id=user_id,
        auth_id=uuid.uuid4(),
        full_name="Radha Krishna",
        dob=date(1998, 5, 15),
        gender="Woman",
        interested_in="Men",
        contact_bridge_type="whatsapp",
        contact_bridge_encrypted="enc_bridge_token",
        referral_code="RADHA108",
        photos=[
            f"https://media.urheart.app/users/{user_id}/moments/slot_1.webp",
            f"https://media.urheart.app/users/{user_id}/moments/slot_2.webp",
        ],
    )

def test_unconfigured_storage_raises_sanctuary_exception():
    """Test: Service raises SanctuaryException if R2 credentials are unset."""
    unconfigured_service = CloudflareR2StorageService(
        account_id="",
        access_key_id="",
        secret_access_key="",
    )
    with pytest.raises(SanctuaryException) as exc_info:
        unconfigured_service.generate_presigned_put_url("users/1/moments/slot_1.webp")
    assert exc_info.value.error_code == "STORAGE_UNCONFIGURED"

def test_generate_presigned_put_url(test_storage):
    """Test 1: S3v4 Presigned PUT URL contains valid query parameters, bucket, and expiry."""
    url = test_storage.generate_presigned_put_url(
        key="users/123/moments/slot_1.webp",
        content_type="image/webp",
        expires_in=300,
    )
    assert "https://test-account.r2.cloudflarestorage.com/ur-heart-media/users/123/moments/slot_1.webp" in url
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in url
    assert "X-Amz-Expires=300" in url
    assert "X-Amz-Signature=" in url

def test_generate_presigned_put_url_with_content_length(test_storage):
    """Test: Presigned PUT URL signs ContentLength to prevent oversized binary uploads."""
    url = test_storage.generate_presigned_put_url(
        key="users/123/moments/slot_1.webp",
        content_type="image/webp",
        content_length=2048000,
        expires_in=300,
    )
    assert "content-length" in url.lower()

def test_generate_presigned_get_url(test_storage):
    """Test 2: Signed GET URL generates with specified expiry for private assets."""
    url = test_storage.generate_presigned_get_url(
        key="users/123/kyc/frame_01.webp",
        expires_in=3600,
    )
    assert "https://test-account.r2.cloudflarestorage.com/ur-heart-media/users/123/kyc/frame_01.webp" in url
    assert "X-Amz-Expires=3600" in url
    assert "X-Amz-Signature=" in url

def test_get_public_cdn_url(test_storage):
    """Test 3: Returns formatted Edge CDN URL with https://media.urheart.app."""
    # Without leading slash
    assert (
        test_storage.get_public_cdn_url("users/123/avatar/primary.webp")
        == "https://media.urheart.app/users/123/avatar/primary.webp"
    )
    # With leading slash
    assert (
        test_storage.get_public_cdn_url("/users/123/avatar/primary.webp")
        == "https://media.urheart.app/users/123/avatar/primary.webp"
    )

def test_delete_object(test_storage):
    """Test 4: delete_object calls S3 delete_object on bucket and key."""
    stubber = Stubber(test_storage.s3_client)
    expected_params = {
        "Bucket": "ur-heart-media",
        "Key": "users/123/moments/slot_1.webp",
    }
    stubber.add_response("delete_object", {}, expected_params)
    with stubber:
        res = test_storage.delete_object("users/123/moments/slot_1.webp")
        assert res is True

def test_delete_objects_by_prefix(test_storage):
    """Test 5: delete_objects_by_prefix lists and batch removes objects under prefix."""
    stubber = Stubber(test_storage.s3_client)
    list_response = {
        "Contents": [
            {"Key": "users/123/avatar/primary.webp"},
            {"Key": "users/123/moments/slot_1.webp"},
        ]
    }
    stubber.add_response(
        "list_objects_v2",
        list_response,
        {"Bucket": "ur-heart-media", "Prefix": "users/123/"},
    )
    delete_response = {
        "Deleted": [
            {"Key": "users/123/avatar/primary.webp"},
            {"Key": "users/123/moments/slot_1.webp"},
        ]
    }
    stubber.add_response(
        "delete_objects",
        delete_response,
        {
            "Bucket": "ur-heart-media",
            "Delete": {
                "Objects": [
                    {"Key": "users/123/avatar/primary.webp"},
                    {"Key": "users/123/moments/slot_1.webp"},
                ]
            },
        },
    )
    with stubber:
        count = test_storage.delete_objects_by_prefix("users/123/")
        assert count == 2

def test_delete_objects_by_prefix_reports_errors(test_storage):
    """Test: delete_objects_by_prefix raises RuntimeError on partial batch deletion failures."""
    stubber = Stubber(test_storage.s3_client)
    list_response = {
        "Contents": [
            {"Key": "users/123/moment.webp"},
        ]
    }
    stubber.add_response(
        "list_objects_v2",
        list_response,
        {"Bucket": "ur-heart-media", "Prefix": "users/123/"},
    )
    delete_response = {
        "Deleted": [],
        "Errors": [
            {"Key": "users/123/moment.webp", "Code": "AccessDenied", "Message": "Permission Denied"}
        ],
    }
    stubber.add_response(
        "delete_objects",
        delete_response,
        {
            "Bucket": "ur-heart-media",
            "Delete": {"Objects": [{"Key": "users/123/moment.webp"}]},
        },
    )
    with stubber:
        with pytest.raises(RuntimeError, match="R2 batch deletion failed"):
            test_storage.delete_objects_by_prefix("users/123/")

@pytest.mark.asyncio
async def test_presigned_url_requires_file_size_bytes(test_user, test_storage):
    """Test: Omitting file_size_bytes is strictly rejected with HTTP 422."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_storage_service] = lambda: test_storage
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/media/presigned-url",
                json={"asset_type": "moment", "slot_number": 1, "content_type": "image/webp"},
            )
            assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_presigned_url_slot_boundaries(test_user, test_storage):
    """Test 6: POST /api/v1/media/presigned-url rejects slot 6 (>5) and slot 0 (<1) with HTTP 422."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_storage_service] = lambda: test_storage
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp6 = await client.post(
                "/api/v1/media/presigned-url",
                json={
                    "asset_type": "moment",
                    "slot_number": 6,
                    "content_type": "image/webp",
                    "file_size_bytes": 102400,
                },
            )
            assert resp6.status_code == 422

            resp0 = await client.post(
                "/api/v1/media/presigned-url",
                json={
                    "asset_type": "moment",
                    "slot_number": 0,
                    "content_type": "image/webp",
                    "file_size_bytes": 102400,
                },
            )
            assert resp0.status_code == 422
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_presigned_url_moment_requires_slot(test_user, test_storage):
    """Test 7: POST /api/v1/media/presigned-url rejects moment without slot_number."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_storage_service] = lambda: test_storage
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/media/presigned-url",
                json={
                    "asset_type": "moment",
                    "content_type": "image/webp",
                    "file_size_bytes": 102400,
                },
            )
            assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_presigned_url_mime_type_validation(test_user, test_storage):
    """Test 8: Rejects non-WebP image types and non-AAC/M4A audio types."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_storage_service] = lambda: test_storage
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp_jpeg = await client.post(
                "/api/v1/media/presigned-url",
                json={
                    "asset_type": "moment",
                    "slot_number": 1,
                    "content_type": "image/jpeg",
                    "file_size_bytes": 102400,
                },
            )
            assert resp_jpeg.status_code == 422

            resp_voice = await client.post(
                "/api/v1/media/presigned-url",
                json={
                    "asset_type": "voice_spark",
                    "content_type": "image/webp",
                    "file_size_bytes": 102400,
                },
            )
            assert resp_voice.status_code == 422
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_presigned_url_file_size_limits(test_user, test_storage):
    """Test: Rejects payload sizes exceeding 5 MB for images and 10 MB for voice sparks."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_storage_service] = lambda: test_storage
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 6 MB image exceeds 5 MB limit
            resp_large_img = await client.post(
                "/api/v1/media/presigned-url",
                json={
                    "asset_type": "moment",
                    "slot_number": 1,
                    "content_type": "image/webp",
                    "file_size_bytes": 6 * 1024 * 1024,
                },
            )
            assert resp_large_img.status_code == 422

            # 12 MB voice exceeds 10 MB limit
            resp_large_voice = await client.post(
                "/api/v1/media/presigned-url",
                json={
                    "asset_type": "voice_spark",
                    "content_type": "audio/m4a",
                    "file_size_bytes": 12 * 1024 * 1024,
                },
            )
            assert resp_large_voice.status_code == 422

            # Valid 2 MB image succeeds
            resp_valid = await client.post(
                "/api/v1/media/presigned-url",
                json={
                    "asset_type": "moment",
                    "slot_number": 1,
                    "content_type": "image/webp",
                    "file_size_bytes": 2 * 1024 * 1024,
                },
            )
            assert resp_valid.status_code == 200
            assert "content-length" in resp_valid.json()["upload_url"].lower()
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_presigned_url_endpoint_success(test_user, test_storage):
    """Test 9: Successfully returns upload_url and public_cdn_url structure for valid requests."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_storage_service] = lambda: test_storage
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/media/presigned-url",
                json={
                    "asset_type": "moment",
                    "slot_number": 3,
                    "content_type": "image/webp",
                    "file_size_bytes": 500000,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert f"users/{test_user.id}/moments/slot_3.webp" in data["upload_url"]
            assert data["public_cdn_url"] == f"https://media.urheart.app/users/{test_user.id}/moments/slot_3.webp"
            assert data["object_key"] == f"users/{test_user.id}/moments/slot_3.webp"
            assert data["expires_in"] == 300
            assert data["max_bytes"] == 5 * 1024 * 1024

            resp_avatar = await client.post(
                "/api/v1/media/presigned-url",
                json={
                    "asset_type": "avatar",
                    "content_type": "image/webp",
                    "file_size_bytes": 250000,
                },
            )
            assert resp_avatar.status_code == 200
            data_avatar = resp_avatar.json()
            assert data_avatar["object_key"] == f"users/{test_user.id}/avatar/primary.webp"

            resp_voice = await client.post(
                "/api/v1/media/presigned-url",
                json={
                    "asset_type": "voice_spark",
                    "content_type": "audio/m4a",
                    "file_size_bytes": 1500000,
                },
            )
            assert resp_voice.status_code == 200
            data_voice = resp_voice.json()
            assert data_voice["object_key"] == f"users/{test_user.id}/voice/spark.m4a"
            assert data_voice["max_bytes"] == 10 * 1024 * 1024
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_delete_moment_endpoint(test_user):
    """Test 10: DELETE /api/v1/media/moment/{slot} removes photo and updates profile photos off the event loop."""
    mock_storage = MagicMock()
    mock_storage.delete_object.return_value = True

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_storage_service] = lambda: mock_storage
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/api/v1/media/moment/1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["slot_number"] == 1
            assert data["deleted"] is True

            mock_storage.delete_object.assert_called_once_with(
                f"users/{test_user.id}/moments/slot_1.webp"
            )
            assert not any("slot_1.webp" in p for p in test_user.photos)
            assert any("slot_2.webp" in p for p in test_user.photos)
            mock_db.commit.assert_awaited_once()

            resp_invalid = await client.delete("/api/v1/media/moment/9")
            assert resp_invalid.status_code == 422
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_voice_spark_redirect_endpoint(test_user, test_storage):
    """Test 11: GET /api/v1/media/voice/{user_id}/{filename} performs HTTP 307 redirect for authorized self-access."""
    app.dependency_overrides[get_storage_service] = lambda: test_storage
    app.dependency_overrides[get_current_user] = lambda: test_user
    user_id = test_user.id
    filename = "spark.m4a"
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            resp = await client.get(f"/api/v1/media/voice/{user_id}/{filename}")
            assert resp.status_code == 307
            location = resp.headers.get("location")
            assert f"users/{user_id}/voice/{filename}" in location
            assert "X-Amz-Signature=" in location
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_voice_spark_redirect_unauthorized(test_user, test_storage):
    """Test 12: GET /api/v1/media/voice/{user_id}/{filename} rejects unauthorized seeker with HTTP 403."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None  # No mutual match found
    mock_db.execute.return_value = mock_res

    app.dependency_overrides[get_storage_service] = lambda: test_storage
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db
    unauthorized_target_id = uuid.uuid4()
    filename = "spark.m4a"
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            resp = await client.get(f"/api/v1/media/voice/{unauthorized_target_id}/{filename}")
            assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
