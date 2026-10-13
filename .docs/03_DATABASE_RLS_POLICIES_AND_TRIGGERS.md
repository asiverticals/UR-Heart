1. Security Architecture & RLS Model Overview
UR-Heart Sanctuary uses a Zero-Trust Database Security Model on Supabase PostgreSQL 15+. Client-side direct access via Supabase Client (PostgREST) is constrained by strict Row Level Security (RLS).
MD

+ 1

Security Principles
Default Deny: Har table par ALTER TABLE ... ENABLE ROW LEVEL SECURITY; execute hota hai. Bina explicit matching policy ke koi bhi read, insert, update ya delete operation allow nahi hota.
MD

Context Mapping (auth.uid() to public.users.id): Supabase Auth user ID (auth.uid()) ko application profile UUID (public.users.id) me resolve karne ke liye optimized, indexed STABLE SECURITY DEFINER functions use kiye jaate hain.
MD

Privilege Separation: Elevated operations (jaise underage quarantine, web deletion token validation, system configuration) PostgREST public access se completely revoking hain aur strictly backend service_role execution context me run hoti hain.
MD

Anti-Tampering Guardrails: Critical columns (kyc_status, role, dob, subscription_tier, reward_balance, deleted_at) client context se kabhi update nahi ho sakte; database-level BEFORE UPDATE triggers unauthorized modifications ko block karte hain.
MD

1. Core Security Helper Functions
Ye helper functions policies ke andar repetitive queries aur sub-select overhead ko eliminate karte hain.

SQL

-- ============================================================================
-- 1. Resolve Current Authenticated User ID
-- ============================================================================
CREATE OR REPLACE FUNCTION public.get_current_user_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT id
    FROM public.users
    WHERE auth_id = auth.uid()
      AND deleted_at IS NULL
    LIMIT 1;
$$;

-- ============================================================================
-- 2. Verify Active Match Participation
-- ============================================================================
CREATE OR REPLACE FUNCTION public.is_active_match_participant(p_match_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.matches m
        JOIN public.users u ON u.auth_id = auth.uid()
        WHERE m.id = p_match_id
          AND m.is_active = TRUE
          AND (m.user1_id = u.id OR m.user2_id = u.id)
    );
$$;

-- ============================================================================
-- 3. Verify Bilateral Block Barrier
-- ============================================================================
CREATE OR REPLACE FUNCTION public.is_user_blocked(p_target_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.blocked_users b
        JOIN public.users u ON u.auth_id = auth.uid()
        WHERE (b.blocker_id = u.id AND b.blocked_id = p_target_id)
           OR (b.blocker_id = p_target_id AND b.blocked_id = u.id)
    );
$$;

-- ============================================================================
-- 4. Verify Superadmin Privileges
-- ============================================================================
CREATE OR REPLACE FUNCTION public.is_superadmin()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.users
        WHERE auth_id = auth.uid()
          AND role = 'superadmin'
          AND deleted_at IS NULL
    );
$$;

MD

3. Complete RLS Policies Specification (All 24 Tables)
Tier 1: Core Identity & Kinship Engine
Table 1: public.users
SQL

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Owner can read own profile; others access via public.discovery_profiles
CREATE POLICY "users_select_owner"
ON public.users
FOR SELECT
TO authenticated
USING (auth_id = auth.uid() AND deleted_at IS NULL);

-- Owner can insert their profile record during onboarding
CREATE POLICY "users_insert_owner"
ON public.users
FOR INSERT
TO authenticated
WITH CHECK (auth_id = auth.uid());

-- Owner can update their profile (anti-tampering trigger protects sensitive columns)
CREATE POLICY "users_update_owner"
ON public.users
FOR UPDATE
TO authenticated
USING (auth_id = auth.uid() AND deleted_at IS NULL)
WITH CHECK (auth_id = auth.uid());

-- Soft-delete only via API or cascade; hard delete restricted to service_role
CREATE POLICY "users_delete_service_role"
ON public.users
FOR DELETE
TO service_role
USING (TRUE);

MD

Table 2: public.swipes
SQL

ALTER TABLE public.swipes ENABLE ROW LEVEL SECURITY;

-- Seeker can view their past swipe history if target is not blocked
CREATE POLICY "swipes_select_actor"
ON public.swipes
FOR SELECT
TO authenticated
USING (actor_id = public.get_current_user_id() AND NOT public.is_user_blocked(target_id));

