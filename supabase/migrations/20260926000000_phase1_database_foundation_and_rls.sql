-- UR-Heart Sanctuary — Phase 1: Chunk 1.1 Database Foundation (Tables 1 to 4)
-- Architectural Invariants:
-- 1. Stateless PostgreSQL 15+ engine with strict referential integrity.
-- 2. Foreign keys enforce ON DELETE CASCADE (with closed_by_user_id ON DELETE SET NULL).
-- 3. Cloudflare R2 URLs stored for media assets; zero unasked dynamic JSON in domain layer.

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
    referral_code VARCHAR(16) UNIQUE NOT NULL DEFAULT ('SANCTUARY-' || UPPER(SUBSTRING(gen_random_uuid()::TEXT, 1, 6))),
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
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Compound Indexes for Feed Filtering & Boost Scoring
CREATE INDEX IF NOT EXISTS idx_users_auth_id ON public.users (auth_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_feed_filter ON public.users (gender, interested_in, kyc_status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_discovery_boost ON public.users (boost_points DESC, streak_count DESC, created_at DESC) WHERE deleted_at IS NULL AND is_profile_completed = TRUE;

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
    CONSTRAINT chk_matches_no_self_match CHECK (user1_id <> user2_id)
);

CREATE INDEX IF NOT EXISTS idx_matches_user1 ON public.matches(user1_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_matches_user2 ON public.matches(user2_id) WHERE is_active = TRUE;

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
