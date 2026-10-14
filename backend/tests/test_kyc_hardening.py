import json
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from fastapi import BackgroundTasks
from sqlalchemy import select

from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.core.exceptions import SanctuaryException
from backend.app.main import app
from backend.app.models.domain.admin_telemetry import AdminKycEscalation
from backend.app.models.domain.user import User
from backend.app.services.kyc_service import KycService, get_kyc_service
from backend.app.services.storage_service import CloudflareR2StorageService, get_storage_service

@pytest.fixture
def mock_storage():
    storage = MagicMock(spec=CloudflareR2StorageService)
    storage.public_domain = "https://media.urheart.app"
    storage.bucket_name = "ur-heart-media"
    storage.generate_presigned_put_url.side_effect = (
        lambda key, content_type="image/webp", expires_in=120: f"https://r2.cloudflare.com/put/{key}"
    )
    storage.get_public_cdn_url.side_effect = (
        lambda key: f"https://media.urheart.app/{key}"
    )
    storage.get_object_bytes.return_value = b"\x89PNG\r\n\x1a\nfake_image_bytes"
    storage.put_object_bytes.return_value = True
    storage.delete_object.return_value = True
    return storage

@pytest.mark.asyncio
async def test_kyc_approved_score_92(db_session, make_user, mock_storage):
    """Test 1: Score >= 80 automatically sets user.kyc_status = True and returns approved."""
    test_user = make_user(
        photos=["https://media.urheart.app/users/test/moments/slot_1.webp"],
        kyc_status=False,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "match_score": 92,
                        "is_live_person": True,
                        "reasoning": "High facial alignment, natural depth gradient, live capture confirmed.",
                    })
                }
            }
        ]
    }
    mock_http.post.return_value = mock_resp

    kyc_svc = KycService(
        storage=mock_storage,
        http_client=mock_http,
        groq_api_key="gsk_test_key_12345",
    )

    bg_tasks = BackgroundTasks()
    res = await kyc_svc.process_kyc_submission(
        user=test_user,
        live_video_key=f"kyc_temp/{test_user.id}/liveness_abc.webp",
        background_tasks=bg_tasks,
        session=db_session,
    )

    assert res["success"] is True
    assert res["status"] == "approved"
    assert res["score"] == 92
    assert test_user.kyc_status is True

@pytest.mark.asyncio
async def test_kyc_escalated_score_65(db_session, make_user, mock_storage):
    """Test 2: Score 50 <= score < 80 keeps kyc_status = False and creates AdminKycEscalation."""
    test_user = make_user(
        photos=["https://media.urheart.app/users/test/moments/slot_1.webp"],
        kyc_status=False,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "match_score": 65,
                        "is_live_person": True,
                        "reasoning": "Partial shadow on jawline, borderline facial symmetry.",
                    })
                }
            }
        ]
    }
    mock_http.post.return_value = mock_resp

    kyc_svc = KycService(
        storage=mock_storage,
        http_client=mock_http,
        groq_api_key="gsk_test_key_12345",
    )

    bg_tasks = BackgroundTasks()
    res = await kyc_svc.process_kyc_submission(
        user=test_user,
        live_video_key=f"kyc_temp/{test_user.id}/liveness_borderline.webp",
        background_tasks=bg_tasks,
        session=db_session,
    )

    assert res["success"] is True
    assert res["status"] == "escalated"
    assert res["score"] == 65
    assert test_user.kyc_status is False

    # Assert escalation record created in DB
    stmt = select(AdminKycEscalation).where(AdminKycEscalation.user_id == test_user.id)
    result = await db_session.execute(stmt)
    escalation = result.scalar_one_or_none()
    assert escalation is not None
    assert escalation.status == "pending"
    assert float(escalation.groq_match_score) == pytest.approx(0.65, abs=0.01)
    assert escalation.selfie_storage_url.startswith(f"kyc_escalations/{test_user.id}/")
    mock_storage.put_object_bytes.assert_called_once()

