import asyncio
import uuid
import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select

from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.core.ws_manager import connection_manager
from backend.app.main import app
from backend.app.models.domain.match_and_chat import Match, Message
from backend.app.models.domain.user import User


@pytest.mark.asyncio
async def test_close_with_grace_success(db_session, make_user):
    """Test 1: User calls /close-with-grace with valid template -> updates to closed_with_grace & is_active=False."""
    user1 = make_user(full_name="User Alpha", is_profile_completed=True)
    user2 = make_user(full_name="User Beta", is_profile_completed=True)
    db_session.add_all([user1, user2])
    await db_session.commit()

    # Invariant: user1_id < user2_id in DB check constraint
    p1, p2 = (user1.id, user2.id) if user1.id < user2.id else (user2.id, user1.id)
    match = Match(
        user1_id=p1,
        user2_id=p2,
        is_active=True,
        closure_status="active",
    )
    db_session.add(match)
    await db_session.commit()
    await db_session.refresh(match)

    app.dependency_overrides[get_current_user] = lambda: user1
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/chat/close-with-grace",
                json={
                    "match_id": str(match.id),
                    "closure_template_key": "grace_paths_diverge",
                    "closure_note": "Wishing you peace and fulfillment.",
                },
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["success"] is True
            assert "closed_at" in data

            # Verify database state
            stmt = select(Match).where(Match.id == match.id)
            updated_match = (await db_session.execute(stmt)).scalar_one()
            assert updated_match.is_active is False
            assert updated_match.closure_status == "closed_with_grace"
            assert updated_match.closed_by_user_id == user1.id
            assert updated_match.closure_template_key == "grace_paths_diverge"
            assert updated_match.closure_note == "Wishing you peace and fulfillment."
            assert updated_match.closed_at is not None
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_close_with_grace_non_participant_forbidden(db_session, make_user):
    """Test 2: Non-participant cannot close the match (raises HTTP 403)."""
    user1 = make_user(full_name="User Alpha", is_profile_completed=True)
    user2 = make_user(full_name="User Beta", is_profile_completed=True)
    outsider = make_user(full_name="User Outsider", is_profile_completed=True)
    db_session.add_all([user1, user2, outsider])
    await db_session.commit()

    p1, p2 = (user1.id, user2.id) if user1.id < user2.id else (user2.id, user1.id)
    match = Match(user1_id=p1, user2_id=p2, is_active=True, closure_status="active")
    db_session.add(match)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: outsider
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/chat/close-with-grace",
                json={
                    "match_id": str(match.id),
                    "closure_template_key": "grace_not_aligned",
                },
            )
            assert resp.status_code == 403
            err = resp.json()
            assert err["error_code"] == "FORBIDDEN_NOT_PARTICIPANT"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_close_with_grace_idempotency(db_session, make_user):
    """Test 3: Closing an already closed match returns idempotent success without error."""
    user1 = make_user(full_name="User Alpha", is_profile_completed=True)
    user2 = make_user(full_name="User Beta", is_profile_completed=True)
    db_session.add_all([user1, user2])
    await db_session.commit()

    p1, p2 = (user1.id, user2.id) if user1.id < user2.id else (user2.id, user1.id)
    match = Match(user1_id=p1, user2_id=p2, is_active=True, closure_status="active")
    db_session.add(match)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user2
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # First closure
            r1 = await client.post(
                "/api/v1/chat/close-with-grace",
                json={
                    "match_id": str(match.id),
                    "closure_template_key": "grace_holding_space",
                },
            )
            assert r1.status_code == 200

            # Second closure (idempotent call)
            r2 = await client.post(
                "/api/v1/chat/close-with-grace",
                json={
                    "match_id": str(match.id),
                    "closure_template_key": "grace_holding_space",
                },
            )
            assert r2.status_code == 200
            assert r2.json()["data"]["success"] is True
            assert r2.json()["data"].get("idempotent") is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_close_with_grace_invalid_template(db_session, make_user):
    """Test 4: Invalid template key raises HTTP 400 INVALID_CLOSURE_TEMPLATE."""
    user1 = make_user(full_name="User Alpha", is_profile_completed=True)
    user2 = make_user(full_name="User Beta", is_profile_completed=True)
    db_session.add_all([user1, user2])
    await db_session.commit()

    p1, p2 = (user1.id, user2.id) if user1.id < user2.id else (user2.id, user1.id)
    match = Match(user1_id=p1, user2_id=p2, is_active=True, closure_status="active")
    db_session.add(match)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user1
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/chat/close-with-grace",
                json={
                    "match_id": str(match.id),
                    "closure_template_key": "grace_invalid_bogus_key",
                },
            )
            assert resp.status_code == 400
            assert resp.json()["error_code"] == "INVALID_CLOSURE_TEMPLATE"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_get_dialogue_messages_history(db_session, make_user):
    """Test 5: Fetch dialogue messages returns chronological list for participants and 403 for outsiders."""
    user1 = make_user(full_name="User Alpha", is_profile_completed=True)
    user2 = make_user(full_name="User Beta", is_profile_completed=True)
    outsider = make_user(full_name="Outsider", is_profile_completed=True)
    db_session.add_all([user1, user2, outsider])
    await db_session.commit()

    p1, p2 = (user1.id, user2.id) if user1.id < user2.id else (user2.id, user1.id)
    match = Match(user1_id=p1, user2_id=p2, is_active=True, closure_status="active")
    db_session.add(match)
    await db_session.commit()

    # Add 2 messages
    m1 = Message(
        match_id=match.id,
        sender_id=user1.id,
        encrypted_text="Ciphertext_Alpha_1",
        status="delivered",
    )
    m2 = Message(
        match_id=match.id,
        sender_id=user2.id,
        encrypted_text="Ciphertext_Beta_2",
        status="sent",
    )
    db_session.add_all([m1, m2])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user1
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Participant fetch
            res = await client.get(f"/api/v1/chat/messages/{match.id}")
            assert res.status_code == 200
            data = res.json()["data"]
            assert len(data) == 2
            assert data[0]["encrypted_text"] == "Ciphertext_Alpha_1"
            assert data[1]["encrypted_text"] == "Ciphertext_Beta_2"

            # Outsider fetch
            app.dependency_overrides[get_current_user] = lambda: outsider
            bad_res = await client.get(f"/api/v1/chat/messages/{match.id}")
            assert bad_res.status_code == 403
            assert bad_res.json()["error_code"] == "FORBIDDEN_NOT_PARTICIPANT"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
