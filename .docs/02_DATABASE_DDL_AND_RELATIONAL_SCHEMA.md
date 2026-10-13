1. Relational Architecture & Extension Requirements
UR-Heart Sanctuary ka database architecture Supabase PostgreSQL 15+ engine par stateless connection pooler (PgBouncer port 6543) ke saath operate karta hai. Schema design me mathematical symmetry, referential integrity, aur zero dynamic data structures follow kiye gaye hain.
MD

+ 1

Mandatory PostgreSQL Extensions
Kisi bhi table creation migration se pehle ye core extensions database me active hone chahiye:
MD

SQL

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

MD

Master Schema Topology (24 Relational Tables)
Database ko 6 logical functional tiers me divide kiya gaya hai:
MD

Core Identity & Kinship: users, swipes, matches, messages.
MD

Monetization & Ad SSV: ad_reward_ledger, processed_ad_transactions, in_app_purchases, pending_web_entitlements.
MD

Cryptographic Reveal Rituals: whatsapp_reveal_tokens, contact_reveal_tokens, photo_reveal_consents.
MD

Anonymous Fast-Track (Condition C1): blind_date_queue, blind_date_sessions, blind_date_messages.
MD

DPDP Act & Legal Protection: underage_quarantine_registry, data_nominees, data_export_requests, consent_audit_logs, grievance_dossiers, blocked_users, web_deletion_tokens.
MD

Administration & Telemetry: admin_kyc_escalations, device_fcm_tokens, admin_audit_logs.
MD

1. Complete Relational DDL Specifications (Tables 1 to 24)
Tier 1: Core Identity & Kinship Engine
Table 1: public.users
Platform ka primary entity table jo seekers ki complete profile, biometric verification state, location fuzzing, aur streak metrics store karta hai.
MD

SQL

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

MD

Table 2: public.swipes
Discovery deck me seeker actions (like, pass, superlike) record karta hai. Bilateral uniqueness enforce karta hai.
MD

+ 1

SQL

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

MD

Table 3: public.matches
Mutual resonance hone par ya Direct Letter bhejne par banne wala active dialogue connection. "Pass with Grace" closure states support karta hai.
MD

+ 1

SQL

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

MD

Table 4: public.messages
Match participants ke beech encrypted text dialogue persist karta hai. Client-side idempotency key aur delivery status maintain karta hai.
MD

+ 1

SQL

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

MD

Tier 2: Monetization, Billing & 5-Network Ad SSV
Table 5: public.ad_reward_ledger
Ad SSV verification callbacks ka primary audit log. Duplicate reward credit block karta hai.
MD

+ 1

SQL

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

MD

Table 6: public.processed_ad_transactions
Replay defense layer jo fast-lookup provide karti hai ad transaction duplicate attempts par.
MD

SQL

CREATE TABLE IF NOT EXISTS public.processed_ad_transactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id VARCHAR(150) UNIQUE NOT NULL,
    network VARCHAR(20) NOT NULL,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    ad_type VARCHAR(30) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

MD

Table 7: public.in_app_purchases
Google Play Billing v3 aur Web store purchase receipts ka statutory financial log. Platform fee accounting maintain karta hai.
MD

+ 1

SQL

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

MD

Table 8: public.pending_web_entitlements
Web store (/store) par unauthenticated guest checkout ke entitlements store karta hai. User login karte hi atomically claim hote hain.
MD

+ 1

SQL

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

MD

Tier 3: Cryptographic Revelation & Consent Rituals
Table 9: public.whatsapp_reveal_tokens
Stage 3 Sacred Contact Bridge ke legacy WhatsApp handles ke bilateral unsealing counter ko track karta hai (3 mindful ads ya ₹99 pass).
MD

SQL

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

MD

Table 10: public.contact_reveal_tokens
Unified multi-platform Contact Bridge (Instagram, Telegram, Signal, WhatsApp) bilateral token exchange.
MD

SQL

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

MD

Table 11: public.photo_reveal_consents
Stage 1 Discovery deck me 35px blur veil ko unmask karne ki bilateral requests track karta hai.
MD

SQL

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