-- Seeker can insert a swipe action
CREATE POLICY "swipes_insert_actor"
ON public.swipes
FOR INSERT
TO authenticated
WITH CHECK (
    actor_id = public.get_current_user_id()
    AND actor_id <> target_id
    AND NOT public.is_user_blocked(target_id)
);

MD

Table 3: public.matches
SQL

ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;

-- Either participant can read the match record
CREATE POLICY "matches_select_participants"
ON public.matches
FOR SELECT
TO authenticated
USING (
    user1_id = public.get_current_user_id()
    OR user2_id = public.get_current_user_id()
);

-- Matches are provisioned exclusively by backend resonance engine (service_role)
CREATE POLICY "matches_insert_service_role"
ON public.matches
FOR INSERT
TO service_role
WITH CHECK (TRUE);

-- Participants can update match closure states ("Pass with Grace") with strict checks
CREATE POLICY "matches_update_participants"
ON public.matches
FOR UPDATE
TO authenticated
USING (
    (user1_id = public.get_current_user_id() OR user2_id = public.get_current_user_id())
    AND is_active = TRUE
    AND closure_status = 'active'
)
WITH CHECK (
    (user1_id = public.get_current_user_id() OR user2_id = public.get_current_user_id())
    AND closure_status IN ('closed_with_grace', 'unmatched')
);

-- Restrict column UPDATE privileges so authenticated clients cannot replace match participant IDs or reactivate matches
REVOKE UPDATE ON public.matches FROM authenticated;
GRANT UPDATE (closure_status, updated_at) ON public.matches TO authenticated;

-- Anti-tampering trigger to guarantee match participant immutability and prevent reactivation
CREATE OR REPLACE FUNCTION public.protect_match_participants()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    IF NEW.user1_id IS DISTINCT FROM OLD.user1_id OR NEW.user2_id IS DISTINCT FROM OLD.user2_id THEN
        RAISE EXCEPTION 'Match participant IDs are immutable.';
    END IF;
    IF OLD.closure_status IN ('closed_with_grace', 'unmatched') AND NEW.closure_status = 'active' THEN
        RAISE EXCEPTION 'Closed matches cannot be reactivated by participants.';
    END IF;
    -- Synchronize is_active when a match closes
    IF NEW.closure_status IN ('closed_with_grace', 'unmatched') THEN
        NEW.is_active := FALSE;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_protect_match_participants ON public.matches;
CREATE TRIGGER trg_protect_match_participants
BEFORE UPDATE ON public.matches
FOR EACH ROW
EXECUTE FUNCTION public.protect_match_participants();

MD

Table 4: public.messages
SQL

ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- Match participants can view encrypted dialogue messages
CREATE POLICY "messages_select_participants"
ON public.messages
FOR SELECT
TO authenticated
USING (public.is_active_match_participant(match_id));

-- Active participants can send messages
CREATE POLICY "messages_insert_sender"
ON public.messages
FOR INSERT
TO authenticated
WITH CHECK (
    sender_id = public.get_current_user_id()
    AND public.is_active_match_participant(match_id)
);

-- Message delivery/read status updates
CREATE POLICY "messages_update_status"
ON public.messages
FOR UPDATE
TO authenticated
USING (public.is_active_match_participant(match_id))
WITH CHECK (public.is_active_match_participant(match_id));

MD

Tier 2: Monetization, Billing & 5-Network Ad SSV
Table 5: public.ad_reward_ledger
SQL

ALTER TABLE public.ad_reward_ledger ENABLE ROW LEVEL SECURITY;

-- User can view their reward credits history
CREATE POLICY "ad_ledger_select_owner"
ON public.ad_reward_ledger
FOR SELECT
TO authenticated
USING (user_id = public.get_current_user_id());

-- Insert restricted to verified SSV backend calls
CREATE POLICY "ad_ledger_insert_service"
ON public.ad_reward_ledger
FOR INSERT
TO service_role
WITH CHECK (TRUE);

MD

Table 6: public.processed_ad_transactions
SQL

ALTER TABLE public.processed_ad_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "processed_ads_select_owner"
ON public.processed_ad_transactions
FOR SELECT
TO authenticated
USING (user_id = public.get_current_user_id());

CREATE POLICY "processed_ads_manage_service"
ON public.processed_ad_transactions
FOR ALL
TO service_role
USING (TRUE);

MD

Table 7: public.in_app_purchases
SQL

ALTER TABLE public.in_app_purchases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "iap_select_owner"
ON public.in_app_purchases
FOR SELECT
TO authenticated
USING (user_id = public.get_current_user_id());

CREATE POLICY "iap_manage_service"
ON public.in_app_purchases
FOR ALL
TO service_role
USING (TRUE);

MD

Table 8: public.pending_web_entitlements
SQL

ALTER TABLE public.pending_web_entitlements ENABLE ROW LEVEL SECURITY;

-- User can read entitlements matching their verified email
CREATE POLICY "pending_entitlements_select_owner"
ON public.pending_web_entitlements
FOR SELECT
TO authenticated
USING (
    (
        email = (auth.jwt() ->> 'email')
        AND (auth.jwt() ->> 'email_verified')::BOOLEAN = TRUE
    )
    OR public.is_superadmin()
);

CREATE POLICY "pending_entitlements_service_role"
ON public.pending_web_entitlements
FOR ALL
TO service_role
USING (TRUE);

MD

Tier 3: Cryptographic Revelation & Consent Rituals
Table 9: public.whatsapp_reveal_tokens
SQL

ALTER TABLE public.whatsapp_reveal_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "wa_tokens_select_participants"
ON public.whatsapp_reveal_tokens
FOR SELECT
TO authenticated
USING (public.is_active_match_participant(match_id));

-- Reveal token mutations (ad counts, consent, ephemeral token unlocking) are mediated via service_role
CREATE POLICY "wa_tokens_update_service_role"
ON public.whatsapp_reveal_tokens
FOR UPDATE
TO service_role
USING (TRUE)
WITH CHECK (TRUE);

CREATE POLICY "wa_tokens_manage_service"
ON public.whatsapp_reveal_tokens
FOR ALL
TO service_role
USING (TRUE);

MD

Table 10: public.contact_reveal_tokens
SQL

ALTER TABLE public.contact_reveal_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "contact_tokens_select_participants"
ON public.contact_reveal_tokens
FOR SELECT
TO authenticated
USING (public.is_active_match_participant(match_id));

-- Contact reveal token mutations mediated via service_role
CREATE POLICY "contact_tokens_update_service_role"
ON public.contact_reveal_tokens
FOR UPDATE
TO service_role
USING (TRUE)
WITH CHECK (TRUE);

CREATE POLICY "contact_tokens_manage_service"
ON public.contact_reveal_tokens
FOR ALL
TO service_role
USING (TRUE);

MD

Table 11: public.photo_reveal_consents
SQL

ALTER TABLE public.photo_reveal_consents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "photo_reveal_select_participants"
ON public.photo_reveal_consents
FOR SELECT
TO authenticated
USING (
    requester_id = public.get_current_user_id()
    OR target_id = public.get_current_user_id()
);

CREATE POLICY "photo_reveal_insert_requester"
ON public.photo_reveal_consents
FOR INSERT
TO authenticated
WITH CHECK (
    requester_id = public.get_current_user_id()
    AND requester_id <> target_id
);

CREATE POLICY "photo_reveal_update_target"
ON public.photo_reveal_consents
FOR UPDATE
TO authenticated
USING (target_id = public.get_current_user_id());

MD

Tier 4: Anonymous Fast-Track Subsystem (Condition C1)
Table 12: public.blind_date_queue
SQL

ALTER TABLE public.blind_date_queue ENABLE ROW LEVEL SECURITY;

CREATE POLICY "blind_queue_select_owner"
ON public.blind_date_queue
FOR SELECT
TO authenticated
USING (user_id = public.get_current_user_id());

CREATE POLICY "blind_queue_insert_owner"
ON public.blind_date_queue
FOR INSERT
TO authenticated
WITH CHECK (user_id = public.get_current_user_id());

CREATE POLICY "blind_queue_delete_owner"
ON public.blind_date_queue
FOR DELETE
TO authenticated
USING (user_id = public.get_current_user_id());

CREATE POLICY "blind_queue_service_role"
ON public.blind_date_queue
FOR ALL
TO service_role
USING (TRUE);

MD

Table 13: public.blind_date_sessions
SQL

ALTER TABLE public.blind_date_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "blind_session_select_participants"
ON public.blind_date_sessions
FOR SELECT
TO authenticated
USING (
    user1_id = public.get_current_user_id()
    OR user2_id = public.get_current_user_id()
);

CREATE POLICY "blind_session_update_service_role"
ON public.blind_date_sessions
FOR UPDATE
TO service_role
USING (TRUE)
WITH CHECK (TRUE);

