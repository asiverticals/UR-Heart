-- UR-Heart Sanctuary — Phase 1: Forward Migration
-- Data Remediation & Safe Constraint Alignment

-- 1. in_app_purchases: user_id ON DELETE SET NULL & Non-negative amounts
ALTER TABLE public.in_app_purchases ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE public.in_app_purchases DROP CONSTRAINT IF EXISTS in_app_purchases_user_id_fkey;
ALTER TABLE public.in_app_purchases
    ADD CONSTRAINT in_app_purchases_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE public.in_app_purchases ALTER COLUMN status SET DEFAULT 'pending';

-- Pre-remediate any historical negative amounts
UPDATE public.in_app_purchases
SET amount_gross = 0.00
WHERE amount_gross < 0;

UPDATE public.in_app_purchases
SET platform_fee = 0.00
WHERE platform_fee < 0;

UPDATE public.in_app_purchases
SET amount_net = 0.00
WHERE amount_net < 0;

ALTER TABLE public.in_app_purchases DROP CONSTRAINT IF EXISTS chk_iap_nonnegative_amounts;
ALTER TABLE public.in_app_purchases
    ADD CONSTRAINT chk_iap_nonnegative_amounts
    CHECK (amount_gross >= 0 AND platform_fee >= 0 AND amount_net >= 0);

-- 2. pending_web_entitlements: Non-negative amounts
UPDATE public.pending_web_entitlements
SET amount_gross = 0.00
WHERE amount_gross < 0;

ALTER TABLE public.pending_web_entitlements DROP CONSTRAINT IF EXISTS chk_web_entitlement_nonnegative_amount;
ALTER TABLE public.pending_web_entitlements
    ADD CONSTRAINT chk_web_entitlement_nonnegative_amount
    CHECK (amount_gross >= 0);

-- 3. whatsapp_reveal_tokens & contact_reveal_tokens: Clamp ad counts to [0, 3]
UPDATE public.whatsapp_reveal_tokens
SET user1_ads_count = LEAST(GREATEST(user1_ads_count, 0), 3),
    user2_ads_count = LEAST(GREATEST(user2_ads_count, 0), 3)
WHERE user1_ads_count < 0 OR user1_ads_count > 3
   OR user2_ads_count < 0 OR user2_ads_count > 3;

ALTER TABLE public.whatsapp_reveal_tokens DROP CONSTRAINT IF EXISTS whatsapp_reveal_tokens_user1_ads_count_check;
ALTER TABLE public.whatsapp_reveal_tokens DROP CONSTRAINT IF EXISTS whatsapp_reveal_tokens_user2_ads_count_check;
ALTER TABLE public.whatsapp_reveal_tokens DROP CONSTRAINT IF EXISTS chk_wa_user1_ads;
ALTER TABLE public.whatsapp_reveal_tokens DROP CONSTRAINT IF EXISTS chk_wa_user2_ads;
ALTER TABLE public.whatsapp_reveal_tokens
    ADD CONSTRAINT chk_wa_user1_ads CHECK (user1_ads_count BETWEEN 0 AND 3),
    ADD CONSTRAINT chk_wa_user2_ads CHECK (user2_ads_count BETWEEN 0 AND 3);

UPDATE public.contact_reveal_tokens
SET user1_ads_count = LEAST(GREATEST(user1_ads_count, 0), 3),
    user2_ads_count = LEAST(GREATEST(user2_ads_count, 0), 3)
WHERE user1_ads_count < 0 OR user1_ads_count > 3
   OR user2_ads_count < 0 OR user2_ads_count > 3;

ALTER TABLE public.contact_reveal_tokens DROP CONSTRAINT IF EXISTS contact_reveal_tokens_user1_ads_count_check;
ALTER TABLE public.contact_reveal_tokens DROP CONSTRAINT IF EXISTS contact_reveal_tokens_user2_ads_count_check;
ALTER TABLE public.contact_reveal_tokens DROP CONSTRAINT IF EXISTS chk_contact_user1_ads;
ALTER TABLE public.contact_reveal_tokens DROP CONSTRAINT IF EXISTS chk_contact_user2_ads;
ALTER TABLE public.contact_reveal_tokens
    ADD CONSTRAINT chk_contact_user1_ads CHECK (user1_ads_count BETWEEN 0 AND 3),
    ADD CONSTRAINT chk_contact_user2_ads CHECK (user2_ads_count BETWEEN 0 AND 3);

-- 4. blind_date_queue: Normalize historical preferred age bounds to adult range
UPDATE public.blind_date_queue
SET preferred_age_min = 18
WHERE preferred_age_min < 18;

UPDATE public.blind_date_queue
SET preferred_age_max = GREATEST(preferred_age_max, preferred_age_min)
WHERE preferred_age_min > preferred_age_max;

ALTER TABLE public.blind_date_queue DROP CONSTRAINT IF EXISTS chk_blind_queue_age_range;
ALTER TABLE public.blind_date_queue
    ADD CONSTRAINT chk_blind_queue_age_range
    CHECK (preferred_age_min >= 18 AND preferred_age_min <= preferred_age_max);
