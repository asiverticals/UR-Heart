-- UR-Heart Sanctuary — Phase 1: Chunk 1.1 Database Foundation (Tables 1 to 4)
-- Architectural Invariants:
-- 1. Stateless PostgreSQL 15+ engine with strict referential integrity.
-- 2. Foreign keys enforce ON DELETE CASCADE (with closed_by_user_id ON DELETE SET NULL).
-- 3. Cloudflare R2 URLs stored for media assets; zero unasked dynamic JSON in domain layer.
-- 4. Immediate default-deny Row Level Security enabled across all exposed tables.

-- 1. Mandatory PostgreSQL Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Table 1: public.users (Core Identity & Kinship Engine)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE,
    full_name VARCHAR(60) NOT NULL,
    dob DATE NOT NULL,
    gender VARCHAR(15) NOT NULL CHECK (gender IN ('Woman', 'Man', 'Non-Binary', 'Other')),
    interested_in VARCHAR(15) NOT NULL CHECK (interested_in IN ('Men', 'Women', 'Everyone')),
    contact_bridge_type VARCHAR(20) NOT NULL DEFAULT 'whatsapp' CHECK (contact_bridge_type IN ('whatsapp', 'instagram', 'snapchat', 'telegram', 'signal')),
    contact_bridge_encrypted TEXT NOT NULL,
    location_name VARCHAR(100) NOT NULL DEFAULT 'Saket, Ayodhya',
    latitude NUMERIC(9,6),
    longitude NUMERIC(9,6),
    bio VARCHAR(500) DEFAULT '',
    profession VARCHAR(80) DEFAULT '',
    education VARCHAR(100) DEFAULT '',
    preferred_age_min INT2 NOT NULL DEFAULT 18 CHECK (preferred_age_min >= 18),
    preferred_age_max INT2 NOT NULL DEFAULT 35 CHECK (preferred_age_max <= 100),
    streak_count INT2 NOT NULL DEFAULT 0,
    boost_points INT4 NOT NULL DEFAULT 0,
    last_streak_ad_at TIMESTAMPTZ,
    streak_expires_at TIMESTAMPTZ,
    reveal_tokens_count INT2 NOT NULL DEFAULT 1,
    reward_balance INT4 NOT NULL DEFAULT 0,
    swipes_remaining INT2 NOT NULL DEFAULT 25,
    direct_letters_count INT2 NOT NULL DEFAULT 1,
    last_installation_uuid VARCHAR(64),
    referral_code VARCHAR(32) UNIQUE NOT NULL DEFAULT ('SANCTUARY-' || UPPER(SUBSTRING(REPLACE(gen_random_uuid()::TEXT, '-', ''), 1, 12))),
    kyc_status BOOLEAN NOT NULL DEFAULT FALSE,
    is_incognito BOOLEAN NOT NULL DEFAULT FALSE,
    is_photo_veiled BOOLEAN NOT NULL DEFAULT FALSE,
    discreet_mode BOOLEAN NOT NULL DEFAULT FALSE,
    night_slumber BOOLEAN NOT NULL DEFAULT FALSE,
    is_profile_completed BOOLEAN NOT NULL DEFAULT FALSE,
    welcome_email_sent BOOLEAN NOT NULL DEFAULT FALSE,
    public_encryption_key VARCHAR(64),
    push_notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    fcm_token VARCHAR(512),
    subscription_tier VARCHAR(20) NOT NULL DEFAULT 'free' CHECK (subscription_tier IN ('free', 'weekly', 'monthly', 'quarterly', 'lifetime')),
    subscription_expires_at TIMESTAMPTZ,
    is_ad_free BOOLEAN NOT NULL DEFAULT FALSE,
    passport_city VARCHAR(100),
    photos TEXT[] DEFAULT ARRAY[]::TEXT[],
    avatar_url VARCHAR(500),
    voice_spark_url VARCHAR(500),
    voice_spark_prompt VARCHAR(120),
    voice_spark_duration NUMERIC(4,1) DEFAULT 7.0,
    is_voice_verified BOOLEAN NOT NULL DEFAULT FALSE,
    last_blind_date_date DATE,
    blind_date_passes INTEGER NOT NULL DEFAULT 0,
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'moderator', 'superadmin')),
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_users_preferred_age_range CHECK (preferred_age_min <= preferred_age_max)
);

