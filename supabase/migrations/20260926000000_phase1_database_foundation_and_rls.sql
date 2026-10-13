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
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_check_message_sender'
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
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    transaction_reference VARCHAR(150) UNIQUE NOT NULL,
    product_identifier VARCHAR(60) NOT NULL,
    store VARCHAR(30) NOT NULL DEFAULT 'google_play' CHECK (store IN ('google_play', 'web_razorpay_india', 'web_stripe_global')),
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    amount_gross NUMERIC(10,2) NOT NULL,
    platform_fee NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    amount_net NUMERIC(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'completed' CHECK (status IN ('pending', 'completed', 'refunded')),
    purchased_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
    claimed_at TIMESTAMPTZ
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
    user1_ads_count INT2 NOT NULL DEFAULT 0 CHECK (user1_ads_count <= 3),
    user2_ads_count INT2 NOT NULL DEFAULT 0 CHECK (user2_ads_count <= 3),
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
    user1_ads_count INT2 NOT NULL DEFAULT 0 CHECK (user1_ads_count <= 3),
    user2_ads_count INT2 NOT NULL DEFAULT 0 CHECK (user2_ads_count <= 3),
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
    CONSTRAINT chk_blind_queue_age_range CHECK (preferred_age_min <= preferred_age_max)
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

-- Trigger: Enforce sender belongs to the referenced blind date session
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
          AND (user1_id = NEW.sender_id OR user2_id = NEW.sender_id)
    ) THEN
        RAISE EXCEPTION 'Sender % is not a participant in blind date session %', NEW.sender_id, NEW.session_id;
    END IF;
    RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_check_blind_date_message_sender'
    ) THEN
        CREATE TRIGGER trg_check_blind_date_message_sender
        BEFORE INSERT OR UPDATE ON public.blind_date_messages
        FOR EACH ROW EXECUTE FUNCTION public.check_blind_date_message_sender();
    END IF;
END $$;

ALTER TABLE public.blind_date_messages ENABLE ROW LEVEL SECURITY;

