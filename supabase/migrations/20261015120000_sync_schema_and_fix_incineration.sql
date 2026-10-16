-- ==============================================================================
-- Migration: 20261015120000_sync_schema_and_fix_incineration.sql
-- Subsystem: Supabase PostgreSQL Database Foundation
-- Purpose: Harmonize SQLAlchemy models with Supabase schema, fix account
--          incineration cascade paradox, deploy missing foreign key indexes,
--          and prune obsolete legacy objects.
-- ==============================================================================

-- 1. Add missing perk and streak tracking columns to public.users
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS super_likes_count INT2 NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS instant_bridge_passes INT2 NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS instant_contact_keys INT2 NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS has_unlimited_swipes BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS passport_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_ad_watched_at TIMESTAMPTZ;

-- 2. Add direct_letter_text to public.swipes for Super-Resonances
ALTER TABLE public.swipes
    ADD COLUMN IF NOT EXISTS direct_letter_text TEXT;

-- 3. Harmonize check constraints across users, matches, and ad rewards
ALTER TABLE public.users
    DROP CONSTRAINT IF EXISTS chk_users_subscription_tier;

ALTER TABLE public.users
    ADD CONSTRAINT chk_users_subscription_tier
    CHECK (subscription_tier IN ('free', 'spark', 'flame', 'kindred', 'lifetime', 'weekly', 'monthly', 'quarterly'));

ALTER TABLE public.matches
    DROP CONSTRAINT IF EXISTS chk_matches_closure_status;

ALTER TABLE public.matches
    ADD CONSTRAINT chk_matches_closure_status
    CHECK (closure_status IN ('active', 'closed_with_grace', 'unmatched', 'peer_incinerated'));

ALTER TABLE public.ad_reward_ledger
    DROP CONSTRAINT IF EXISTS chk_ad_reward_ledger_ad_type;

ALTER TABLE public.ad_reward_ledger
    ADD CONSTRAINT chk_ad_reward_ledger_ad_type
    CHECK (ad_type IN (
        'daily_harvest_boost',
        'extra_swipes',
        'instant_reveal_key',
        'super_like',
        'instant_bridge_pass',
        'streak_freeze',
        'rewind_pass',
        'compass_teleport',
        'ad_free_24h',
        'profile_spotlight',
        'incognito_hour'
    ));

-- 4. Fix Account Incineration "Vaporization Paradox"
-- Allow user1_id and user2_id to be nullable so deleting User A does NOT destroy
-- the match row; instead, user1_id is set to NULL, preserving closure_status = 'peer_incinerated'
-- for the surviving User B.
ALTER TABLE public.matches
    ALTER COLUMN user1_id DROP NOT NULL,
    ALTER COLUMN user2_id DROP NOT NULL;

ALTER TABLE public.matches
    DROP CONSTRAINT IF EXISTS matches_user1_id_fkey,
    DROP CONSTRAINT IF EXISTS matches_user2_id_fkey;

ALTER TABLE public.matches
    ADD CONSTRAINT matches_user1_id_fkey
    FOREIGN KEY (user1_id) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE public.matches
    ADD CONSTRAINT matches_user2_id_fkey
    FOREIGN KEY (user2_id) REFERENCES public.users(id) ON DELETE SET NULL;

-- 4.1 Trigger to mark surviving match rows as peer_incinerated before user is deleted,
-- and delete matches where both participants are deleted / null.
CREATE OR REPLACE FUNCTION public.handle_user_incineration_matches()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    -- If counterpart is already deleted/null, expunge match entirely
    DELETE FROM public.matches
    WHERE (user1_id = OLD.id AND user2_id IS NULL)
       OR (user2_id = OLD.id AND user1_id IS NULL);

    -- Mark surviving matches where counterpart remains active
    UPDATE public.matches
    SET closure_status = 'peer_incinerated',
        is_active = false
    WHERE user1_id = OLD.id OR user2_id = OLD.id;
    RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_user_incineration_matches ON public.users;
CREATE TRIGGER trg_user_incineration_matches
    BEFORE DELETE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_user_incineration_matches();

-- 4.2 Row-level trigger targeting only affected match rows when both user IDs become null
CREATE OR REPLACE FUNCTION public.handle_orphaned_matches_cleanup()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    IF NEW.user1_id IS NULL AND NEW.user2_id IS NULL THEN
        DELETE FROM public.matches WHERE id = NEW.id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_cleanup_orphaned_matches ON public.matches;
CREATE TRIGGER trg_cleanup_orphaned_matches
    AFTER UPDATE OF user1_id, user2_id ON public.matches
    FOR EACH ROW
    WHEN (NEW.user1_id IS NULL AND NEW.user2_id IS NULL)
    EXECUTE FUNCTION public.handle_orphaned_matches_cleanup();

-- 5. Deploy missing foreign key B-tree indexes to prevent sequential lockups on cascade deletions
CREATE INDEX IF NOT EXISTS idx_matches_closed_by_user_id ON public.matches (closed_by_user_id) WHERE closed_by_user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_sender_id ON public.messages (sender_id) WHERE sender_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_grievance_reporter_id ON public.grievance_dossiers (reporter_id);
CREATE INDEX IF NOT EXISTS idx_grievance_reported_user_id ON public.grievance_dossiers (reported_user_id);
CREATE INDEX IF NOT EXISTS idx_data_export_requests_user_id ON public.data_export_requests (user_id);
CREATE INDEX IF NOT EXISTS idx_blocked_users_blocked_id ON public.blocked_users (blocked_id);
CREATE INDEX IF NOT EXISTS idx_pending_web_entitlements_claimed_by ON public.pending_web_entitlements (claimed_by_user_id) WHERE claimed_by_user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_web_deletion_tokens_user_id ON public.web_deletion_tokens (user_id);

-- 6. Drop obsolete legacy duplicate table
DROP TABLE IF EXISTS public.whatsapp_reveal_tokens CASCADE;

-- 7. Correct storage cleanup cascade trigger prefix (use OLD.id instead of OLD.auth_id)
-- Note: Binary media objects are actively purged across 'users/{OLD.id}/' and 'kyc_temp/{OLD.id}/'
-- via the Supabase Storage / Cloudflare R2 API in AccountIncinerationService post-commit.
-- This trigger handles underlying storage object database metadata cleanup within PostgreSQL.
CREATE OR REPLACE FUNCTION public.handle_user_cascade_cleanup()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM set_config('storage.allow_delete_query', 'true', true);
    DELETE FROM storage.objects
    WHERE bucket_id = 'ur-heart-media'
      AND (name LIKE ('users/' || OLD.id::text || '/%') OR name LIKE ('kyc_temp/' || OLD.id::text || '/%'));
    PERFORM set_config('storage.allow_delete_query', 'false', true);
    RETURN OLD;
END;
$$;