-- Compound Indexes for Feed Filtering & Boost Scoring
CREATE INDEX IF NOT EXISTS idx_users_auth_id ON public.users (auth_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_feed_filter ON public.users (gender, interested_in, kyc_status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_discovery_boost ON public.users (boost_points DESC, streak_count DESC, created_at DESC) WHERE deleted_at IS NULL AND is_profile_completed = TRUE;

-- Enable Row Level Security (Default Deny until Chunk 1.2 Policies)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- 3. Table 2: public.swipes (Discovery Deck Bilateral Actions)
CREATE TABLE IF NOT EXISTS public.swipes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    swipe_type VARCHAR(10) NOT NULL CHECK (swipe_type IN ('like', 'pass', 'superlike')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_swipes_actor_target UNIQUE (actor_id, target_id),
    CONSTRAINT chk_swipes_no_self_swipe CHECK (actor_id <> target_id)
);

CREATE INDEX IF NOT EXISTS idx_swipes_actor ON public.swipes(actor_id);
CREATE INDEX IF NOT EXISTS idx_swipes_target ON public.swipes(target_id);

-- Enable Row Level Security
ALTER TABLE public.swipes ENABLE ROW LEVEL SECURITY;

-- 4. Table 3: public.matches (Active Dialogue Connections & Closure States)
CREATE TABLE IF NOT EXISTS public.matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user1_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    user2_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    matched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closure_status VARCHAR(30) NOT NULL DEFAULT 'active' CHECK (closure_status IN ('active', 'closed_with_grace', 'unmatched')),
    closed_by_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    closed_at TIMESTAMPTZ,
    closure_template_key VARCHAR(50),
    closure_note TEXT,
    CONSTRAINT uq_matches_pair UNIQUE (user1_id, user2_id),
    CONSTRAINT chk_matches_no_self_match CHECK (user1_id <> user2_id),
    CONSTRAINT chk_matches_ordered_pair CHECK (user1_id < user2_id)
);

CREATE INDEX IF NOT EXISTS idx_matches_user1 ON public.matches(user1_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_matches_user2 ON public.matches(user2_id) WHERE is_active = TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_matches_unordered_pair ON public.matches (LEAST(user1_id, user2_id), GREATEST(user1_id, user2_id));

-- Enable Row Level Security
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;

-- 5. Table 4: public.messages (Encrypted Dialogue Persistence)
CREATE TABLE IF NOT EXISTS public.messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id UUID NOT NULL REFERENCES public.matches(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    encrypted_text TEXT NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'sent' CHECK (status IN ('sent', 'delivered', 'read')),
    client_id VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_match_chronological ON public.messages(match_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_purge ON public.messages(created_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_messages_client_id ON public.messages(match_id, sender_id, client_id) WHERE client_id IS NOT NULL;

-- Trigger: Require message sender to be a participant in the referenced match
CREATE OR REPLACE FUNCTION public.check_message_sender_is_participant()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.matches
        WHERE id = NEW.match_id
          AND (user1_id = NEW.sender_id OR user2_id = NEW.sender_id)
    ) THEN
        RAISE EXCEPTION 'Sender % is not a participant in match %', NEW.sender_id, NEW.match_id;
    END IF;
    RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trg_check_message_sender'
          AND tgrelid = 'public.messages'::regclass
    ) THEN
        CREATE TRIGGER trg_check_message_sender
        BEFORE INSERT OR UPDATE ON public.messages
        FOR EACH ROW EXECUTE FUNCTION public.check_message_sender_is_participant();
    END IF;
END $$;

-- Enable Row Level Security
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Tier 2: Monetization, Billing & 5-Network Ad SSV
-- ============================================================================

-- 6. Table 5: public.ad_reward_ledger
CREATE TABLE IF NOT EXISTS public.ad_reward_ledger (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    ssv_transaction_id VARCHAR(150) UNIQUE NOT NULL,
    network VARCHAR(20) NOT NULL CHECK (network IN ('admob', 'admob_client', 'meta', 'unity', 'chartboost', 'liftoff')),
    ad_type VARCHAR(30) NOT NULL CHECK (ad_type IN ('quick_reflection', 'deep_resonance', 'sacred_bridge_reveal', 'whatsapp_reveal', 'morning_harvest_unlock', 'daily_streak_boost')),
    reward_points INT4 NOT NULL CHECK (reward_points > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ad_reward_ledger_user ON public.ad_reward_ledger(user_id);
ALTER TABLE public.ad_reward_ledger ENABLE ROW LEVEL SECURITY;

-- 7. Table 6: public.processed_ad_transactions
CREATE TABLE IF NOT EXISTS public.processed_ad_transactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id VARCHAR(150) UNIQUE NOT NULL,
    network VARCHAR(20) NOT NULL,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    ad_type VARCHAR(30) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_processed_ad_user ON public.processed_ad_transactions(user_id);
ALTER TABLE public.processed_ad_transactions ENABLE ROW LEVEL SECURITY;

-- 8. Table 7: public.in_app_purchases
CREATE TABLE IF NOT EXISTS public.in_app_purchases (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    transaction_reference VARCHAR(150) UNIQUE NOT NULL,
    product_identifier VARCHAR(60) NOT NULL,
    store VARCHAR(30) NOT NULL DEFAULT 'google_play' CHECK (store IN ('google_play', 'web_razorpay_india', 'web_stripe_global')),
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    amount_gross NUMERIC(10,2) NOT NULL,
    platform_fee NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    amount_net NUMERIC(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'refunded')),
    purchased_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_iap_nonnegative_amounts CHECK (amount_gross >= 0 AND platform_fee >= 0 AND amount_net >= 0)
);

CREATE INDEX IF NOT EXISTS idx_iap_user_id ON public.in_app_purchases(user_id);
ALTER TABLE public.in_app_purchases ENABLE ROW LEVEL SECURITY;

-- 9. Table 8: public.pending_web_entitlements
CREATE TABLE IF NOT EXISTS public.pending_web_entitlements (
    id BIGSERIAL PRIMARY KEY,
    order_id VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    product_identifier VARCHAR(60) NOT NULL,
    payment_reference VARCHAR(150),
    amount_gross NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    status VARCHAR(30) NOT NULL DEFAULT 'paid_pending_claim' CHECK (status IN ('paid_pending_claim', 'claimed', 'refunded')),
    claimed_by_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    claimed_at TIMESTAMPTZ,
    CONSTRAINT chk_web_entitlement_nonnegative_amount CHECK (amount_gross >= 0)
);

CREATE INDEX IF NOT EXISTS idx_pending_web_email ON public.pending_web_entitlements(email) WHERE status = 'paid_pending_claim';
ALTER TABLE public.pending_web_entitlements ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Tier 3: Cryptographic Revelation & Consent Rituals
-- ============================================================================

-- 10. Table 9: public.whatsapp_reveal_tokens
CREATE TABLE IF NOT EXISTS public.whatsapp_reveal_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID UNIQUE NOT NULL REFERENCES public.matches(id) ON DELETE CASCADE,
    user1_consent BOOLEAN NOT NULL DEFAULT FALSE,
    user2_consent BOOLEAN NOT NULL DEFAULT FALSE,
    user1_ads_count INT2 NOT NULL DEFAULT 0 CHECK (user1_ads_count BETWEEN 0 AND 3),
    user2_ads_count INT2 NOT NULL DEFAULT 0 CHECK (user2_ads_count BETWEEN 0 AND 3),
    is_unlocked BOOLEAN NOT NULL DEFAULT FALSE,
    ephemeral_token VARCHAR(64),
    expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.whatsapp_reveal_tokens ENABLE ROW LEVEL SECURITY;

-- 11. Table 10: public.contact_reveal_tokens
CREATE TABLE IF NOT EXISTS public.contact_reveal_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID UNIQUE NOT NULL REFERENCES public.matches(id) ON DELETE CASCADE,
    user1_consent BOOLEAN NOT NULL DEFAULT FALSE,
    user2_consent BOOLEAN NOT NULL DEFAULT FALSE,
    user1_ads_count INT2 NOT NULL DEFAULT 0 CHECK (user1_ads_count BETWEEN 0 AND 3),
    user2_ads_count INT2 NOT NULL DEFAULT 0 CHECK (user2_ads_count BETWEEN 0 AND 3),
    is_unlocked BOOLEAN NOT NULL DEFAULT FALSE,
    ephemeral_token VARCHAR(64),
    expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.contact_reveal_tokens ENABLE ROW LEVEL SECURITY;

-- 12. Table 11: public.photo_reveal_consents
CREATE TABLE IF NOT EXISTS public.photo_reveal_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requester_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_photo_reveal_pair UNIQUE (requester_id, target_id),
    CONSTRAINT chk_photo_reveal_no_self CHECK (requester_id <> target_id)
);

CREATE INDEX IF NOT EXISTS idx_photo_reveal_target ON public.photo_reveal_consents(target_id) WHERE status = 'pending';
ALTER TABLE public.photo_reveal_consents ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Tier 4: Anonymous Fast-Track Subsystem (Condition C1)
-- ============================================================================

-- 13. Table 12: public.blind_date_queue
CREATE TABLE IF NOT EXISTS public.blind_date_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    gender VARCHAR(20) NOT NULL,
    interested_in VARCHAR(100) NOT NULL,
    age INT2 NOT NULL DEFAULT 24,
    preferred_age_min INT2 NOT NULL DEFAULT 18,
    preferred_age_max INT2 NOT NULL DEFAULT 45,
    status VARCHAR(20) NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'paired', 'cancelled')),
    is_fast_track BOOLEAN NOT NULL DEFAULT FALSE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    paired_session_id UUID,
    CONSTRAINT chk_blind_queue_age_range CHECK (preferred_age_min >= 18 AND preferred_age_min <= preferred_age_max)
);

CREATE INDEX IF NOT EXISTS idx_blind_queue_matching ON public.blind_date_queue(gender, status, joined_at) WHERE status = 'waiting';
ALTER TABLE public.blind_date_queue ENABLE ROW LEVEL SECURITY;

-- 14. Table 13: public.blind_date_sessions
CREATE TABLE IF NOT EXISTS public.blind_date_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user1_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    user2_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'revealed', 'passed', 'cancelled')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    user1_decision VARCHAR(15) NOT NULL DEFAULT 'pending' CHECK (user1_decision IN ('pending', 'resonate', 'pass')),
    user2_decision VARCHAR(15) NOT NULL DEFAULT 'pending' CHECK (user2_decision IN ('pending', 'resonate', 'pass')),
    icebreaker_prompt TEXT DEFAULT 'What is a quiet dream you hold close to your heart?',
    match_id UUID REFERENCES public.matches(id) ON DELETE SET NULL,
    extension_count INT2 NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_blind_session_no_self CHECK (user1_id <> user2_id)
);

CREATE INDEX IF NOT EXISTS idx_blind_session_user1 ON public.blind_date_sessions(user1_id);
CREATE INDEX IF NOT EXISTS idx_blind_session_user2 ON public.blind_date_sessions(user2_id);
ALTER TABLE public.blind_date_sessions ENABLE ROW LEVEL SECURITY;

-- Foreign key linking blind_date_queue to paired blind_date_sessions
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_blind_queue_paired_session'
    ) THEN
        ALTER TABLE public.blind_date_queue
            ADD CONSTRAINT fk_blind_queue_paired_session
            FOREIGN KEY (paired_session_id)
            REFERENCES public.blind_date_sessions(id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- Trigger: Reset queue status to 'waiting' when a paired blind date session is deleted
CREATE OR REPLACE FUNCTION public.reset_queue_on_session_deletion()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    UPDATE public.blind_date_queue
    SET status = CASE 
            WHEN status = 'paired' THEN 'waiting' 
            ELSE status 
        END,
        paired_session_id = NULL
    WHERE paired_session_id = OLD.id;
    RETURN OLD;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trg_reset_queue_on_session_deletion'
          AND tgrelid = 'public.blind_date_sessions'::regclass
    ) THEN
        CREATE TRIGGER trg_reset_queue_on_session_deletion
        BEFORE DELETE ON public.blind_date_sessions
        FOR EACH ROW EXECUTE FUNCTION public.reset_queue_on_session_deletion();
    END IF;
END $$;

-- 15. Table 14: public.blind_date_messages
CREATE TABLE IF NOT EXISTS public.blind_date_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.blind_date_sessions(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    recipient_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    ciphertext TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_blind_msg_session ON public.blind_date_messages(session_id, created_at ASC);

-- Trigger: Enforce sender and recipient belong to the referenced blind date session
CREATE OR REPLACE FUNCTION public.check_blind_date_message_sender()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.blind_date_sessions
        WHERE id = NEW.session_id
          AND (
            (user1_id = NEW.sender_id AND (NEW.recipient_id IS NULL OR NEW.recipient_id = user2_id))
            OR (user2_id = NEW.sender_id AND (NEW.recipient_id IS NULL OR NEW.recipient_id = user1_id))
          )
    ) THEN
        RAISE EXCEPTION 'Sender % or recipient % is invalid for blind date session %', NEW.sender_id, NEW.recipient_id, NEW.session_id;
    END IF;
    RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trg_check_blind_date_message_sender'
          AND tgrelid = 'public.blind_date_messages'::regclass
    ) THEN
        CREATE TRIGGER trg_check_blind_date_message_sender
        BEFORE INSERT OR UPDATE ON public.blind_date_messages
        FOR EACH ROW EXECUTE FUNCTION public.check_blind_date_message_sender();
    END IF;
END $$;

ALTER TABLE public.blind_date_messages ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- TIER 5: DPDP ACT 2023, IT RULES & LEGAL PROTECTION (Tables 15 to 21)
-- ============================================================================

-- 16. Table 15: public.underage_quarantine_registry
CREATE TABLE IF NOT EXISTS public.underage_quarantine_registry (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    device_hash VARCHAR(64) UNIQUE NOT NULL,
    attempted_dob DATE NOT NULL,
    quarantine_until TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '180 days'),
    attempt_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quarantine_lookup ON public.underage_quarantine_registry(device_hash, quarantine_until);
ALTER TABLE public.underage_quarantine_registry ENABLE ROW LEVEL SECURITY;

-- 17. Table 16: public.data_nominees
CREATE TABLE IF NOT EXISTS public.data_nominees (
    user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    nominee_name VARCHAR(60) NOT NULL,
    nominee_contact VARCHAR(30) NOT NULL,
    relationship VARCHAR(30) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.data_nominees ENABLE ROW LEVEL SECURITY;

-- 18. Table 17: public.data_export_requests
CREATE TABLE IF NOT EXISTS public.data_export_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    status VARCHAR(15) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'expired')),
    export_url TEXT,
    export_payload JSONB,
    checksum_sha256 VARCHAR(64),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.data_export_requests ENABLE ROW LEVEL SECURITY;

-- 19. Table 18: public.consent_audit_logs
CREATE TABLE IF NOT EXISTS public.consent_audit_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    consent_purpose_id VARCHAR(50) NOT NULL,
    is_granted BOOLEAN NOT NULL DEFAULT TRUE,
    ip_hash VARCHAR(64) NOT NULL,
    installation_uuid VARCHAR(64) NOT NULL,
    consented_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consent_audit_user ON public.consent_audit_logs(user_id);
ALTER TABLE public.consent_audit_logs ENABLE ROW LEVEL SECURITY;

-- 20. Table 19: public.grievance_dossiers
CREATE TABLE IF NOT EXISTS public.grievance_dossiers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dossier_reference_id VARCHAR(32) UNIQUE NOT NULL DEFAULT ('GRV-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' || UPPER(SUBSTRING(gen_random_uuid()::TEXT, 1, 6))),
    reporter_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    reported_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    violation_category VARCHAR(30) NOT NULL CHECK (violation_category IN ('harassment', 'explicit_content', 'impersonation', 'underage', 'offplatform_leak')),
    evidence_text VARCHAR(500) NOT NULL DEFAULT '',
    status VARCHAR(15) NOT NULL DEFAULT 'under_review' CHECK (status IN ('under_review', 'actioned', 'dismissed')),
    acknowledgment_sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    statutory_resolution_due_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '15 days'),
    resolution_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actioned_at TIMESTAMPTZ,
    CONSTRAINT chk_grievance_no_self_report CHECK (reporter_id <> reported_user_id)
);

CREATE INDEX IF NOT EXISTS idx_grievance_status ON public.grievance_dossiers(status);
ALTER TABLE public.grievance_dossiers ENABLE ROW LEVEL SECURITY;

-- 21. Table 20: public.blocked_users
CREATE TABLE IF NOT EXISTS public.blocked_users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    blocker_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    blocked_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    reason VARCHAR(50) NOT NULL DEFAULT 'unspecified',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_block_pair UNIQUE (blocker_id, blocked_id),
    CONSTRAINT chk_block_no_self CHECK (blocker_id <> blocked_id)
);

CREATE INDEX IF NOT EXISTS idx_blocked_users_lookup ON public.blocked_users(blocker_id, blocked_id);
ALTER TABLE public.blocked_users ENABLE ROW LEVEL SECURITY;

-- 22. Table 21: public.web_deletion_tokens
CREATE TABLE IF NOT EXISTS public.web_deletion_tokens (
    token VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    auth_id UUID,
    reason TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web_deletion_email ON public.web_deletion_tokens(email);
ALTER TABLE public.web_deletion_tokens ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- TIER 6: ADMINISTRATION & TELEMETRY (Tables 22 to 24)
-- ============================================================================

-- 23. Table 22: public.admin_kyc_escalations
CREATE TABLE IF NOT EXISTS public.admin_kyc_escalations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    declared_dob DATE NOT NULL,
    declared_age INT2 NOT NULL,
    groq_match_score INT2 NOT NULL,
    groq_reasoning VARCHAR(255) NOT NULL,
    anchor_photo_url TEXT NOT NULL,
    kyc_video_url TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_at TIMESTAMPTZ,
    reviewed_by VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.admin_kyc_escalations ENABLE ROW LEVEL SECURITY;

-- 24. Table 23: public.device_fcm_tokens
CREATE TABLE IF NOT EXISTS public.device_fcm_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token VARCHAR(512) UNIQUE NOT NULL,
    platform VARCHAR(20) NOT NULL DEFAULT 'unknown',
    installation_id VARCHAR(128),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_fcm_token UNIQUE (user_id, token)
);

CREATE INDEX IF NOT EXISTS idx_fcm_tokens_user ON public.device_fcm_tokens(user_id) WHERE active = TRUE;
ALTER TABLE public.device_fcm_tokens ENABLE ROW LEVEL SECURITY;

-- 25. Table 24: public.admin_audit_logs
CREATE TABLE IF NOT EXISTS public.admin_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    admin_email VARCHAR(120) NOT NULL,
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id VARCHAR(100),
    details TEXT,
    ip_address VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_audit_created ON public.admin_audit_logs(created_at DESC);