MD

Tier 4: Anonymous Fast-Track Subsystem (Condition C1)
Table 12: public.blind_date_queue
Condition C1 (1M MAU gate) ke under synchronous matchmaking FIFO queue maintain karta hai.
MD

SQL

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
    paired_session_id UUID
);

CREATE INDEX IF NOT EXISTS idx_blind_queue_matching ON public.blind_date_queue(gender, status, joined_at) WHERE status = 'waiting';

MD

Table 13: public.blind_date_sessions
5-minute (300 seconds) timed anonymous chamber session state. Both 'resonate' par mutual match provision karta hai.
MD

+ 1

SQL

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

MD

Table 14: public.blind_date_messages
Anonymous session ke dauran exchange hone wale ephemeral messages.
MD

SQL

CREATE TABLE IF NOT EXISTS public.blind_date_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.blind_date_sessions(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    recipient_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    ciphertext TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_blind_msg_session ON public.blind_date_messages(session_id, created_at ASC);

MD

Tier 5: DPDP Act 2023, IT Rules & Legal Protection
Table 15: public.underage_quarantine_registry
Hardware-level anti-tampering lock. Underage declared DOB par SHA-256 device hash ko 180 days tak quarantine karta hai.
MD

+ 1

SQL

CREATE TABLE IF NOT EXISTS public.underage_quarantine_registry (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    device_hash VARCHAR(64) UNIQUE NOT NULL,
    attempted_dob DATE NOT NULL,
    quarantine_until TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '180 days'),
    attempt_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quarantine_lookup ON public.underage_quarantine_registry(device_hash, quarantine_until);

MD

Table 16: public.data_nominees
India DPDP Act 2023 Section 14 compliance: Seeker ke digital nominee rights record karta hai.
MD

SQL

CREATE TABLE IF NOT EXISTS public.data_nominees (
    user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    nominee_name VARCHAR(60) NOT NULL,
    nominee_contact VARCHAR(30) NOT NULL,
    relationship VARCHAR(30) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

MD

Table 17: public.data_export_requests
DPDP Act Section 11 Data Portability archive generation status aur checksum record karta hai.
MD

SQL

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

MD

Table 18: public.consent_audit_logs
DPDP Act Section 6 Purpose-Limitation consent tracking. Hardware installation UUID aur SHA-256 IP hash capture karta hai.
MD

+ 1

SQL

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

MD

Table 19: public.grievance_dossiers
IT Rules 2021 Rule 3(2) statutory grievance register. 24h acknowledgement aur 15d SLA mandatory maintain karta hai.
MD

+ 1

SQL

CREATE TABLE IF NOT EXISTS public.grievance_dossiers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dossier_reference_id VARCHAR(32) UNIQUE NOT NULL DEFAULT ('GRV-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' || UPPER(SUBSTRING(gen_random_uuid()::TEXT, 1, 6))),
    reporter_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    reported_user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
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

MD

Table 20: public.blocked_users
Seekers ke beech bilateral block barrier enforce karta hai. Feeds aur chats se complete erasure karta hai.
MD

+ 1

SQL

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

MD

Table 21: public.web_deletion_tokens
Google Play Data Safety & DPDP Act Section 12 web account deletion (/delete-account) verification tokens. 15-minute validity window.
MD

+ 1

SQL

CREATE TABLE IF NOT EXISTS public.web_deletion_tokens (
    token VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    auth_id UUID,
    reason TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

MD

Tier 6: Administration & Telemetry
Table 22: public.admin_kyc_escalations
Groq Vision AI liveness check me low confidence aane par superadmin review ke liye manual queue.
MD

SQL

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

MD

Table 23: public.device_fcm_tokens
Active hardware FCM tokens maintain karta hai. Re-installations par previous associations ko detach karta hai.
MD

+ 1

SQL

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

MD

Table 24: public.admin_audit_logs
Superadmin level actions (ban, unban, override_kyc, config_update) ka immutable security trail.
MD

SQL

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

MD

1. Production Migration File Placement
Ye DDL code seedhe repository ke migration structure me save kiya jayega:

Plaintext

supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql
