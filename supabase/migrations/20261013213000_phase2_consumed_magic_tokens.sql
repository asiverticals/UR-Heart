-- UR-Heart Sanctuary — Phase 2: Forward Migration
-- Consumed Magic Link Tokens Ledger for Multi-Process Replay Protection

CREATE TABLE IF NOT EXISTS public.consumed_magic_tokens (
    jti VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_consumed_magic_tokens_expires_at ON public.consumed_magic_tokens(expires_at);

ALTER TABLE public.consumed_magic_tokens ENABLE ROW LEVEL SECURITY;
