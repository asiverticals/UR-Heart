"""
Milestone 4: Supabase Database RLS & Policy Hardening Verification Tests.

Verifies:
1. Migration 20261016160000_security_and_rls_hardening.sql exists, is well-formed, and contains:
   - SEC-VULN-12: data_export_requests policy split into dedicated SELECT and INSERT policies.
   - SEC-VULN-12: photo_reveal_consents column-level GRANTs (status, updated_at) and WITH CHECK status validation.
   - SEC-VULN-14: is_match_participant() function definition and messages_select_participants updated policy.
   - SEC-VULN-03: urheart_app unprivileged application role creation with proper schema privileges.
   - consumed_magic_tokens RLS service_role policy and anon/authenticated revocation.
2. Historical messages query integrity:
   - Messages for an inactive/closed match can still be retrieved by participants via application queries.
"""

from pathlib import Path
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.domain.match_and_chat import Match, Message
from backend.app.models.domain.user import User


def test_m4_migration_file_exists_and_covers_all_security_remediations():
    """Verify migration 20261016160000_security_and_rls_hardening.sql exists and covers all SEC vulnerabilities."""
    migration_path = (
        Path(__file__).resolve().parent.parent.parent
        / "supabase"
        / "migrations"
        / "20261016160000_security_and_rls_hardening.sql"
    )
    assert migration_path.exists(), f"Migration file missing at {migration_path}"
    content = migration_path.read_text(encoding="utf-8")

    # 1. data_export_requests policy split
    assert "data_export_select_owner" in content
    assert "data_export_insert_owner" in content
    assert "DROP POLICY IF EXISTS \"data_export_all_owner\"" in content
    assert "FOR SELECT TO authenticated" in content
    assert "FOR INSERT TO authenticated" in content

    # 2. photo_reveal_consents hardening
    assert "GRANT UPDATE (status, updated_at) ON public.photo_reveal_consents TO authenticated;" in content
    assert "photo_reveal_update_target" in content
    assert "WITH CHECK" in content
    assert "'accepted', 'rejected', 'pending', 'revealed'" in content

    # 3. is_match_participant helper and messages SELECT policy
    assert "FUNCTION public.is_match_participant(p_match_id UUID)" in content
    assert "messages_select_participants" in content
    assert "public.is_match_participant(match_id)" in content

    # 4. urheart_app unprivileged role
    assert "CREATE ROLE urheart_app" in content
    assert "GRANT CONNECT ON DATABASE postgres TO urheart_app;" in content
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO urheart_app;" in content

    # 5. consumed_magic_tokens table hardening
    assert "REVOKE ALL ON public.consumed_magic_tokens FROM anon, authenticated;" in content
    assert "consumed_tokens_service_role" in content


@pytest.mark.asyncio
async def test_historical_messages_accessible_on_closed_match(db_session: AsyncSession, make_user):
    """Verify participants can query historical messages after match closure (SEC-VULN-14 requirement)."""
    uid1 = uuid.uuid4()
    uid2 = uuid.uuid4()
    if uid1 > uid2:
        uid1, uid2 = uid2, uid1

    user1 = make_user(id=uid1, full_name="Historic Seeker 1", is_profile_completed=True)
    user2 = make_user(id=uid2, full_name="Historic Seeker 2", is_profile_completed=True)
    db_session.add_all([user1, user2])
    await db_session.flush()

    # Closed match
    closed_match = Match(
        id=uuid.uuid4(),
        user1_id=user1.id,
        user2_id=user2.id,
        is_active=False,
        closure_status="closed_with_grace",
        closed_by_user_id=user1.id,
    )
    db_session.add(closed_match)
    await db_session.flush()

    # Dialogue messages previously sent in that match
    msg1 = Message(
        match_id=closed_match.id,
        sender_id=user1.id,
        encrypted_text="Farewell and safe journey.",
        status="delivered",
    )
    msg2 = Message(
        match_id=closed_match.id,
        sender_id=user2.id,
        encrypted_text="Thank you, take care.",
        status="delivered",
    )
    db_session.add_all([msg1, msg2])
    await db_session.commit()

    # Query messages for this closed match where participant is user1 or user2
    stmt = (
        select(Message)
        .join(Match, Match.id == Message.match_id)
        .where(
            Message.match_id == closed_match.id,
            (Match.user1_id == user1.id) | (Match.user2_id == user1.id),
        )
        .order_by(Message.created_at)
    )
    res = await db_session.execute(stmt)
    messages = res.scalars().all()

    assert len(messages) == 2
    assert messages[0].encrypted_text == "Farewell and safe journey."
    assert messages[1].encrypted_text == "Thank you, take care."