ALTER TABLE public.admin_audit_logs ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- CHUNK 1.4: DATABASE SECURITY FUNCTIONS, RLS POLICIES, TRIGGERS & VIEWS
-- ============================================================================

-- ============================================================================
-- 1. CORE SECURITY HELPER FUNCTIONS
-- ============================================================================

-- 1. Resolve Current Authenticated User ID
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

-- 2. Verify Active Match Participation
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
        JOIN public.users u ON u.auth_id = auth.uid() AND u.deleted_at IS NULL
        WHERE m.id = p_match_id
          AND m.is_active = TRUE
          AND (m.user1_id = u.id OR m.user2_id = u.id)
    );
$$;

-- 3. Verify Bilateral Block Barrier
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

-- 4. Verify Superadmin Privileges
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

-- ============================================================================
-- 2. COMPLETE RLS POLICIES (ALL 24 TABLES)
-- ============================================================================

-- Tier 1: Core Identity & Kinship Engine
DO $$
BEGIN
    -- Table 1: public.users
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'users' AND policyname = 'users_select_owner') THEN
        CREATE POLICY "users_select_owner" ON public.users FOR SELECT TO authenticated USING (auth_id = auth.uid() AND deleted_at IS NULL);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'users' AND policyname = 'users_insert_owner') THEN
        CREATE POLICY "users_insert_owner" ON public.users FOR INSERT TO authenticated WITH CHECK (auth_id = auth.uid());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'users' AND policyname = 'users_update_owner') THEN
        CREATE POLICY "users_update_owner" ON public.users FOR UPDATE TO authenticated USING (auth_id = auth.uid() AND deleted_at IS NULL) WITH CHECK (auth_id = auth.uid());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'users' AND policyname = 'users_delete_service_role') THEN
        CREATE POLICY "users_delete_service_role" ON public.users FOR DELETE TO service_role USING (TRUE);
    END IF;

    -- Table 2: public.swipes
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'swipes' AND policyname = 'swipes_select_actor') THEN
        CREATE POLICY "swipes_select_actor" ON public.swipes FOR SELECT TO authenticated USING (actor_id = public.get_current_user_id() AND NOT public.is_user_blocked(target_id));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'swipes' AND policyname = 'swipes_insert_actor') THEN
        CREATE POLICY "swipes_insert_actor" ON public.swipes FOR INSERT TO authenticated WITH CHECK (actor_id = public.get_current_user_id() AND actor_id <> target_id AND NOT public.is_user_blocked(target_id));
    END IF;

    -- Table 3: public.matches
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'matches' AND policyname = 'matches_select_participants') THEN
        CREATE POLICY "matches_select_participants" ON public.matches FOR SELECT TO authenticated USING (user1_id = public.get_current_user_id() OR user2_id = public.get_current_user_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'matches' AND policyname = 'matches_insert_service_role') THEN
        CREATE POLICY "matches_insert_service_role" ON public.matches FOR INSERT TO service_role WITH CHECK (TRUE);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'matches' AND policyname = 'matches_update_participants') THEN
        CREATE POLICY "matches_update_participants" ON public.matches FOR UPDATE TO authenticated
        USING ((user1_id = public.get_current_user_id() OR user2_id = public.get_current_user_id()) AND is_active = TRUE AND closure_status = 'active')
        WITH CHECK (
            (user1_id = public.get_current_user_id() OR user2_id = public.get_current_user_id())
            AND closure_status IN ('closed_with_grace', 'unmatched')
            AND closed_by_user_id = public.get_current_user_id()
        );
    END IF;

    -- Table 4: public.messages
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'messages' AND policyname = 'messages_select_participants') THEN
        CREATE POLICY "messages_select_participants" ON public.messages FOR SELECT TO authenticated USING (public.is_active_match_participant(match_id));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'messages' AND policyname = 'messages_insert_sender') THEN
        CREATE POLICY "messages_insert_sender" ON public.messages FOR INSERT TO authenticated WITH CHECK (sender_id = public.get_current_user_id() AND public.is_active_match_participant(match_id));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'messages' AND policyname = 'messages_update_status') THEN
        CREATE POLICY "messages_update_status" ON public.messages FOR UPDATE TO authenticated
        USING (public.is_active_match_participant(match_id) AND sender_id <> public.get_current_user_id())
        WITH CHECK (public.is_active_match_participant(match_id) AND sender_id <> public.get_current_user_id());
    END IF;
END $$;

-- Column privilege restrictions on matches and messages
REVOKE UPDATE ON public.matches FROM authenticated;
GRANT UPDATE (closure_status, closed_by_user_id, closed_at, closure_template_key, closure_note) ON public.matches TO authenticated;

REVOKE UPDATE ON public.messages FROM authenticated;
GRANT UPDATE (status) ON public.messages TO authenticated;

-- Tier 2: Monetization, Billing & 5-Network Ad SSV
DO $$
BEGIN
    -- Table 5: public.ad_reward_ledger
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'ad_reward_ledger' AND policyname = 'ad_ledger_select_owner') THEN
        CREATE POLICY "ad_ledger_select_owner" ON public.ad_reward_ledger FOR SELECT TO authenticated USING (user_id = public.get_current_user_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'ad_reward_ledger' AND policyname = 'ad_ledger_insert_service') THEN
        CREATE POLICY "ad_ledger_insert_service" ON public.ad_reward_ledger FOR INSERT TO service_role WITH CHECK (TRUE);
    END IF;

    -- Table 6: public.processed_ad_transactions
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'processed_ad_transactions' AND policyname = 'processed_ads_select_owner') THEN
        CREATE POLICY "processed_ads_select_owner" ON public.processed_ad_transactions FOR SELECT TO authenticated USING (user_id = public.get_current_user_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'processed_ad_transactions' AND policyname = 'processed_ads_manage_service') THEN
        CREATE POLICY "processed_ads_manage_service" ON public.processed_ad_transactions FOR ALL TO service_role USING (TRUE);
    END IF;

    -- Table 7: public.in_app_purchases
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'in_app_purchases' AND policyname = 'iap_select_owner') THEN
        CREATE POLICY "iap_select_owner" ON public.in_app_purchases FOR SELECT TO authenticated USING (user_id = public.get_current_user_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'in_app_purchases' AND policyname = 'iap_manage_service') THEN
        CREATE POLICY "iap_manage_service" ON public.in_app_purchases FOR ALL TO service_role USING (TRUE);
    END IF;

    -- Table 8: public.pending_web_entitlements
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'pending_web_entitlements' AND policyname = 'pending_entitlements_select_owner') THEN
        CREATE POLICY "pending_entitlements_select_owner" ON public.pending_web_entitlements FOR SELECT TO authenticated USING (((email = (auth.jwt() ->> 'email') AND (auth.jwt() ->> 'email_verified')::BOOLEAN = TRUE)) OR public.is_superadmin());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'pending_web_entitlements' AND policyname = 'pending_entitlements_service_role') THEN
        CREATE POLICY "pending_entitlements_service_role" ON public.pending_web_entitlements FOR ALL TO service_role USING (TRUE);
    END IF;
END $$;

-- Tier 3: Cryptographic Revelation & Consent Rituals
DO $$
BEGIN
    -- Table 9: public.whatsapp_reveal_tokens
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'whatsapp_reveal_tokens' AND policyname = 'wa_tokens_select_participants') THEN
        CREATE POLICY "wa_tokens_select_participants" ON public.whatsapp_reveal_tokens FOR SELECT TO authenticated USING (public.is_active_match_participant(match_id));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'whatsapp_reveal_tokens' AND policyname = 'wa_tokens_update_service_role') THEN
        CREATE POLICY "wa_tokens_update_service_role" ON public.whatsapp_reveal_tokens FOR UPDATE TO service_role USING (TRUE) WITH CHECK (TRUE);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'whatsapp_reveal_tokens' AND policyname = 'wa_tokens_manage_service') THEN
        CREATE POLICY "wa_tokens_manage_service" ON public.whatsapp_reveal_tokens FOR ALL TO service_role USING (TRUE);
    END IF;

    -- Table 10: public.contact_reveal_tokens
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'contact_reveal_tokens' AND policyname = 'contact_tokens_select_participants') THEN
        CREATE POLICY "contact_tokens_select_participants" ON public.contact_reveal_tokens FOR SELECT TO authenticated USING (public.is_active_match_participant(match_id));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'contact_reveal_tokens' AND policyname = 'contact_tokens_update_service_role') THEN
        CREATE POLICY "contact_tokens_update_service_role" ON public.contact_reveal_tokens FOR UPDATE TO service_role USING (TRUE) WITH CHECK (TRUE);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'contact_reveal_tokens' AND policyname = 'contact_tokens_manage_service') THEN
        CREATE POLICY "contact_tokens_manage_service" ON public.contact_reveal_tokens FOR ALL TO service_role USING (TRUE);
    END IF;

    -- Table 11: public.photo_reveal_consents
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'photo_reveal_consents' AND policyname = 'photo_reveal_select_participants') THEN
        CREATE POLICY "photo_reveal_select_participants" ON public.photo_reveal_consents FOR SELECT TO authenticated USING (requester_id = public.get_current_user_id() OR target_id = public.get_current_user_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'photo_reveal_consents' AND policyname = 'photo_reveal_insert_requester') THEN
        CREATE POLICY "photo_reveal_insert_requester" ON public.photo_reveal_consents FOR INSERT TO authenticated WITH CHECK (requester_id = public.get_current_user_id() AND requester_id <> target_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'photo_reveal_consents' AND policyname = 'photo_reveal_update_target') THEN
        CREATE POLICY "photo_reveal_update_target" ON public.photo_reveal_consents FOR UPDATE TO authenticated USING (target_id = public.get_current_user_id());
    END IF;
END $$;

-- Tier 4: Anonymous Fast-Track Subsystem
DO $$
BEGIN
    -- Table 12: public.blind_date_queue
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'blind_date_queue' AND policyname = 'blind_queue_select_owner') THEN
        CREATE POLICY "blind_queue_select_owner" ON public.blind_date_queue FOR SELECT TO authenticated USING (user_id = public.get_current_user_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'blind_date_queue' AND policyname = 'blind_queue_insert_owner') THEN
        CREATE POLICY "blind_queue_insert_owner" ON public.blind_date_queue FOR INSERT TO authenticated WITH CHECK (user_id = public.get_current_user_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'blind_date_queue' AND policyname = 'blind_queue_delete_owner') THEN
        CREATE POLICY "blind_queue_delete_owner" ON public.blind_date_queue FOR DELETE TO authenticated USING (user_id = public.get_current_user_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'blind_date_queue' AND policyname = 'blind_queue_service_role') THEN
        CREATE POLICY "blind_queue_service_role" ON public.blind_date_queue FOR ALL TO service_role USING (TRUE);
    END IF;

    -- Table 13: public.blind_date_sessions
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'blind_date_sessions' AND policyname = 'blind_session_select_participants') THEN
        CREATE POLICY "blind_session_select_participants" ON public.blind_date_sessions FOR SELECT TO authenticated USING (user1_id = public.get_current_user_id() OR user2_id = public.get_current_user_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'blind_date_sessions' AND policyname = 'blind_session_update_service_role') THEN
        CREATE POLICY "blind_session_update_service_role" ON public.blind_date_sessions FOR UPDATE TO service_role USING (TRUE) WITH CHECK (TRUE);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'blind_date_sessions' AND policyname = 'blind_session_service_role') THEN
        CREATE POLICY "blind_session_service_role" ON public.blind_date_sessions FOR ALL TO service_role USING (TRUE);
    END IF;

    -- Table 14: public.blind_date_messages
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'blind_date_messages' AND policyname = 'blind_msg_select_participants') THEN
        CREATE POLICY "blind_msg_select_participants" ON public.blind_date_messages FOR SELECT TO authenticated USING (sender_id = public.get_current_user_id() OR recipient_id = public.get_current_user_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'blind_date_messages' AND policyname = 'blind_msg_insert_sender') THEN
        CREATE POLICY "blind_msg_insert_sender" ON public.blind_date_messages FOR INSERT TO authenticated
        WITH CHECK (
            sender_id = public.get_current_user_id()
            AND EXISTS (
                SELECT 1 FROM public.blind_date_sessions s
                WHERE s.id = session_id
                  AND s.status = 'active'
                  AND (
                      (s.user1_id = public.get_current_user_id() AND recipient_id = s.user2_id)
                      OR (s.user2_id = public.get_current_user_id() AND recipient_id = s.user1_id)
                  )
            )
        );
    END IF;
