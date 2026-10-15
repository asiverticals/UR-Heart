import hashlib
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.core.security import create_access_token
from backend.app.main import app
from backend.app.models.domain import (
    DataNominee,
    DeviceFcmToken,
    Match,
    Message,
    Swipe,
    User,
    WebDeletionToken,
)
from backend.app.services.account_incineration_service import (
    AccountIncinerationService,
    account_incineration_service,
)
from backend.app.services.storage_service import storage_service


@pytest.mark.asyncio
async def test_confirmation_phrase_guard(db_session, make_user):
    """Test 1: Submitting an invalid confirmation phrase or oversized reason returns HTTP 422."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Incorrect phrase fails
            resp = await client.request(
                "DELETE",
                "/api/v1/legal/account",
                headers={"Authorization": f"Bearer {token}"},
                json={"confirmation_phrase": "delete"},
            )
            assert resp.status_code == 422

            # 2. Oversized reason (> 500 chars) fails validation
            resp_long = await client.request(
                "DELETE",
                "/api/v1/legal/account",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "confirmation_phrase": "PERMANENTLY INCINERATE",
                    "reason": "x" * 501,
                },
            )
            assert resp_long.status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_r2_cascade_deletion(db_session, make_user, monkeypatch):
    """Test 2: Verifies storage_service.delete_objects_by_prefix is called with users/{user_id}/ and kyc_temp/{user_id}/."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    mock_delete_prefix = MagicMock(return_value=5)
    monkeypatch.setattr(storage_service, "delete_objects_by_prefix", mock_delete_prefix)

    service = AccountIncinerationService(storage=storage_service)
    result = await service.execute_account_incineration(user.id, db_session)

    assert result["success"] is True
    assert "certificate" in result
    assert result["certificate"].startswith("DPDP-INCINERATE-")

    mock_delete_prefix.assert_any_call(f"users/{user.id}/")
    mock_delete_prefix.assert_any_call(f"kyc_temp/{user.id}/")
    assert mock_delete_prefix.call_count == 2

    # Verify storage errors are NOT swallowed
    failing_user = make_user()
    db_session.add(failing_user)
    await db_session.commit()

    failing_storage = MagicMock()
    failing_storage.delete_objects_by_prefix.side_effect = RuntimeError("R2 connection lost")
    failing_service = AccountIncinerationService(storage=failing_storage)

    with pytest.raises(RuntimeError, match="R2 connection lost"):
        await failing_service.execute_account_incineration(failing_user.id, db_session)


@pytest.mark.asyncio
async def test_relational_cleanliness(db_session, make_user, monkeypatch):
    """Test 3: Verifies that after incineration, queries for users, swipes, device_fcm_tokens, and data_nominees return 0 rows."""
    u1 = make_user()
    u2 = make_user()
    if u1.id > u2.id:
        u1, u2 = u2, u1
    db_session.add_all([u1, u2])
    await db_session.commit()

    # Create associated child records
    fcm = DeviceFcmToken(user_id=u1.id, token="fake_fcm_token_123", platform="android")
    nominee = DataNominee(
        user_id=u1.id,
        nominee_name="Nominee Seeker",
        nominee_contact="nominee@urheart.app",
        relationship="Sibling",
    )
    swipe = Swipe(actor_id=u1.id, target_id=u2.id, swipe_type="like")
    db_session.add_all([fcm, nominee, swipe])
    await db_session.commit()

    # Mock R2 delete
    monkeypatch.setattr(storage_service, "delete_objects_by_prefix", MagicMock(return_value=0))

    # Execute full incineration via API
    token = create_access_token(u1.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.request(
                "DELETE",
                "/api/v1/legal/account",
                headers={"Authorization": f"Bearer {token}"},
                json={"confirmation_phrase": "PERMANENTLY INCINERATE", "reason": "Moving on"},
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["status"] == "incinerated"
    finally:
        app.dependency_overrides.pop(get_db, None)

    # Verify 0 rows in child tables and users
    res_user = await db_session.execute(select(User).where(User.id == u1.id))
    assert res_user.scalar_one_or_none() is None

    res_fcm = await db_session.execute(select(DeviceFcmToken).where(DeviceFcmToken.user_id == u1.id))
    assert res_fcm.scalar_one_or_none() is None

    res_nominee = await db_session.execute(select(DataNominee).where(DataNominee.user_id == u1.id))
    assert res_nominee.scalar_one_or_none() is None

    res_swipe = await db_session.execute(select(Swipe).where(Swipe.actor_id == u1.id))
    assert res_swipe.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_mutual_match_deactivation(db_session, make_user):
    """Test 4: Counterpart's active match transitions to is_active = FALSE and closure_status = 'peer_incinerated', and ALL dialogue messages are purged."""
    u1 = make_user()
    u2 = make_user()
    if u1.id > u2.id:
        u1, u2 = u2, u1
    db_session.add_all([u1, u2])
    await db_session.commit()

    match = Match(user1_id=u1.id, user2_id=u2.id, is_active=True, closure_status="active")
    db_session.add(match)
    await db_session.flush()

    # Both seeker and counterpart send messages
    msg1 = Message(match_id=match.id, sender_id=u1.id, encrypted_text="cipher_goodbye")
    msg2 = Message(match_id=match.id, sender_id=u2.id, encrypted_text="cipher_counterpart_reply")
    db_session.add_all([msg1, msg2])
    await db_session.commit()

    # Execute match deactivation step
    rows_affected = await account_incineration_service.deactivate_mutual_matches(u1.id, db_session)
    assert rows_affected >= 1
    await db_session.commit()

    # Refresh match to observe state transition
    stmt = select(Match).where(Match.id == match.id)
    updated_match = (await db_session.execute(stmt)).scalar_one()

    assert updated_match.is_active is False
    assert updated_match.closure_status == "peer_incinerated"

    # All dialogue messages across this match (both seeker's and counterpart's) are expunged
    stmt_msgs = select(Message).where(Message.match_id == match.id)
    remaining_messages = (await db_session.execute(stmt_msgs)).scalars().all()
    assert len(remaining_messages) == 0


@pytest.mark.asyncio
async def test_token_invalidation(db_session, make_user, monkeypatch):
    """Test 5: Calling /auth/me with an incinerated user's JWT bearer token immediately returns HTTP 401."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id)
    monkeypatch.setattr(storage_service, "delete_objects_by_prefix", MagicMock(return_value=0))

    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # First verify /auth/me succeeds while user exists
            resp_active = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp_active.status_code == 200

            # Execute incineration
            await account_incineration_service.execute_account_incineration(user.id, db_session)

            # Subsequent call with the same token must fail with 401
            resp_incinerated = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp_incinerated.status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_web_deletion_loop(db_session, make_user, monkeypatch):
    """Test 6: Web magic link generation with SHA-256 hashing and confirmation triggers complete account eradication."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    monkeypatch.setattr(storage_service, "delete_objects_by_prefix", MagicMock(return_value=0))
    app.dependency_overrides[get_db] = lambda: db_session

    # Spy on email dispatch to capture generated token link
    dispatched_links = []

    async def mock_send_email(email: str, url: str) -> bool:
        dispatched_links.append(url)
        return True

    monkeypatch.setattr(
        account_incineration_service,
        "send_web_deletion_email",
        mock_send_email,
    )

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Dispatch web deletion request
            resp_dispatch = await client.post(
                "/api/v1/legal/web-account-deletion",
                json={"email": user.email, "reason": "Moving on"},
            )
            assert resp_dispatch.status_code == 200
            assert resp_dispatch.json()["data"]["dispatched"] is True
            assert len(dispatched_links) == 1

            raw_url = dispatched_links[0]
            raw_token = raw_url.split("token=")[1]
            token_sha256 = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

            # 2. Verify token is stored as SHA-256 hash in database, not plaintext
            stmt = select(WebDeletionToken).where(WebDeletionToken.user_id == user.id)
            token_record = (await db_session.execute(stmt)).scalar_one()
            assert token_record.token == token_sha256

            # 3. Confirm deletion via magic link token
            resp_confirm = await client.post(
                "/api/v1/legal/web-account-deletion/confirm",
                json={"token": raw_token},
            )
            assert resp_confirm.status_code == 200
            data = resp_confirm.json()["data"]
            assert data["status"] == "incinerated"
            assert "certificate" in data

            # 4. Verify user record and token record are completely expunged
            res_user = await db_session.execute(select(User).where(User.id == user.id))
            assert res_user.scalar_one_or_none() is None

            res_token = await db_session.execute(
                select(WebDeletionToken).where(WebDeletionToken.token == token_sha256)
            )
            assert res_token.scalar_one_or_none() is None
    finally:
        app.dependency_overrides.pop(get_db, None)