@pytest.mark.asyncio
async def test_kyc_rejected_score_30(db_session, make_user, mock_storage):
    """Test 3: Score < 50 rejects verification and leaves kyc_status = False."""
    test_user = make_user(
        photos=["https://media.urheart.app/users/test/moments/slot_1.webp"],
        kyc_status=False,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "match_score": 30,
                        "is_live_person": False,
                        "reasoning": "Screen glare detected, 2D presentation spoof suspected.",
                    })
                }
            }
        ]
    }
    mock_http.post.return_value = mock_resp

    kyc_svc = KycService(
        storage=mock_storage,
        http_client=mock_http,
        groq_api_key="gsk_test_key_12345",
    )

    bg_tasks = BackgroundTasks()
    res = await kyc_svc.process_kyc_submission(
        user=test_user,
        live_video_key=f"kyc_temp/{test_user.id}/liveness_spoof.webp",
        background_tasks=bg_tasks,
        session=db_session,
    )

    assert res["success"] is False
    assert res["status"] == "rejected"
    assert res["score"] == 30
    assert test_user.kyc_status is False

@pytest.mark.asyncio
async def test_ephemeral_biometric_purge_invoked(mock_storage):
    """Test 4: Programmatic delete_object is called for ephemeral key within <60s SLA."""
    kyc_svc = KycService(storage=mock_storage)
    temp_key = "kyc_temp/user_123/liveness_xyz.webp"

    purged = await kyc_svc.purge_ephemeral_biometrics(temp_key)
    assert purged is True
    mock_storage.delete_object.assert_called_once_with(temp_key)