END $$;

-- Tier 5: DPDP Act 2023, IT Rules & Legal Protection
REVOKE ALL ON public.underage_quarantine_registry FROM anon, authenticated;
REVOKE ALL ON public.web_deletion_tokens FROM anon, authenticated;

DO $$
BEGIN
    -- Table 15: public.underage_quarantine_registry
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'underage_quarantine_registry' AND policyname = 'underage_service_role_all') THEN
        CREATE POLICY "underage_service_role_all" ON public.underage_quarantine_registry FOR ALL TO service_role USING (TRUE);
    END IF;

    -- Table 16: public.data_nominees
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'data_nominees' AND policyname = 'data_nominees_all_owner') THEN
        CREATE POLICY "data_nominees_all_owner" ON public.data_nominees FOR ALL TO authenticated USING (user_id = public.get_current_user_id()) WITH CHECK (user_id = public.get_current_user_id());
    END IF;

    -- Table 17: public.data_export_requests
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'data_export_requests' AND policyname = 'data_export_all_owner') THEN
        CREATE POLICY "data_export_all_owner" ON public.data_export_requests FOR ALL TO authenticated USING (user_id = public.get_current_user_id()) WITH CHECK (user_id = public.get_current_user_id());
    END IF;

    -- Table 18: public.consent_audit_logs
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'consent_audit_logs' AND policyname = 'consent_logs_select_owner') THEN
        CREATE POLICY "consent_logs_select_owner" ON public.consent_audit_logs FOR SELECT TO authenticated USING (user_id = public.get_current_user_id());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'consent_audit_logs' AND policyname = 'consent_logs_insert_owner') THEN
        CREATE POLICY "consent_logs_insert_owner" ON public.consent_audit_logs FOR INSERT TO authenticated WITH CHECK (user_id = public.get_current_user_id());
    END IF;

    -- Table 19: public.grievance_dossiers
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'grievance_dossiers' AND policyname = 'grievance_select_reporter') THEN
        CREATE POLICY "grievance_select_reporter" ON public.grievance_dossiers FOR SELECT TO authenticated USING (reporter_id = public.get_current_user_id() OR public.is_superadmin());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'grievance_dossiers' AND policyname = 'grievance_insert_reporter') THEN
        CREATE POLICY "grievance_insert_reporter" ON public.grievance_dossiers FOR INSERT TO authenticated WITH CHECK (reporter_id = public.get_current_user_id() AND (reported_user_id IS NULL OR reporter_id <> reported_user_id));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'grievance_dossiers' AND policyname = 'grievance_admin_update') THEN
        CREATE POLICY "grievance_admin_update" ON public.grievance_dossiers FOR UPDATE TO authenticated USING (public.is_superadmin());
    END IF;

    -- Table 20: public.blocked_users
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'blocked_users' AND policyname = 'blocked_users_all_blocker') THEN
        CREATE POLICY "blocked_users_all_blocker" ON public.blocked_users FOR ALL TO authenticated USING (blocker_id = public.get_current_user_id()) WITH CHECK (blocker_id = public.get_current_user_id() AND blocker_id <> blocked_id);
    END IF;

    -- Table 21: public.web_deletion_tokens
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'web_deletion_tokens' AND policyname = 'web_deletion_service_role') THEN
        CREATE POLICY "web_deletion_service_role" ON public.web_deletion_tokens FOR ALL TO service_role USING (TRUE);
    END IF;

    -- Table 22: public.admin_kyc_escalations
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'admin_kyc_escalations' AND policyname = 'kyc_escalation_select_owner') THEN
        CREATE POLICY "kyc_escalation_select_owner" ON public.admin_kyc_escalations FOR SELECT TO authenticated USING (user_id = public.get_current_user_id() OR public.is_superadmin());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'admin_kyc_escalations' AND policyname = 'kyc_escalation_admin_manage') THEN
        CREATE POLICY "kyc_escalation_admin_manage" ON public.admin_kyc_escalations FOR ALL TO authenticated USING (public.is_superadmin());
    END IF;

    -- Table 23: public.device_fcm_tokens
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'device_fcm_tokens' AND policyname = 'device_fcm_all_owner') THEN
        CREATE POLICY "device_fcm_all_owner" ON public.device_fcm_tokens FOR ALL TO authenticated USING (user_id = public.get_current_user_id()) WITH CHECK (user_id = public.get_current_user_id());
    END IF;

    -- Table 24: public.admin_audit_logs
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'admin_audit_logs' AND policyname = 'admin_audit_logs_superadmin_all') THEN
        CREATE POLICY "admin_audit_logs_superadmin_all" ON public.admin_audit_logs FOR ALL TO authenticated USING (public.is_superadmin());
    END IF;
END $$;

-- ============================================================================
-- 3. INTEGRITY TRIGGERS & ANTI-TAMPERING ENGINE
-- ============================================================================

