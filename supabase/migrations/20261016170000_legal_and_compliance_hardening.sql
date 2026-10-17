-- ==============================================================================
-- Migration: 20261016170000_legal_and_compliance_hardening.sql
-- Subsystem: Supabase PostgreSQL Database Legal & Compliance Foundation
-- Purpose: Harmonize database check constraints and statutory definitions for:
--          1. IT Rules 2021 Rule 3(2)(b): Add 'ncii' (Non-Consensual Intimate Imagery)
--             to public.grievance_dossiers violation_category check constraint to ensure
--             emergency 24-hour takedown grievances can be persisted without IntegrityError.
--          2. Section 79 IT Act 2000 Safe Harbor retention and due diligence compliance.
-- ==============================================================================

-- 1. Align public.grievance_dossiers violation_category check constraint with 'ncii'
ALTER TABLE public.grievance_dossiers 
    DROP CONSTRAINT IF EXISTS chk_grievance_category;
ALTER TABLE public.grievance_dossiers 
    DROP CONSTRAINT IF EXISTS grievance_dossiers_violation_category_check;

ALTER TABLE public.grievance_dossiers 
    ADD CONSTRAINT chk_grievance_category 
    CHECK (violation_category IN (
        'harassment',
        'explicit_content',
        'impersonation',
        'underage',
        'offplatform_leak',
        'ncii',
        'underage_suspicion',
        'inappropriate_content',
        'fraud',
        'other'
    ));

-- 2. Align public.in_app_purchases store check constraint with Apple StoreKit & RevenueCat (Apple Guideline 3.1.1)
ALTER TABLE public.in_app_purchases 
    DROP CONSTRAINT IF EXISTS chk_iap_store;
ALTER TABLE public.in_app_purchases 
    DROP CONSTRAINT IF EXISTS in_app_purchases_store_check;

ALTER TABLE public.in_app_purchases 
    ADD CONSTRAINT chk_iap_store 
    CHECK (store IN (
        'google_play',
        'apple_storekit',
        'revenuecat_in_app',
        'web_razorpay_india',
        'web_stripe_global',
        'stripe_web'
    ));