CREATE POLICY "blind_session_service_role"
ON public.blind_date_sessions
FOR ALL
TO service_role
USING (TRUE);

MD

Table 14: public.blind_date_messages
SQL

ALTER TABLE public.blind_date_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "blind_msg_select_participants"
ON public.blind_date_messages
FOR SELECT
TO authenticated
USING (
    sender_id = public.get_current_user_id()
    OR recipient_id = public.get_current_user_id()
);

CREATE POLICY "blind_msg_insert_sender"
ON public.blind_date_messages
FOR INSERT
TO authenticated
WITH CHECK (
    sender_id = public.get_current_user_id()
    AND EXISTS (
        SELECT 1
        FROM public.blind_date_sessions s
        WHERE s.id = session_id
          AND s.status = 'active'
          AND (
              (s.user1_id = public.get_current_user_id() AND recipient_id = s.user2_id)
              OR (s.user2_id = public.get_current_user_id() AND recipient_id = s.user1_id)
          )
    )
);

MD

Tier 5: DPDP Act 2023, IT Rules & Legal Protection
Table 15: public.underage_quarantine_registry
SQL

ALTER TABLE public.underage_quarantine_registry ENABLE ROW LEVEL SECURITY;

-- PostgREST access completely revoked; Service Role only
REVOKE ALL ON public.underage_quarantine_registry FROM anon, authenticated;

CREATE POLICY "underage_service_role_all"
ON public.underage_quarantine_registry
FOR ALL
TO service_role
USING (TRUE);

MD

Table 16: public.data_nominees
SQL

ALTER TABLE public.data_nominees ENABLE ROW LEVEL SECURITY;

CREATE POLICY "data_nominees_all_owner"
ON public.data_nominees
FOR ALL
TO authenticated
USING (user_id = public.get_current_user_id())
WITH CHECK (user_id = public.get_current_user_id());

MD

Table 17: public.data_export_requests
SQL

ALTER TABLE public.data_export_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "data_export_all_owner"
ON public.data_export_requests
FOR ALL
TO authenticated
USING (user_id = public.get_current_user_id())
WITH CHECK (user_id = public.get_current_user_id());

MD

Table 18: public.consent_audit_logs
SQL

ALTER TABLE public.consent_audit_logs ENABLE ROW LEVEL SECURITY;

-- Logs are append-only by owner, read-only by owner
CREATE POLICY "consent_logs_select_owner"
ON public.consent_audit_logs
FOR SELECT
TO authenticated
USING (user_id = public.get_current_user_id());

CREATE POLICY "consent_logs_insert_owner"
ON public.consent_audit_logs
FOR INSERT
TO authenticated
WITH CHECK (user_id = public.get_current_user_id());

MD

Table 19: public.grievance_dossiers
SQL

ALTER TABLE public.grievance_dossiers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "grievance_select_reporter"
ON public.grievance_dossiers
FOR SELECT
TO authenticated
USING (reporter_id = public.get_current_user_id() OR public.is_superadmin());

CREATE POLICY "grievance_insert_reporter"
ON public.grievance_dossiers
FOR INSERT
TO authenticated
WITH CHECK (
    reporter_id = public.get_current_user_id()
    AND reporter_id <> reported_user_id
);

CREATE POLICY "grievance_admin_update"
ON public.grievance_dossiers
FOR UPDATE
TO authenticated
USING (public.is_superadmin());

MD

Table 20: public.blocked_users
SQL

ALTER TABLE public.blocked_users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "blocked_users_all_blocker"
ON public.blocked_users
FOR ALL
TO authenticated
USING (blocker_id = public.get_current_user_id())
WITH CHECK (
    blocker_id = public.get_current_user_id()
    AND blocker_id <> blocked_id
);

MD

Table 21: public.web_deletion_tokens
SQL

ALTER TABLE public.web_deletion_tokens ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.web_deletion_tokens FROM anon, authenticated;

CREATE POLICY "web_deletion_service_role"
ON public.web_deletion_tokens
FOR ALL
TO service_role
USING (TRUE);

MD

Tier 6: Administration & Telemetry
Table 22: public.admin_kyc_escalations
SQL

ALTER TABLE public.admin_kyc_escalations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kyc_escalation_select_owner"
ON public.admin_kyc_escalations
FOR SELECT
TO authenticated
USING (user_id = public.get_current_user_id() OR public.is_superadmin());