-- 3.1 Match Participant Immutability and Grace Closure Trigger
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
    IF NEW.closure_status IN ('closed_with_grace', 'unmatched') THEN
        NEW.is_active := FALSE;
    END IF;
    RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trg_protect_match_participants'
          AND tgrelid = 'public.matches'::regclass
    ) THEN
        CREATE TRIGGER trg_protect_match_participants
        BEFORE UPDATE ON public.matches
        FOR EACH ROW
        EXECUTE FUNCTION public.protect_match_participants();
    END IF;
END $$;

-- 3.2 Privilege Escalation Guard on Registration
CREATE OR REPLACE FUNCTION public.prevent_user_insert_privileges()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    IF auth.role() = 'service_role' THEN
        RETURN NEW;
    END IF;

    NEW.role := 'user';
    NEW.kyc_status := FALSE;
    NEW.is_voice_verified := FALSE;
    NEW.subscription_tier := 'free';
    NEW.subscription_expires_at := NULL;
    NEW.is_ad_free := FALSE;
    NEW.reward_balance := 0;
    NEW.boost_points := 0;
    NEW.swipes_remaining := 25;
    NEW.reveal_tokens_count := 1;
    NEW.direct_letters_count := 1;
    NEW.streak_count := 0;
    NEW.blind_date_passes := 0;
    NEW.deleted_at := NULL;
    RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'tr_prevent_user_insert_privileges'
          AND tgrelid = 'public.users'::regclass
    ) THEN
        CREATE TRIGGER tr_prevent_user_insert_privileges
        BEFORE INSERT ON public.users
        FOR EACH ROW
        EXECUTE FUNCTION public.prevent_user_insert_privileges();
    END IF;
END $$;

-- 3.3 Anti-Tampering Trigger for Sensitive User Attributes
CREATE OR REPLACE FUNCTION public.prevent_user_field_tampering()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    IF auth.role() = 'service_role' OR public.is_superadmin() THEN
        RETURN NEW;
    END IF;

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
    IF NEW.blind_date_passes IS DISTINCT FROM OLD.blind_date_passes
       OR NEW.last_blind_date_date IS DISTINCT FROM OLD.last_blind_date_date THEN
        RAISE EXCEPTION 'Tampering detected: blind date entitlements are server-managed';
    END IF;
    IF NEW.streak_expires_at IS DISTINCT FROM OLD.streak_expires_at
       OR NEW.last_streak_ad_at IS DISTINCT FROM OLD.last_streak_ad_at THEN
        RAISE EXCEPTION 'Tampering detected: streak timestamps are managed by daily cycle engine';
    END IF;
    IF NEW.referral_code IS DISTINCT FROM OLD.referral_code OR NEW.id IS DISTINCT FROM OLD.id THEN
        RAISE EXCEPTION 'Tampering detected: identity fields are immutable';
    END IF;

    RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'tr_prevent_user_tampering'
          AND tgrelid = 'public.users'::regclass
    ) THEN
        CREATE TRIGGER tr_prevent_user_tampering
        BEFORE UPDATE ON public.users
        FOR EACH ROW
        EXECUTE FUNCTION public.prevent_user_field_tampering();
    END IF;
END $$;

-- 3.3 Auto-Timestamp Refresh Trigger
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'tr_users_updated_at'
          AND tgrelid = 'public.users'::regclass
    ) THEN
        CREATE TRIGGER tr_users_updated_at
        BEFORE UPDATE ON public.users
        FOR EACH ROW
        EXECUTE FUNCTION public.handle_updated_at();
    END IF;
END $$;

-- 3.5 Cascade Storage and Account Cleanup Triggers
CREATE OR REPLACE FUNCTION public.handle_user_cascade_cleanup()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    -- 1. Purge media objects from ur-heart-media storage bucket with storage bypass config
    PERFORM set_config('storage.allow_delete_query', 'true', true);
    DELETE FROM storage.objects
    WHERE bucket_id = 'ur-heart-media'
      AND (name LIKE ('users/' || OLD.auth_id::text || '/%'));
    PERFORM set_config('storage.allow_delete_query', 'false', true);

    RETURN OLD;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trg_user_cascade_cleanup'
          AND tgrelid = 'public.users'::regclass
    ) THEN
        CREATE TRIGGER trg_user_cascade_cleanup
        BEFORE DELETE ON public.users
        FOR EACH ROW
        EXECUTE FUNCTION public.handle_user_cascade_cleanup();
    END IF;
END $$;

CREATE OR REPLACE FUNCTION public.handle_user_auth_cleanup()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    -- 2. Cascade hard delete to auth.users if not already executing from auth cascade
    IF OLD.auth_id IS NOT NULL AND pg_trigger_depth() <= 1 THEN
        DELETE FROM auth.users
        WHERE id = OLD.auth_id;
    END IF;

    RETURN NULL;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trg_user_auth_cleanup'
          AND tgrelid = 'public.users'::regclass
    ) THEN
        CREATE TRIGGER trg_user_auth_cleanup
        AFTER DELETE ON public.users
        FOR EACH ROW
        EXECUTE FUNCTION public.handle_user_auth_cleanup();
    END IF;
END $$;

-- ============================================================================
-- 4. SECURE DISCOVERY PROJECTION VIEW
-- ============================================================================

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
    CASE 
        WHEN u.is_photo_veiled THEN ARRAY[]::TEXT[] 
        ELSE u.photos 
    END AS photos,
    CASE 
        WHEN u.is_photo_veiled THEN NULL 
        ELSE u.avatar_url 
    END::VARCHAR(500) AS avatar_url,
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

GRANT SELECT ON public.discovery_profiles TO authenticated;

-- ============================================================================
-- 5. MAINTENANCE & DATA RETENTION AUTOMATION
-- ============================================================================

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

REVOKE EXECUTE ON FUNCTION public.purge_expired_temporary_records() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.purge_expired_temporary_records() TO service_role;

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


