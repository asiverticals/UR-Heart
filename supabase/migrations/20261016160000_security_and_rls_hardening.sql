-- ==============================================================================
-- Migration: 20261016160000_security_and_rls_hardening.sql
-- Subsystem: Supabase PostgreSQL Database Security & Row Level Security (RLS)
-- Purpose: Remediate critical and high-severity access control & RLS vulnerabilities:
--          1. SEC-VULN-12: Split public.data_export_requests over-permissive FOR ALL
--             policy into distinct FOR SELECT and FOR INSERT policies scoped to owner.
--          2. SEC-VULN-12: Restrict column update privileges on public.photo_reveal_consents
--             to (status, updated_at) and add status validation in WITH CHECK.
--          3. SEC-VULN-14: Deploy public.is_match_participant(UUID) without is_active requirement
--             and update public.messages SELECT policy so dialogue history is preserved post-closure.
--          4. SEC-VULN-03: Establish dedicated unprivileged database application role `urheart_app`.
--          5. SEC-VULN-12: Harden public.consumed_magic_tokens with explicit service_role policy
--             and revoke anon/authenticated permissions.
-- ==============================================================================

-- 1. Split data_export_requests policy into dedicated SELECT and INSERT policies
DO $$
BEGIN
    DROP POLICY IF EXISTS "data_export_all_owner" ON public.data_export_requests;
    DROP POLICY IF EXISTS "data_export_select_owner" ON public.data_export_requests;
    DROP POLICY IF EXISTS "data_export_insert_owner" ON public.data_export_requests;
    DROP POLICY IF EXISTS "data_export_service_role" ON public.data_export_requests;

    -- Authenticated seekers may only read their own export requests
    CREATE POLICY "data_export_select_owner" ON public.data_export_requests
        FOR SELECT TO authenticated
        USING (user_id = public.get_current_user_id());

    -- Authenticated seekers may only create new export requests for themselves
    CREATE POLICY "data_export_insert_owner" ON public.data_export_requests
        FOR INSERT TO authenticated
        WITH CHECK (user_id = public.get_current_user_id());

    -- Administrative service role retains full management for generating archives
    CREATE POLICY "data_export_service_role" ON public.data_export_requests
        FOR ALL TO service_role
        USING (TRUE)
        WITH CHECK (TRUE);
END $$;


-- 2. Harden photo_reveal_consents column permissions and update policy
REVOKE ALL ON public.photo_reveal_consents FROM authenticated;
GRANT SELECT, INSERT ON public.photo_reveal_consents TO authenticated;
GRANT UPDATE (status, updated_at) ON public.photo_reveal_consents TO authenticated;

DO $$
BEGIN
    DROP POLICY IF EXISTS "photo_reveal_update_target" ON public.photo_reveal_consents;

    CREATE POLICY "photo_reveal_update_target" ON public.photo_reveal_consents
        FOR UPDATE TO authenticated
        USING (target_id = public.get_current_user_id())
        WITH CHECK (
            target_id = public.get_current_user_id()
            AND status IN ('accepted', 'rejected', 'pending', 'revealed')
        );
END $$;


-- 3. Deploy is_match_participant() helper & update messages SELECT policy
CREATE OR REPLACE FUNCTION public.is_match_participant(p_match_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1 
        FROM public.matches m
        JOIN public.users u ON u.auth_id = auth.uid() AND u.deleted_at IS NULL
        WHERE m.id = p_match_id
          AND (m.user1_id = u.id OR m.user2_id = u.id)
    );
$$;

DO $$
BEGIN
    DROP POLICY IF EXISTS "messages_select_participants" ON public.messages;

    CREATE POLICY "messages_select_participants" ON public.messages
        FOR SELECT TO authenticated
        USING (public.is_match_participant(match_id));
END $$;


-- 4. Establish dedicated unprivileged application user `urheart_app`
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'urheart_app') THEN
        CREATE ROLE urheart_app WITH LOGIN PASSWORD 'urheart_app_secure_local_dev_pwd';
    END IF;
END $$;

GRANT CONNECT ON DATABASE postgres TO urheart_app;
GRANT USAGE ON SCHEMA public TO urheart_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO urheart_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO urheart_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO urheart_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO urheart_app;


-- 5. Harden consumed_magic_tokens table against unauthorized access
REVOKE ALL ON public.consumed_magic_tokens FROM anon, authenticated;

DO $$
BEGIN
    DROP POLICY IF EXISTS "consumed_tokens_service_role" ON public.consumed_magic_tokens;

    CREATE POLICY "consumed_tokens_service_role" ON public.consumed_magic_tokens
        FOR ALL TO service_role
        USING (TRUE)
        WITH CHECK (TRUE);
END $$;