CREATE POLICY "kyc_escalation_admin_manage"
ON public.admin_kyc_escalations
FOR ALL
TO authenticated
USING (public.is_superadmin());

MD

Table 23: public.device_fcm_tokens
SQL

ALTER TABLE public.device_fcm_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "device_fcm_all_owner"
ON public.device_fcm_tokens
FOR ALL
TO authenticated
USING (user_id = public.get_current_user_id())
WITH CHECK (user_id = public.get_current_user_id());

MD

Table 24: public.admin_audit_logs
SQL

ALTER TABLE public.admin_audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "admin_audit_logs_superadmin_all"
ON public.admin_audit_logs
FOR ALL
TO authenticated
USING (public.is_superadmin());

MD

4. Integrity Triggers & Anti-Tampering Engine
4.1 Anti-Tampering Trigger (prevent_user_field_tampering)
Blocks users from upgrading their privileges or bypassing verifications by updating their own users row.
MD

SQL

CREATE OR REPLACE FUNCTION public.prevent_user_field_tampering()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    -- Permit updates performed by service_role or superadmin
    IF auth.role() = 'service_role' OR public.is_superadmin() THEN
        RETURN NEW;
    END IF;

    -- Guard against client-side elevation of verified and billing state
    IF NEW.kyc_status IS DISTINCT FROM OLD.kyc_status THEN
        RAISE EXCEPTION 'Tampering detected: kyc_status cannot be modified directly';
    END IF;

    IF NEW.is_voice_verified IS DISTINCT FROM OLD.is_voice_verified THEN
        RAISE EXCEPTION 'Tampering detected: is_voice_verified requires audio verification service';
    END IF;

    IF NEW.email IS DISTINCT FROM OLD.email THEN
        RAISE EXCEPTION 'Tampering detected: email address change requires re-authentication';
    END IF;

    IF NEW.role IS DISTINCT FROM OLD.role THEN
        RAISE EXCEPTION 'Tampering detected: role elevation is unauthorized';
    END IF;

    IF NEW.dob IS DISTINCT FROM OLD.dob THEN
        RAISE EXCEPTION 'Tampering detected: declared DOB is legally immutable';
    END IF;

    IF NEW.subscription_tier IS DISTINCT FROM OLD.subscription_tier THEN
        RAISE EXCEPTION 'Tampering detected: subscription_tier requires gateway validation';
    END IF;

    IF NEW.subscription_expires_at IS DISTINCT FROM OLD.subscription_expires_at THEN
        RAISE EXCEPTION 'Tampering detected: subscription_expires_at requires gateway validation';
    END IF;

    IF NEW.is_ad_free IS DISTINCT FROM OLD.is_ad_free THEN
        RAISE EXCEPTION 'Tampering detected: is_ad_free requires active entitlement';
    END IF;

    IF NEW.reward_balance IS DISTINCT FROM OLD.reward_balance THEN
        RAISE EXCEPTION 'Tampering detected: reward_balance requires valid SSV ledger credit';
    END IF;

    IF NEW.boost_points IS DISTINCT FROM OLD.boost_points THEN
        RAISE EXCEPTION 'Tampering detected: boost_points requires authorized reward credit';
    END IF;

    IF NEW.swipes_remaining IS DISTINCT FROM OLD.swipes_remaining THEN
        RAISE EXCEPTION 'Tampering detected: swipes_remaining cannot be self-awarded';
    END IF;

    IF NEW.reveal_tokens_count IS DISTINCT FROM OLD.reveal_tokens_count THEN
        RAISE EXCEPTION 'Tampering detected: reveal_tokens_count cannot be self-awarded';
    END IF;

    IF NEW.direct_letters_count IS DISTINCT FROM OLD.direct_letters_count THEN
        RAISE EXCEPTION 'Tampering detected: direct_letters_count cannot be self-awarded';
    END IF;

    IF NEW.streak_count IS DISTINCT FROM OLD.streak_count THEN
        RAISE EXCEPTION 'Tampering detected: streak_count is managed by daily cycle engine';
    END IF;

    IF NEW.deleted_at IS DISTINCT FROM OLD.deleted_at THEN
        RAISE EXCEPTION 'Tampering detected: soft-deletion must proceed via legal erasure API';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tr_prevent_user_tampering ON public.users;