@pytest.mark.asyncio
async def test_kyc_endpoints_integration(db_session, make_user, mock_storage):
    """Test 5: Full integration test of /presigned-upload, /verify-liveness, and /status endpoints."""
    test_user = make_user(
        photos=["https://media.urheart.app/users/test/moments/slot_1.webp"],
        kyc_status=False,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    mock_kyc = MagicMock(spec=KycService)
    mock_kyc.process_kyc_submission = AsyncMock(return_value={
        "success": True,
        "status": "approved",
        "score": 90,
        "message": "Sacred identity verified.",
        "reasoning": "Authentic match",
    })

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_storage_service] = lambda: mock_storage
    app.dependency_overrides[get_kyc_service] = lambda: mock_kyc

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Presigned Upload
            up_resp = await client.post("/api/v1/kyc/presigned-upload")
            assert up_resp.status_code == 200
            up_data = up_resp.json()
            assert "upload_url" in up_data
            assert up_data["object_key"].startswith(f"kyc_temp/{test_user.id}/")

            # 2. Verify Liveness - Cross tenant path blocked
            bad_resp = await client.post(
                "/api/v1/kyc/verify-liveness",
                json={"object_key": "kyc_temp/other_user_id/liveness_0123456789abcdef0123456789abcdef.webp"},
            )
            assert bad_resp.status_code == 403

            # 3. Verify Liveness - Path traversal blocked
            traversal_resp = await client.post(
                "/api/v1/kyc/verify-liveness",
                json={"object_key": f"kyc_temp/{test_user.id}/../../etc/passwd"},
            )
            assert traversal_resp.status_code == 403

            # 4. Verify Liveness - Valid key
            good_resp = await client.post(
                "/api/v1/kyc/verify-liveness",
                json={"object_key": up_data["object_key"]},
            )
            assert good_resp.status_code == 200
            good_data = good_resp.json()
            assert good_data["status"] == "approved"
            assert good_data["score"] == 90

            # 5. Status Check
            status_resp = await client.get("/api/v1/kyc/status")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            assert "kyc_status" in status_data
            assert "has_pending_escalation" in status_data
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_kyc_purge_scheduled_even_on_exception(db_session, make_user, mock_storage):
    """Test 6: Ephemeral purge is scheduled in finally block even if liveness evaluation fails."""
    test_user = make_user(
        photos=["https://media.urheart.app/users/test/moments/slot_1.webp"],
        kyc_status=False,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    # Simulate Groq API throwing an exception / timeout
    mock_http.post.side_effect = httpx.ConnectTimeout("Groq API timeout")

    kyc_svc = KycService(
        storage=mock_storage,
        http_client=mock_http,
        groq_api_key="gsk_test_key_12345",
    )

    bg_tasks = BackgroundTasks()
    temp_key = f"kyc_temp/{test_user.id}/liveness_fail.webp"

    with pytest.raises(SanctuaryException):
        await kyc_svc.process_kyc_submission(
            user=test_user,
            live_video_key=temp_key,
            background_tasks=bg_tasks,
            session=db_session,
        )

    # Confirm purge was scheduled despite exception
    assert len(bg_tasks.tasks) == 1
    assert bg_tasks.tasks[0].func == kyc_svc.purge_ephemeral_biometrics
    assert bg_tasks.tasks[0].args == (temp_key,)

@pytest.mark.asyncio
async def test_kyc_anchor_fetch_blocks_ssrf_and_foreign_keys(db_session, make_user, mock_storage):
    """Test 7: Anchor retrieval rejects foreign URLs/keys and never performs direct HTTP requests."""
    test_user = make_user(
        photos=["http://169.254.169.254/latest/meta-data/"],
        kyc_status=False,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    kyc_svc = KycService(
        storage=mock_storage,
        http_client=mock_http,
        groq_api_key="gsk_test_key_12345",
    )

    # When photos[0] is an arbitrary URL, _fetch_anchor_bytes ignores it and fetches users/{id}/moments/slot_1.webp
    bytes_result = await kyc_svc._fetch_anchor_bytes(test_user)
    assert bytes_result == b"\x89PNG\r\n\x1a\nfake_image_bytes"
    mock_http.get.assert_not_called()
    mock_storage.get_object_bytes.assert_called_with(f"users/{test_user.id}/moments/slot_1.webp")

@pytest.mark.asyncio
async def test_kyc_reescalation_purges_previous_escalation_frame(db_session, make_user, mock_storage):
    """Test 8: Re-escalation schedules deletion of the stale prior escalation frame in background tasks."""
    test_user = make_user(
        photos=["https://media.urheart.app/users/test/moments/slot_1.webp"],
        kyc_status=False,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    old_escalation_key = f"kyc_escalations/{test_user.id}/review_old_123.webp"
    existing_ticket = AdminKycEscalation(
        user_id=test_user.id,
        declared_dob=test_user.dob,
        groq_match_score=Decimal("0.600"),
        selfie_storage_url=old_escalation_key,
        id_card_storage_url="https://media.urheart.app/users/test/moments/slot_1.webp",
        status="pending",
    )
    db_session.add(existing_ticket)
    await db_session.commit()

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "match_score": 68,
                        "is_live_person": True,
                        "reasoning": "Subtle lighting variance, borderline confidence.",
                    })
                }
            }
        ]
    }
    mock_http.post.return_value = mock_resp

    kyc_svc = KycService(
        storage=mock_storage,
        http_client=mock_http,
        groq_api_key="gsk_test_key_12345",
    )

    bg_tasks = BackgroundTasks()
    live_temp_key = f"kyc_temp/{test_user.id}/liveness_retry.webp"

    res = await kyc_svc.process_kyc_submission(
        user=test_user,
        live_video_key=live_temp_key,
        background_tasks=bg_tasks,
        session=db_session,
    )

    assert res["status"] == "escalated"
    assert res["score"] == 68

    # Verify both the ephemeral temp key AND the previous stale escalation key are queued for purge
    purged_keys = [task.args[0] for task in bg_tasks.tasks if task.func == kyc_svc.purge_ephemeral_biometrics]
    assert live_temp_key in purged_keys
    assert old_escalation_key in purged_keys
