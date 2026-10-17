-- ==============================================================================
-- Migration: 20261016150000_harmonize_schema_types_and_constraints.sql
-- Subsystem: Supabase PostgreSQL Database Foundation
-- Purpose: Harmonize schema types, constraints, and column definitions between
--          Supabase PostgreSQL and SQLAlchemy declarative models:
--          1. Align public.grievance_dossiers status check constraint and columns
--          2. Align public.ad_reward_ledger ad_type check constraint with all 22 reward types
--          3. Harmonize public.blind_date_messages column name (ciphertext -> encrypted_text)
--          4. Harmonize public.device_fcm_tokens column name (active -> is_active) & index
--          5. Harmonize public.admin_kyc_escalations columns & nullability
--          6. Idempotent guard for legacy whatsapp_reveal_tokens
-- ==============================================================================

-- 1. Align public.grievance_dossiers check constraint & statutory columns
ALTER TABLE public.grievance_dossiers 
    DROP CONSTRAINT IF EXISTS grievance_dossiers_status_check;
ALTER TABLE public.grievance_dossiers 
    DROP CONSTRAINT IF EXISTS chk_grievance_dossiers_status;
ALTER TABLE public.grievance_dossiers 
    DROP CONSTRAINT IF EXISTS chk_grievance_status;

ALTER TABLE public.grievance_dossiers 
    ALTER COLUMN status TYPE VARCHAR(25);
ALTER TABLE public.grievance_dossiers 
    ALTER COLUMN status SET DEFAULT 'acknowledged';

ALTER TABLE public.grievance_dossiers 
    ADD CONSTRAINT chk_grievance_dossiers_status 
    CHECK (status IN ('under_review', 'actioned', 'dismissed', 'acknowledged', 'investigating', 'closed'));

ALTER TABLE public.grievance_dossiers 
    ADD COLUMN IF NOT EXISTS statutory_notes TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS sla_deadline_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS resolution_summary TEXT,
    ADD COLUMN IF NOT EXISTS actioned_at TIMESTAMPTZ;


-- 2. Align public.ad_reward_ledger check constraint with all 22 legitimate ad reward types
ALTER TABLE public.ad_reward_ledger 
    DROP CONSTRAINT IF EXISTS chk_ad_reward_ledger_ad_type;
ALTER TABLE public.ad_reward_ledger 
    DROP CONSTRAINT IF EXISTS ad_reward_ledger_ad_type_check;
ALTER TABLE public.ad_reward_ledger 
    DROP CONSTRAINT IF EXISTS chk_ad_type;

ALTER TABLE public.ad_reward_ledger 
    ALTER COLUMN ad_type TYPE VARCHAR(50);

ALTER TABLE public.ad_reward_ledger 
    ADD CONSTRAINT chk_ad_reward_ledger_ad_type 
    CHECK (ad_type IN (
        -- Emitted by ad_ssv_service.py
        'quick_reflection',
        'deep_resonance',
        'sacred_bridge_reveal',
        'whatsapp_reveal',
        'morning_harvest_unlock',
        'daily_streak_boost',
        'rewarded_daily_boost',
        -- Monetization model & claim endpoints
        'rewarded_reveal',
        'rewarded_extra_swipes',
        'rewarded_streak_freeze',
        'rewarded_blind_date_extend',
        'extra_swipes',
        -- Rewarded catalog & perk boosts
        'daily_harvest_boost',
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


-- 3. Align public.blind_date_messages column name (ciphertext -> encrypted_text)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'blind_date_messages' 
          AND column_name = 'ciphertext'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'blind_date_messages' 
          AND column_name = 'encrypted_text'
    ) THEN
        ALTER TABLE public.blind_date_messages RENAME COLUMN ciphertext TO encrypted_text;
    END IF;
END $$;


-- 4. Align public.device_fcm_tokens column name (active -> is_active) & recreate index
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'device_fcm_tokens' 
          AND column_name = 'active'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'device_fcm_tokens' 
          AND column_name = 'is_active'
    ) THEN
        ALTER TABLE public.device_fcm_tokens RENAME COLUMN active TO is_active;
    END IF;
END $$;

DROP INDEX IF EXISTS public.idx_fcm_tokens_user;
CREATE INDEX IF NOT EXISTS idx_fcm_tokens_user 
    ON public.device_fcm_tokens(user_id) 
    WHERE is_active = TRUE;


-- 5. Align public.admin_kyc_escalations columns & nullability
ALTER TABLE public.admin_kyc_escalations
    ADD COLUMN IF NOT EXISTS selfie_storage_url TEXT,
    ADD COLUMN IF NOT EXISTS id_card_storage_url TEXT,
    ADD COLUMN IF NOT EXISTS declared_age INT2 DEFAULT 18,
    ADD COLUMN IF NOT EXISTS groq_reasoning VARCHAR(255) DEFAULT 'Automated biometric audit';

UPDATE public.admin_kyc_escalations
    SET selfie_storage_url = COALESCE(selfie_storage_url, kyc_video_url, ''),
        id_card_storage_url = COALESCE(id_card_storage_url, anchor_photo_url, '')
    WHERE selfie_storage_url IS NULL OR id_card_storage_url IS NULL;

ALTER TABLE public.admin_kyc_escalations
    ALTER COLUMN anchor_photo_url DROP NOT NULL,
    ALTER COLUMN kyc_video_url DROP NOT NULL,
    ALTER COLUMN declared_age DROP NOT NULL,
    ALTER COLUMN groq_reasoning DROP NOT NULL,
    ALTER COLUMN groq_reasoning SET DEFAULT 'Automated biometric audit';


-- 6. Safeguard: Prune legacy whatsapp_reveal_tokens if still lingering
DROP TABLE IF EXISTS public.whatsapp_reveal_tokens CASCADE;