CREATE TRIGGER tr_prevent_user_tampering
BEFORE UPDATE ON public.users
FOR EACH ROW
EXECUTE FUNCTION public.prevent_user_field_tampering();

MD

4.2 Auto-Timestamp Refresh Trigger
SQL

CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tr_users_updated_at ON public.users;
CREATE TRIGGER tr_users_updated_at
BEFORE UPDATE ON public.users
FOR EACH ROW
EXECUTE FUNCTION public.handle_updated_at();

MD

4.3 Cascade Storage & Account Cleanup Trigger (handle_user_cascade_cleanup)
Ensures that deleting a profile clears Supabase Storage objects and cascades to auth.users.
MD

SQL

CREATE OR REPLACE FUNCTION public.handle_user_cascade_cleanup()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    -- 1. Purge media objects from ur-heart-media storage bucket
    DELETE FROM storage.objects
    WHERE bucket_id = 'ur-heart-media'
      AND (name LIKE ('users/' || OLD.auth_id::text || '/%'));

    -- 2. Cascade hard delete to auth.users if not already executed
    DELETE FROM auth.users
    WHERE id = OLD.auth_id;

    RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_user_cascade_cleanup ON public.users;
CREATE TRIGGER trg_user_cascade_cleanup
BEFORE DELETE ON public.users
FOR EACH ROW
EXECUTE FUNCTION public.handle_user_cascade_cleanup();

MD

5. Secure Discovery Projection View (public.discovery_profiles)
Replaces direct table access for the discovery feed, stripping PII (email, phone, raw GPS) while enforcing reciprocal orientation and self-exclusion filters.
MD

SQL

CREATE OR REPLACE VIEW public.discovery_profiles
WITH (security_barrier = TRUE, security_invoker = FALSE)
AS
SELECT
    u.id,
    u.full_name,
    DATE_PART('year', AGE(CURRENT_DATE, u.dob))::INT2 AS age,
    u.gender,
    u.interested_in,
    u.location_name,
    ROUND(u.latitude::NUMERIC, 2) AS latitude,
    ROUND(u.longitude::NUMERIC, 2) AS longitude,
    u.bio,
    u.profession,
    u.education,
    u.streak_count,
    u.boost_points,
    u.kyc_status,
    u.is_photo_veiled,
    u.photos,
    u.avatar_url,
    u.voice_spark_url,
    u.voice_spark_prompt,
    u.voice_spark_duration,
    u.is_voice_verified,
    u.created_at
FROM public.users u
WHERE u.deleted_at IS NULL
  AND u.is_profile_completed = TRUE
  AND u.is_incognito = FALSE
  AND u.auth_id <> auth.uid()
  AND NOT public.is_user_blocked(u.id);

-- Grant select to authenticated clients
GRANT SELECT ON public.discovery_profiles TO authenticated;

MD

6. Maintenance & Data Retention Automation (pg_cron)
Statutory compliance schedule executing daily at 03:00 UTC:
MD

Purges messages older than 30 days.
MD

Purges pass swipes older than 30 days to free deck space.
MD

Purges expired data export payloads.
MD

Purges expired web account deletion tokens.
MD

SQL

CREATE OR REPLACE FUNCTION public.purge_expired_temporary_records()
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    -- 1. Purge messages older than 30 days
    DELETE FROM public.messages
    WHERE created_at < NOW() - INTERVAL '30 days';

    -- 2. Purge pass swipes older than 30 days
    DELETE FROM public.swipes
    WHERE swipe_type = 'pass'
      AND created_at < NOW() - INTERVAL '30 days';

    -- 3. Invalidate completed/expired data export archives
    DELETE FROM public.data_export_requests
    WHERE expires_at IS NOT NULL AND expires_at < NOW();

    -- 4. Purge expired web deletion tokens
    DELETE FROM public.web_deletion_tokens
    WHERE expires_at < NOW();
END;
$$;

-- Security hardening: revoke public RPC execution and restrict to service_role
REVOKE EXECUTE ON FUNCTION public.purge_expired_temporary_records() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.purge_expired_temporary_records() TO service_role;

-- Schedule cron job if pg_cron is enabled
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        PERFORM cron.schedule(
            'sanctuary_daily_retention_purge',
            '0 3 * * *',
            'SELECT public.purge_expired_temporary_records();'
        );
    END IF;
END $$;

MD

7. Migration File Placement
Save this specification into the Supabase migrations directory:

Plaintext

supabase/migrations/20260926000001_phase1_security_policies_and_triggers.sql
