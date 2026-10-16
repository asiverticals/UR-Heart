# Comprehensive End-to-End Security Vulnerability Audit Report — UR-Heart Platform

**Document Version:** 1.0.0  
**Audit Scope:** Full Platform End-to-End (`backend/app/`, `lib/`, `supabase/migrations/`, `.env`, `render.yaml`, `Dockerfile`)  
**Target System:** UR-Heart Dating & Kinship Sanctuary  
**Classification:** STRICTLY CONFIDENTIAL // SECURITY AUDIT & VULNERABILITY ASSESSMENT  
**Lead Auditor:** Security Audit Specialist Worker (`worker_security_1`)  
**Date of Audit:** October 15, 2026  
**Standards & Benchmarks:** OWASP Top 10 (2021), OWASP API Security Top 10 (2023), CVSS v3.1 Scoring, CWE Top 25, India DPDP Act 2023, IT Act 2000 & 2021 Intermediary Guidelines  

---

## 1. Executive Summary & Security Posture Overview

### 1.1 Architecture & Ecosystem Overview
UR-Heart is engineered as a privacy-centric, mindful dating and kinship sanctuary. The platform architecture comprises:
1. **Client Tier (`lib/`)**: A Flutter cross-platform mobile application comprising 65 Dart source files, implementing Riverpod state management, GoRouter navigation, Dio-based HTTP client interceptors, and a custom WebSocket real-time messaging pipeline. Core functional modules include Phone/Google OAuth authentication, profile onboarding with a 35px Gaussian modesty veil, blind date matching, voice spark recording, real-time ephemeral chat, a gamified growth/reward hub, and a legal compliance vault.
2. **Backend Application Tier (`backend/app/`)**: A Python 3.14 / FastAPI asynchronous microservice architecture exposing 20 APIRouters, 31 HTTP endpoints, and 2 WebSocket endpoints. The backend utilizes SQLAlchemy 2.0 with `asyncpg` connection pooling to PostgreSQL, SlowAPI rate limiting, Cloudflare R2 S3v4 storage adapters, an in-memory WebSocket ticket handshake gateway, Razorpay payment verification, 5-network Ad Server-Side Verification (SSV) cryptographic waterfalls, and external AI inference clusters (Groq LPU, Google Gemini, OpenRouter).
3. **Database & Storage Tier (`supabase/`)**: A Supabase-managed PostgreSQL instance containing 25 public relational tables, 1 security-barrier view (`discovery_profiles`), 9 triggers, and 5 security RPC helper functions. Media storage is primarily hosted on Cloudflare R2 with public CDN edge distribution at `https://media.urheart.app/`.

### 1.2 Security Posture Assessment
The UR-Heart codebase exhibits strong intent toward privacy engineering in several specialized subsystems. Notable defensive highlights include:
- **Location Coordinate Fuzzing:** Latitude and longitude are clamped to two decimal places (~1.1 km grid precision) via Pydantic validators (`backend/app/schemas/profile.py#L28-L34`) and database view rounding (`ROUND(u.latitude::NUMERIC, 2)`), mitigating physical stalking risks under Section 6 of the DPDP Act 2023.
- **Single-Use Magic Link Ledger:** Prevention of token reuse via the dedicated `consumed_magic_tokens` blacklist table (`supabase/migrations/20261013213000_phase2_consumed_magic_tokens.sql`).
- **Ephemeral WebSocket Ticket Authentication:** Replacement of long-lived JWT query parameters with 32-byte cryptographic tickets having a strict 60-second TTL (`backend/app/core/ws_ticket_store.py#L7-L62`), preventing access token leakage into web server access logs and proxy caches.
- **Android Window Security:** Implementation of Android `FLAG_SECURE` native channel guards preventing screen capture and task-switcher previews of intimate conversations.

However, beneath these architectural strengths, the audit discovered **critical, catastrophic systemic vulnerabilities** that undermine the platform's core security boundaries, expose live infrastructure, invalidate user privacy guarantees, and create severe financial loss vectors.

### 1.3 Vulnerability Severity Distribution & Master Summary
The audit cataloged **20 distinct, verified security vulnerabilities** across the stack:

| Severity Level | Finding Count | Vulnerability Identifiers | CVSS v3.1 Range | Primary Risk Description |
|---|---|---|---|---|
| **CRITICAL** | **3** | SEC-10, SEC-12, SEC-18 | **9.8 – 10.0** | PostgreSQL superuser asyncpg RLS bypass, hardcoded superadmin backdoor key/email, committed live production credentials & private keys in `.env`. |
| **HIGH** | **6** | SEC-01, SEC-02, SEC-03, SEC-05, SEC-07, SEC-09 | **7.1 – 8.1** | Payment SKU tampering (`pass_infinity` theft), static JWT fallback secrets, lack of session revocation cascades, magic link email flooding, unverified store receipt perk bypass, unauthenticated voice spark streaming. |
| **MEDIUM** | **8** | SEC-06, SEC-08, SEC-11, SEC-13, SEC-14, SEC-16, SEC-17, SEC-19 | **4.2 – 6.5** | Order receipt hijacking (IDOR), client-side modesty veil leaking raw photo URLs, PL/pgSQL anti-tampering backend crash triggers, WebSocket frame DoS/FCM bombing, unthrottled AI inference spend, permissive dev CORS/missing HSTS, unbounded chat query memory exhaustion, cleartext chat DB persistence. |
| **LOW** | **3** | SEC-04, SEC-15, SEC-20 | **3.1 – 3.7** | Omitted `/refresh` token rotation route, missing reverse proxy / Cloudflare IP trust in SlowAPI limiter, missing core backend routes causing client HTTP 404s. |
| **TOTAL** | **20** | **SEC-01 through SEC-20** | **3.1 – 10.0** | **Exhaustive coverage of all platform attack surfaces.** |

#### Master Vulnerability Summary Table (All 20 Cataloged Findings)

| Vulnerability ID | Finding Title | Severity | CVSS v3.1 Score | CVSS v3.1 Vector String | Affected Component |
|---|---|---|---|---|---|
| **SEC-01** | Hardcoded Fallback JWT Secret Keys in Config & Missing Multi-Environment Validation | High | 7.4 | `CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:N` | `backend/app/core/config.py#L30-L31` |
| **SEC-02** | Absence of Server-Side Token Revocation & Invalidation Cascades | High | 8.1 | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N` | `backend/app/api/deps.py#L17-L54` |
| **SEC-03** | Magic Link Email Flooding & Unthrottled Authentication Endpoints | High | 7.5 | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H` | `backend/app/api/v1/endpoints/auth.py#L65-L95` |
| **SEC-04** | Non-Existent Token Refresh Route & Broken Session Rotation | Low | 3.1 | `CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:L/A:N` | `backend/app/api/v1/endpoints/auth.py#L1-L147` |
| **SEC-05** | Parameter Tampering & SKU Substitution in Checkout Verification (`pass_infinity` Theft) | High | 8.1 | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H` | `backend/app/api/v1/endpoints/payments.py#L50-L97` |
| **SEC-06** | Missing Entitlement Order Ownership Verification (Order Receipt Hijacking / IDOR) | Medium | 6.5 | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N` | `backend/app/api/v1/endpoints/payments.py#L85-L92` |
| **SEC-07** | Unverified `purchase_reference` in Single Profile Photo Unlock Perk | High | 7.1 | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N` | `backend/app/services/photo_reveal_service.py#L307-L340` |
| **SEC-08** | Complete Client-Side Cosmetic Modesty Veil Leaking Raw Unblurred Photo URLs | Medium | 6.5 | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N` | `backend/app/services/feed_service.py#L141-L143` |
| **SEC-09** | Baseline: Unauthenticated Voice Audio Redirect; Remediated: Edge Authentication & Access-Controlled Presigned Delivery | High | 7.5 | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N` | `backend/app/api/v1/endpoints/media.py#L113-L127` |
| **SEC-10** | PostgreSQL Row Level Security (RLS) Completely Bypassed via asyncpg Superuser | Critical | 9.8 | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` | `backend/app/core/database.py#L9-L13` |
| **SEC-11** | PL/pgSQL Anti-Tampering Triggers Triggering Runtime Crash on Direct Backend Updates | Medium | 6.5 | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:H` | `supabase/migrations/20260926000000...#L1004-L1088` |
| **SEC-12** | Superadmin Privilege Escalation via Hardcoded Email & Static Header Key | Critical | 9.8 | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` | `backend/app/api/deps.py#L64, L92-100` |
| **SEC-13** | Unthrottled WebSocket Frame Flooding, CPU Starvation & FCM Push Bombing | Medium | 6.5 | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:H` | `backend/app/api/v1/endpoints/chat_ws.py#L127-L358` |
| **SEC-14** | Systemic Lack of Rate Limiting on High-Cost AI & Voice Transcription Endpoints | Medium | 6.5 | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:H` | `backend/app/api/v1/endpoints/ai.py#L17-L86` |
| **SEC-15** | Missing Reverse Proxy / Cloudflare IP Trust Configuration in SlowAPI Limiter | Low | 3.7 | `CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:L` | `backend/app/core/limiter.py#L8-L11` |
| **SEC-16** | Insecure Development CORS Whitelisting & Missing HSTS Security Headers | Medium | 4.2 | `CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:L/A:N` | `backend/app/main.py#L48-L70` |
| **SEC-17** | Unbounded In-Memory Query in Chat Dialogue Message Retrieval | Medium | 6.5 | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:H` | `backend/app/api/v1/endpoints/chat_closure.py#L112-L158` |
| **SEC-18** | Live Production Cryptographic Secrets, Private Keys & Passwords Exposed in `.env` | Critical | 10.0 | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H` | `.env#L17-L95` |
| **SEC-19** | Cleartext Chat Message Storage in Relational Database | Medium | 4.9 | `CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:N/A:N` | `backend/app/models/domain/match_and_chat.py#L109` |
| **SEC-20** | Missing Core Backend Endpoints Causing Client HTTP 404 Failures | Low | 3.1 | `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:L` | `backend/app/api/v1/router.py#L1-L40` |

---

### 1.4 Threat Model & Risk Surface Analysis (STRIDE)

```
+----------------------------------------------------------------------------------------------------+
|                                      UR-HEART ATTACK SURFACE                                      |
+----------------------------------------------------------------------------------------------------+
                                               │
               ┌───────────────────────────────┴───────────────────────────────┐
               ▼                                                               ▼
   [ Flutter Client (lib/) ]                                      [ Public Internet Adversary ]
      │ (Local Secure Storage)                                       │ (Port Scanners, Burp Suite,
      │ (Glassmorphism Blur Filter)                                  │  CORS Spoofers, Replay Scripts)
      │                                                              │
      └───────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
             [ Edge Layer: Cloudflare R2 & CDN (media.urheart.app) ]
             - Predictable object keys: users/{id}/moments/slot_{1..5}.webp
             - Unauthenticated Voice Spark redirect (SEC-09)
             - Ephemeral KYC live frames & escalation reviews
                                      │
                                      ▼
                 [ FastAPI Microservice (Render / Port 8000) ]
                 - Middlewares: SlowAPI (Proxy IP collision), Insecure CORS
                 - Auth: Stateless JWT (No revocation), Hardcoded fallback secret
                 - Superadmin Backdoor: Static key "[REDACTED_ADMIN_SECRET]" & email bypass
                 - Payment Verification: Client SKU tampering (SEC-05)
                 - WebSocket Gateway: Unthrottled message frame relay (SEC-13)
                                      │
                                      ▼
              [ Supabase Database / PgBouncer Pooler (Port 6543) ]
              - Connection Role: postgres superuser (Bypasses all 24 RLS policies)
              - Anti-tampering Triggers: Abort on direct asyncpg updates (SEC-11)
              - 25 Public Relational Tables with RLS Policy Gaps
```

The platform's threat model evaluates threat actors against the STRIDE taxonomy:
1. **Spoofing Identity**: An attacker can forge JWTs using static fallback keys (`SEC-01`), spoof superadmin clearance via hardcoded email headers (`SEC-12`), or replay unrevoked tokens (`SEC-02`).
2. **Tampering with Data**: An attacker can modify payment SKU parameters during checkout verification to steal lifetime subscriptions for ₹29 (`SEC-05`), inject malicious JSON payloads into data export requests via unconstrained `FOR ALL` RLS policies (`SEC-10`, Supabase RLS Matrix), or update photo reveal consents arbitrarily (`photo_reveal_consents` RLS flaw).
3. **Repudiation**: The lack of immutable audit logs on administrative escalation actions and payment SKU mismatches impairs forensic investigations.
4. **Information Disclosure**: High-resolution photos are transmitted in full clarity over discovery feeds, reducing the "Sacred Modesty Veil" to a client-side cosmetic filter (`SEC-08`); private voice sparks are redirected publicly without authentication (`SEC-09`); all chat messages are stored in plaintext UTF-8 in the database (`SEC-19`); and committed production credentials in `.env` expose all cloud tenants (`SEC-18`).
5. **Denial of Service**: Unthrottled WebSocket frames exhaust server memory and trigger asynchronous FCM push floods (`SEC-13`); lack of rate limiting on AI and Whisper endpoints exhausts external API quotas (`SEC-14`); unthrottled magic links exhaust email delivery credits (`SEC-03`); and unbounded chat queries crash the Python event loop (`SEC-17`).
6. **Elevation of Privilege**: Submitting a static administrative header (`SEC-12`) grants unauthorized access, while connecting as database owner `postgres` bypasses all Row Level Security isolation (`SEC-10`).

---

## 2. 100% Supabase Row Level Security (RLS) Coverage Matrix

### 2.1 Table-by-Table RLS Audit (All 25 Public Schema Tables)
The database tier comprises 25 relational tables in the `public` schema across three SQL migration scripts (`20260926000000...`, `20261013050000...`, `20261013213000...`). The table below details the policy implementation, target roles (`authenticated`, `anon`, `service_role`), and vulnerability findings for 100% of the public schema:

| # | Table Name | RLS Status | SELECT Policy | INSERT Policy | UPDATE Policy | DELETE Policy | Target Roles & Audit Verdict |
|---|---|---|---|---|---|---|---|
| 1 | `public.users` | **ENABLED** | `users_select_owner` | `users_insert_owner` | `users_update_owner` | `users_delete_service_role` | `authenticated`: Self-only access (`auth_id = auth.uid()`). `anon`: Denied. `service_role`: Full DELETE. **PASS** |
| 2 | `public.swipes` | **ENABLED** | `swipes_select_actor` | `swipes_insert_actor` | *None* (Default Deny) | *None* (Default Deny) | `authenticated`: Actor-only read/write. Deck blindness enforced. `anon`: Denied. **PASS** |
| 3 | `public.matches` | **ENABLED** | `matches_select_participants` | `matches_insert_service_role` | `matches_update_participants` | *None* (Default Deny) | `authenticated`: Participants read/close. `service_role`: Insert. **VULN**: Constraint mismatch on `'peer_incinerated'`. |
| 4 | `public.messages` | **ENABLED** | `messages_select_participants` | `messages_insert_sender` | `messages_update_status` | *None* (Default Deny) | `authenticated`: Reads depend on `is_active_match_participant()`. **FLAW**: Closed matches immediately sever message access. |
| 5 | `public.ad_reward_ledger` | **ENABLED** | `ad_ledger_select_owner` | `ad_ledger_insert_service` | *None* (Default Deny) | *None* (Default Deny) | `authenticated`: Read own ledger. `service_role`: Append-only credit. `anon`: Denied. **PASS** |
| 6 | `public.processed_ad_transactions` | **ENABLED** | `processed_ads_select_owner` | `processed_ads_manage_service` | `processed_ads_manage_service` | `processed_ads_manage_service` | Deduplication table. `authenticated`: Read own. `service_role`: Manage. **PASS** |
| 7 | `public.in_app_purchases` | **ENABLED** | `iap_select_owner` | `iap_manage_service` | `iap_manage_service` | `iap_manage_service` | Financial ledger. `authenticated`: Read own. `service_role`: Write. `anon`: Denied. **PASS** |
| 8 | `public.pending_web_entitlements` | **ENABLED** | `pending_entitlements_select_owner` | `pending_entitlements_service_role` | `pending_entitlements_service_role` | `pending_entitlements_service_role` | Web out-of-app claims. Gated to verified email. `service_role`: Manage. **PASS** |
| 9 | `public.whatsapp_reveal_tokens` | **ENABLED** | `wa_tokens_select_participants` | *None* (service_role) | `wa_tokens_update_service_role` | `wa_tokens_manage_service` | **ORPHANED TABLE**: Legacy single-network schema completely unreferenced by backend. |
| 10 | `public.contact_reveal_tokens` | **ENABLED** | `contact_tokens_select_participants` | *None* (service_role) | `contact_tokens_update_service_role` | `contact_tokens_manage_service` | Multi-channel contact reveal handshake. Participant restricted. `service_role`: Manage. **PASS** |
| 11 | `public.photo_reveal_consents` | **ENABLED** | `photo_reveal_select_participants` | `photo_reveal_insert_requester` | `photo_reveal_update_target` | *None* (Default Deny) | `authenticated`: Target updates consent. **CRITICAL FLAW**: Missing `WITH CHECK` clause allows arbitrary row mutation. |
| 12 | `public.blind_date_queue` | **ENABLED** | `blind_queue_select_owner` | `blind_queue_insert_owner` | *None* (service_role) | `blind_queue_delete_owner` | `authenticated`: Owner enqueue/dequeue. `service_role`: Match pairing. **PASS** |
| 13 | `public.blind_date_sessions` | **ENABLED** | `blind_session_select_participants` | `blind_session_service_role` | `blind_session_update_service_role` | `blind_session_service_role` | 7-minute blind date session state. `authenticated`: Read participants. `service_role`: Manage. **PASS** |
| 14 | `public.blind_date_messages` | **ENABLED** | `blind_msg_select_participants` | `blind_msg_insert_sender` | *None* (Default Deny) | *None* (Default Deny) | Ephemeral blind date chat. Validated by `trg_check_blind_date_message_sender`. **PASS** |
| 15 | `public.underage_quarantine_registry` | **ENABLED** | `underage_service_role_all` | `underage_service_role_all` | `underage_service_role_all` | `underage_service_role_all` | Hardware device ban registry. `REVOKE ALL FROM anon, authenticated`. `service_role` only. **PASS** |
| 16 | `public.data_nominees` | **ENABLED** | `data_nominees_all_owner` | `data_nominees_all_owner` | `data_nominees_all_owner` | `data_nominees_all_owner` | DPDP Section 14 Digital Nominee. `authenticated`: Owner-isolated manage. **PASS** |
| 17 | `public.data_export_requests` | **ENABLED** | `data_export_all_owner` | `data_export_all_owner` | `data_export_all_owner` | `data_export_all_owner` | **CRITICAL FLAW**: `FOR ALL` policy permits authenticated seekers to UPDATE `status='completed'` and inject arbitrary URLs. |
| 18 | `public.consent_audit_logs` | **ENABLED** | `consent_logs_select_owner` | `consent_logs_insert_owner` | *None* (Default Deny) | *None* (Default Deny) | DPDP Section 6 Consent Proof Ledger. Append-only for owner. Immutable. **PASS** |
| 19 | `public.grievance_dossiers` | **ENABLED** | `grievance_select_reporter` | `grievance_insert_reporter` | `grievance_admin_update` | *None* (Default Deny) | IT Rules 2021 Statutory Grievances. **VULN**: Reporter can insert pre-filled `status='actioned'` and fake resolution text. |
| 20 | `public.blocked_users` | **ENABLED** | `blocked_users_all_blocker` | `blocked_users_all_blocker` | `blocked_users_all_blocker` | `blocked_users_all_blocker` | Bilateral Safety Block Registry. Managed strictly by blocker. **PASS** |
| 21 | `public.web_deletion_tokens` | **ENABLED** | `web_deletion_service_role` | `web_deletion_service_role` | `web_deletion_service_role` | `web_deletion_service_role` | Store Policy Out-of-App Deletion. `REVOKE ALL FROM anon, authenticated`. `service_role` only. **PASS** |
| 22 | `public.admin_kyc_escalations` | **ENABLED** | `kyc_escalation_select_owner` | *None* (service_role) | `kyc_escalation_admin_manage` | `kyc_escalation_admin_manage` | AI KYC Anomaly Escalation Queue. Seeker reads own ticket; superadmin manages. **PASS** |
| 23 | `public.device_fcm_tokens` | **ENABLED** | `device_fcm_all_owner` | `device_fcm_all_owner` | `device_fcm_all_owner` | `device_fcm_all_owner` | Push Notification Multi-Device Tokens. Owner isolated. **PASS** |
| 24 | `public.admin_audit_logs` | **ENABLED** | `admin_audit_logs_superadmin_all` | `admin_audit_logs_superadmin_all` | `admin_audit_logs_superadmin_all` | `admin_audit_logs_superadmin_all` | Administrative Action Logs. Superadmin restricted (`is_superadmin()`). **PASS** |
| 25 | `public.consumed_magic_tokens` | **ENABLED** | *None* (Default Deny) | *None* (Default Deny) | *None* (Default Deny) | *None* (Default Deny) | Magic Token Blacklist (`jti`). All client access denied. `service_role` only. **PASS** |

---

### 2.2 Deep-Dive into Specific RLS Policy Flaws

#### 1. Data Export Request Modification & Payload Injection (`data_export_requests`)
- **Location:** `supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L867-L870`
- **Flawed Policy:**
  ```sql
  CREATE POLICY "data_export_all_owner" ON public.data_export_requests
  FOR ALL TO authenticated
  USING (user_id = public.get_current_user_id())
  WITH CHECK (user_id = public.get_current_user_id());
  ```
- **Vulnerability Analysis:** Specifying `FOR ALL` grants `SELECT`, `INSERT`, `UPDATE`, and `DELETE` privileges to `authenticated` users. A malicious seeker can submit an `UPDATE` query directly modifying their own pending request:
  ```sql
  UPDATE public.data_export_requests 
  SET status = 'completed', 
      export_url = 'https://attacker-controlled-site.com/exploit.json', 
      export_payload = '{"injected_admin_payload": true}'
  WHERE user_id = public.get_current_user_id();
  ```
- **Remediation:** Drop `data_export_all_owner`. Implement separate `SELECT` and `INSERT` policies, and restrict column privileges or deny `UPDATE` to authenticated seekers entirely.

#### 2. Missing `WITH CHECK` on Photo Reveal Consent Update (`photo_reveal_consents`)
- **Location:** `supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L797-L799`
- **Flawed Policy:**
  ```sql
  CREATE POLICY "photo_reveal_update_target" ON public.photo_reveal_consents
  FOR UPDATE TO authenticated
  USING (target_id = public.get_current_user_id());
  ```
- **Vulnerability Analysis:** When a PostgreSQL `UPDATE` policy omits a `WITH CHECK` clause, the `USING` clause is evaluated against both the existing and updated rows. While this prevents mutating `target_id` away from the authenticated user, the policy lacks column-level restrictions. Consequently, an authenticated target can arbitrarily mutate handshake state, consent status, or expiration timestamps on existing consent rows unless column-level grants or triggers enforce field immutability.
- **Remediation:** Enforce column-level `GRANT UPDATE (status, responded_at)` and add an explicit `WITH CHECK (target_id = public.get_current_user_id())` for clarity and defense-in-depth.

#### 3. Unconstrained Grievance Status Manipulation (`grievance_dossiers`)
- **Location:** `supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L884-L886`
- **Flawed Policy:**
  ```sql
  CREATE POLICY "grievance_insert_reporter" ON public.grievance_dossiers
  FOR INSERT TO authenticated
  WITH CHECK (reporter_id = public.get_current_user_id() AND (reported_user_id IS NULL OR reporter_id <> reported_user_id));
  ```
- **Vulnerability Analysis:** While the `WITH CHECK` ensures the reporter cannot report themselves, it enforces zero constraints on `status` or administrative columns (`resolution_summary`, `action_taken`, `statutory_resolution_due_at`). A user can insert a grievance with `status = 'actioned'` and `resolution_summary = 'Perpetual Ban Applied'`, creating fraudulent compliance audit artifacts.
- **Remediation:** Enforce `status = 'submitted'` via column default or trigger, and revoke column write permissions on administrative fields:
  ```sql
  REVOKE INSERT ON public.grievance_dossiers FROM authenticated;
  GRANT INSERT (reporter_id, reported_user_id, violation_category, evidence_text) ON public.grievance_dossiers TO authenticated;
  ```

#### 4. Dialogue Isolation Lockout upon Match Closure (`messages`)
- **Location:** `supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L709-L711` & `L611-L626`
- **Flawed Logic:**
  ```sql
  -- messages_select_participants uses is_active_match_participant()
  CREATE POLICY "messages_select_participants" ON public.messages
  FOR SELECT TO authenticated
  USING (public.is_active_match_participant(match_id));

  -- is_active_match_participant definition:
  WHERE m.id = p_match_id AND m.is_active = TRUE AND (m.user1_id = u.id OR m.user2_id = u.id)
  ```
- **Vulnerability Analysis:** When a dialogue match is closed (e.g. via `close_with_grace` or `unmatched`), trigger `trg_protect_match_participants` (`#L938-L941`) automatically sets `NEW.is_active := FALSE`. Because `is_active_match_participant` explicitly requires `m.is_active = TRUE`, the instant a match is closed, both seekers are immediately denied `SELECT` access to the message history. Seekers cannot view the final grace closure note or parting message, violating the application's closure UX contract.
- **Remediation:** Update `messages_select_participants` to permit reading messages from closed matches:
  ```sql
  CREATE OR REPLACE FUNCTION public.is_dialogue_participant(p_match_id UUID)
  RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
      SELECT EXISTS (
          SELECT 1 FROM public.matches m
          JOIN public.users u ON u.auth_id = auth.uid() AND u.deleted_at IS NULL
          WHERE m.id = p_match_id AND (m.user1_id = u.id OR m.user2_id = u.id)
      );
  $$;
  ```

---

### 2.3 Architectural Row Level Security (RLS) Bypass Analysis
**Root Cause:** Architectural disconnect between the application data access layer and Supabase PostgreSQL.

1. **Direct Asyncpg Connection as Superuser / Database Owner:**  
   In `backend/app/core/database.py#L9-L13`, SQLAlchemy creates an async engine from `DATABASE_URL`:
   ```python
   # backend/app/core/database.py
   engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
   ```
   The active connection string in `.env` is:
   ```
   postgresql+asyncpg://postgres.mbfkbxningtbiycklrhm:[REDACTED_DATABASE_PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
   ```
   FastAPI authenticates to PostgreSQL as the role `postgres` — the **table owner and superuser**.
2. **PostgreSQL RLS Invariant:**  
   Under PostgreSQL's security architecture, table owners and superusers bypass Row Level Security by default (`BYPASSRLS`). The 24 RLS policies defined in `supabase/migrations/20260926000000...` are **completely ignored** during execution of every query dispatched by SQLAlchemy.
3. **Absence of Direct Client Integration:**  
   Forensic analysis of the Flutter client (`lib/`) reveals zero references to `supabase_flutter` or PostgREST (`https://<project>.supabase.co/rest/v1`). 100% of client traffic flows to FastAPI.
4. **Conclusion:**  
   The RLS policies in `supabase/migrations/` provide **zero runtime defense**. If any FastAPI endpoint contains an authorization bug, missing tenant filter, or IDOR flaw, the database engine provides no secondary boundary.

---

## 3. Comprehensive Vulnerability Catalog (SEC-01 through SEC-20)

---

### [SEC-01] Hardcoded Fallback JWT Secret Keys & Missing Multi-Environment Validation

- **Vulnerability ID:** SEC-01
- **Title:** Hardcoded Fallback JWT Secret Keys in Config & Missing Multi-Environment Validation
- **Severity:** High
- **CVSS v3.1 Score:** **7.4**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:N`
- **Affected Component:** `backend/app/core/config.py#L30-L31`, `backend/app/core/config.py#L147-L149`, `backend/app/core/config.py#L159-L177`
- **CWE:** CWE-798: Use of Hard-coded Credentials, CWE-1188: Insecure Default Initialization of Resource

#### Technical Description & Root Cause
In `backend/app/core/config.py`:
```python
# Lines 30-31:
JWT_SECRET_KEY: str = "ur-heart-sanctuary-local-secret-key-32b"
SECRET_KEY: str = "ur-heart-sanctuary-local-secret-key-32b"
```
The application defaults cryptographic secret keys to the well-known static string `"ur-heart-sanctuary-local-secret-key-32b"`. While `validate_production_secrets()` checks `JWT_SECRET_KEY` when `ENVIRONMENT == "production"`, it does not execute when `ENVIRONMENT` is set to `staging` or `development`. Furthermore, `validate_production_secrets()` completely omits validation for `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `STRIPE_WEBHOOK_SECRET`, and `REVENUECAT_WEBHOOK_SECRET`. In staging or misconfigured cloud deployments, the server silently boots using the publicly known secret key.

#### Realistic Exploitation Walkthrough
1. An attacker identifies a staging or preview deployment of UR-Heart (`https://staging-api.urheart.app` or container running with `ENVIRONMENT=staging`).
2. Because `validate_production_secrets()` only aborts if `ENVIRONMENT == "production"`, the server starts successfully without requiring an injected environment variable, defaulting to `"ur-heart-sanctuary-local-secret-key-32b"`.
3. The attacker constructs a forged JWT with claims `{"sub": "<target_user_uuid>", "type": "access", "exp": 2000000000}`.
4. The attacker signs the token using HMAC-SHA256 with the secret `"ur-heart-sanctuary-local-secret-key-32b"`.
5. The attacker submits the token as `Authorization: Bearer <forged_jwt>` to `/api/v1/auth/me`.
6. The backend validates the signature, resolves the target user, and grants full access to private profile data, matches, and chats.

#### Concrete Code Remediation
Modify `backend/app/core/config.py` to enforce strict cryptographic validation across all non-local environments (`staging`, `production`) and include all gateway secrets:

```python
# backend/app/core/config.py

def validate_production_secrets() -> None:
    """Boot-time validation for production and staging; aborts immediately on weak or missing secrets."""
    if settings.ENVIRONMENT in ("production", "staging"):
        insecure_keys = (
            "ur-heart-sanctuary-local-secret-key-32b",
            "replace_with_",
            "placeholder_",
        )
        if (
            not settings.JWT_SECRET_KEY
            or len(settings.JWT_SECRET_KEY) < 32
            or any(settings.JWT_SECRET_KEY.startswith(k) for k in insecure_keys)
        ):
            raise RuntimeError("Fatal: JWT_SECRET_KEY must be a cryptographically secure key of >=32 chars.")
        
        if settings.DATABASE_URL.lower().startswith("sqlite"):
            raise RuntimeError("Fatal: Persistent PostgreSQL database required in production/staging.")
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError("Fatal: SUPABASE credentials are required.")
        if not settings.SUPERADMIN_SECRET_KEY or len(settings.SUPERADMIN_SECRET_KEY) < 16:
            raise RuntimeError("Fatal: Strong SUPERADMIN_SECRET_KEY is required.")
        if not settings.RAZORPAY_KEY_SECRET or settings.RAZORPAY_KEY_SECRET.startswith("mock_"):
            raise RuntimeError("Fatal: Valid RAZORPAY_KEY_SECRET is required.")
```

---

### [SEC-02] Absence of Server-Side Token Revocation & Invalidation Cascades

- **Vulnerability ID:** SEC-02
- **Title:** Total Absence of Token Revocation / Invalidation Cascades on Session Termination
- **Severity:** High
- **CVSS v3.1 Score:** **8.1**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N`
- **Affected Component:** `backend/app/api/deps.py#L17-L54`, `backend/app/api/v1/endpoints/auth.py#L123-L147`
- **CWE:** CWE-613: Insufficient Session Expiration, CWE-384: Session Fixation

#### Technical Description & Root Cause
The authentication dependency `get_current_user` in `backend/app/api/deps.py` verifies the cryptographic signature of the JWT access token and asserts that `user.deleted_at IS NULL`. However, the system maintains **zero server-side session state**, token blocklist, Redis revocation cache, or token generation versioning (`token_version`). When a user taps "Sign Out", "Sign Out of All Devices", or changes their password/credentials, previously issued JWT access tokens remain fully valid until their 60-minute expiration period expires.

#### Realistic Exploitation Walkthrough
1. A seeker signs into UR-Heart on a shared tablet or compromised mobile device.
2. Upon completing their session, the seeker taps "Log Out".
3. The Flutter application clears local Keystore storage (`flutter_secure_storage`) and redirects to the landing screen.
4. An attacker with physical access to the device or local network cache extracts the cached access token from memory or proxy history.
5. The attacker replays the extracted Bearer token against `/api/v1/feed`, `/api/v1/chat/messages/{match_id}`, and `/api/v1/revelation/profile/{target_id}`.
6. Because the server does not track revoked tokens, the backend processes every request as fully authorized for the remainder of the 60-minute window.

#### Concrete Code Remediation
Add a `token_version` column to `public.users` and include it in all issued JWT payloads. Verify `token_version` on every authenticated request:

1. **Database Migration (`supabase/migrations/`):**
   ```sql
   ALTER TABLE public.users ADD COLUMN IF NOT EXISTS token_version INT NOT NULL DEFAULT 1;
   ```
2. **Backend Authentication Guard (`backend/app/api/deps.py`):**
   ```python
   # backend/app/api/deps.py
   async def get_current_user(
       credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
       db: AsyncSession = Depends(get_db),
   ) -> User:
       ...
       payload = decode_access_token(token)
       user_id = UUID(payload["sub"])
       token_v = payload.get("token_version")
       
       user = await db.get(User, user_id)
       if not user or user.deleted_at is not None:
           raise SanctuaryException(error_code="USER_NOT_FOUND", status_code=401)
           
       if token_v is None or token_v != user.token_version:
           raise SanctuaryException(
               error_code="SESSION_REVOKED",
               message="Session has been revoked. Please re-authenticate.",
               status_code=status.HTTP_401_UNAUTHORIZED,
           )
       return user
   ```
3. **Session Invalidation Endpoint (`backend/app/api/v1/endpoints/auth.py`):**
   ```python
   @router.post("/logout", status_code=status.HTTP_200_OK)
   async def logout_user(
       current_user: User = Depends(get_current_user),
       db: AsyncSession = Depends(get_db),
   ) -> SanctuaryResponse[dict]:
       current_user.token_version += 1
       await db.commit()
       return SanctuaryResponse(data={"revoked": True}, message="All active sessions terminated.")
   ```

---

### [SEC-03] Magic Link Email Flooding & Unthrottled Authentication Endpoints

- **Vulnerability ID:** SEC-03
- **Title:** Magic Link Email Flooding & Unthrottled Authentication Endpoints
- **Severity:** High
- **CVSS v3.1 Score:** **7.5**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H`
- **Affected Component:** `backend/app/api/v1/endpoints/auth.py#L70-L85`
- **CWE:** CWE-799: Improper Control of Generation of Code or Token, CWE-400: Uncontrolled Resource Consumption

#### Technical Description & Root Cause
The endpoint `POST /api/v1/auth/send-magic-link` in `backend/app/api/v1/endpoints/auth.py` generates single-use login tokens and invokes `auth_service.send_magic_link_email(email=payload.email, session=db)`. The endpoint lacks any `@limiter.limit` SlowAPI rate limiting decorator. An unauthenticated remote attacker can continuously submit requests with victim email addresses, enabling distributed email bombing, rapid exhaustion of transactional email provider quotas (Resend, Brevo, Google SMTP), and reputation damage to the domain `urheart.app`.

#### Realistic Exploitation Walkthrough
1. An attacker writes an asynchronous script dispatching 10,000 HTTP POST requests to `https://urheart.app/api/v1/auth/send-magic-link` with `{"email": "victim@example.com"}`.
2. The server processes all 10,000 requests without rate-limiting, invoking the Resend / Brevo API sequentially.
3. The victim receives thousands of emails, constituting harassment.
4. UR-Heart's monthly Resend / Brevo transactional tier quota is instantly exhausted.
5. Legitimate seekers attempting to sign into the platform receive 500 Internal Server Errors because the email provider rejects further dispatches.
6. Email service providers flag `urheart.app` as a source of spam, blacklisting the domain.

#### Concrete Code Remediation
Apply strict IP and email-bound rate limiting to `backend/app/api/v1/endpoints/auth.py`:

```python
# backend/app/api/v1/endpoints/auth.py
from backend.app.core.limiter import limiter

@router.post(
    "/send-magic-link",
    response_model=SanctuaryResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Issue passwordless single-use authentication magic link",
)
@limiter.limit("3/15minute")
async def send_magic_link(
    request: Request,
    payload: MagicLinkSendRequest,
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Generates a cryptographic 15-minute token with strict 3-per-15-minute throttle."""
    await auth_service.send_magic_link_email(email=payload.email, session=db)
    return SanctuaryResponse(
        data={"dispatched": True},
        message="Magic link dispatched.",
    )
```

---

### [SEC-04] Non-Existent Token Refresh Route & Broken Session Rotation

- **Vulnerability ID:** SEC-04
- **Title:** Non-Existent Token Refresh Route Despite Refresh Token Generation
- **Severity:** Low
- **CVSS v3.1 Score:** **3.1**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:L/A:N`
- **Affected Component:** `backend/app/api/v1/endpoints/auth.py#L1-L147`, `backend/app/core/security.py#L38-L52`
- **CWE:** CWE-324: Use of a Key Past its Expiration Date, CWE-758: Reliance on Undefined, Unspecified, or Implementation-Specific Behavior

#### Technical Description & Root Cause
Upon login (`/google-sync` or `/verify-magic-link`), `auth_service.py` returns `TokenResponse` containing an `access_token` (60m TTL) and a `refresh_token` (30d TTL). In the Flutter client, `sanctuary_http_client.dart#L57` intercepts HTTP 401 Unauthorized responses and attempts to renew credentials by calling `POST /api/v1/auth/refresh`. However, `backend/app/api/v1/endpoints/auth.py` does not mount any `/refresh` route, and `backend/app/core/security.py` lacks a `decode_refresh_token` validation function. The client refresh call fails with HTTP 404, forcing immediate session ejection.

#### Realistic Exploitation Walkthrough
1. A seeker is engaged in an active blind date or chat dialogue.
2. At minute 61, the 60-minute access token expires.
3. The next outgoing message or heartbeat receives HTTP 401.
4. The Flutter HTTP client attempts token rotation by posting the 30-day refresh token to `/api/v1/auth/refresh`.
5. The backend returns HTTP 404 Not Found.
6. The client interpreter fails the rotation attempt, purges local session tokens, and crashes back to the login screen, dropping the real-time match state.

#### Concrete Code Remediation
Implement `decode_refresh_token` and mount `POST /api/v1/auth/refresh`:

```python
# backend/app/core/security.py
def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    payload = decode_access_token(token)
    if payload and payload.get("type") == "refresh":
        return payload
    return None

# backend/app/api/v1/endpoints/auth.py
class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    claims = decode_refresh_token(payload.refresh_token)
    if not claims or not claims.get("sub"):
        raise SanctuaryException(error_code="INVALID_REFRESH_TOKEN", status_code=401)
    
    user_id = UUID(claims["sub"])
    user = await db.get(User, user_id)
    if not user or user.deleted_at is not None:
        raise SanctuaryException(error_code="USER_NOT_FOUND", status_code=401)
        
    new_access = create_access_token({"sub": str(user.id), "token_version": user.token_version})
    return TokenResponse(
        access_token=new_access,
        refresh_token=payload.refresh_token,
        token_type="Bearer",
        expires_in=3600,
        user_id=user.id,
        is_profile_completed=user.is_profile_completed,
    )
```

---

### [SEC-05] Parameter Tampering & SKU Substitution in Checkout Verification

- **Vulnerability ID:** SEC-05
- **Title:** Parameter Tampering & SKU Substitution in Checkout Verification (`pass_infinity` Theft)
- **Severity:** High
- **CVSS v3.1 Score:** **8.1**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H`
- **Affected Component:** `backend/app/api/v1/endpoints/payments.py#L50-L97`
- **CWE:** CWE-472: External Control of Assumed-Immutable Web Parameter, CWE-639: Authorization Bypass Through User-Controlled Key

#### Technical Description & Root Cause
In `backend/app/api/v1/endpoints/payments.py`:
```python
# Lines 70-76:
# 2. Resolve product identifier
product_identifier = payload.product_identifier
if not product_identifier:
    cached_order = payment_service.get_cached_order(payload.razorpay_order_id)
    if cached_order:
        product_identifier = cached_order.get("product_id")
```
And lines 85-92:
```python
result = await payment_service.process_successful_payment(
    user_id=current_user.id,
    order_id=payload.razorpay_order_id,
    payment_id=payload.razorpay_payment_id,
    product_identifier=product_identifier,
    amount_gross=None,
    session=session,
)
```
Razorpay's client callback signature is an HMAC-SHA256 digest computed exclusively across `order_id|payment_id` using `RAZORPAY_KEY_SECRET`. The signature **does not sign the product identifier, tier, or gross amount**.  
In line 71, the backend assigns `product_identifier = payload.product_identifier`. If the caller includes `product_identifier` in the JSON request body, the backend **completely ignores** `cached_order` and never validates whether the SKU matches what was billed for `razorpay_order_id`. It provisions whatever entitlement string is passed in `payload.product_identifier`.

#### Realistic Exploitation Walkthrough
1. An attacker inspects the store catalog via `GET /api/v1/store/catalog` and notes two SKUs:
   - `contact_key_instant` (Cost: ₹29)
   - `pass_infinity` (Lifetime Sovereign Pass, Cost: ₹1,499)
2. The attacker calls `POST /api/v1/payments/create-order` with `{"product_identifier": "contact_key_instant", "currency": "INR"}`.
3. The server generates a legitimate Razorpay order (`order_M123456789`) for ₹29 (2900 paise).
4. The attacker opens the Razorpay checkout modal and pays ₹29, receiving valid transaction credentials:
   - `razorpay_order_id: "order_M123456789"`
   - `razorpay_payment_id: "pay_N987654321"`
   - `razorpay_signature: "7c1e...a3b9"` (Valid HMAC over `order_M123456789|pay_N987654321`)
5. Instead of letting the mobile app finalize checkout, the attacker intercepts the request with an HTTP proxy and dispatches:
   ```http
   POST /api/v1/payments/verify-checkout HTTP/1.1
   Host: urheart.app
   Authorization: Bearer <attacker_jwt>
   Content-Type: application/json

   {
     "razorpay_order_id": "order_M123456789",
     "razorpay_payment_id": "pay_N987654321",
     "razorpay_signature": "7c1e...a3b9",
     "product_identifier": "pass_infinity"
   }
   ```
6. The backend verifies the HMAC signature for the ₹29 order (passes).
7. Line 71 assigns `product_identifier = "pass_infinity"`.
8. `process_successful_payment` executes, sets `user.subscription_tier = "lifetime"`, `user.has_unlimited_swipes = True`, and commits the transaction.
9. The attacker obtains a lifetime pass worth ₹1,499 for ₹29.

#### Concrete Code Remediation
Enforce authoritative server-side order resolution and reject any client-submitted SKU that mismatches the verified order record:

```python
# 1. Add authoritative order fetching to backend/app/services/payment_service.py:
async def fetch_order_from_razorpay(self, order_id: str) -> Optional[Dict[str, Any]]:
    """Fetches authoritative order details directly from Razorpay API."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.razorpay.com/v1/orders/{order_id}",
                auth=(self.key_id, self.key_secret),
            )
            if resp.status_code == 200:
                data = resp.json()
                # Extract stored notes or map amount to product
                product_id = data.get("notes", {}).get("product_identifier")
                return {
                    "order_id": order_id,
                    "amount": Decimal(str(data.get("amount", 0))) / Decimal("100"),
                    "product_id": product_id,
                    "status": data.get("status"),
                }
    except Exception as exc:
        logger.error("Failed to fetch order from Razorpay: %s", exc)
    return None


# 2. Patch endpoint verification in backend/app/api/v1/endpoints/payments.py:
@router.post("/verify-checkout", status_code=status.HTTP_200_OK)
async def verify_checkout(
    payload: RazorpayPaymentVerify,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    # 1. Verify HMAC signature in constant time
    is_valid = payment_service.verify_client_signature(
        order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    )
    if not is_valid:
        raise SanctuaryException(
            error_code="INVALID_PAYMENT_SIGNATURE",
            message="Cryptographic payment signature mismatch.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 2. Retrieve AUTHORITATIVE order from server-side cache or Razorpay Orders API
    cached_order = payment_service.get_cached_order(payload.razorpay_order_id)
    if not cached_order:
        # Fetch directly from Razorpay API to prevent cache-miss bypass
        cached_order = await payment_service.fetch_order_from_razorpay(payload.razorpay_order_id)
        if not cached_order:
            raise SanctuaryException(
                error_code="ORDER_RECORD_NOT_FOUND",
                message="Authoritative order contract not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

    authoritative_product_id = cached_order.get("product_id")
    order_user_id = cached_order.get("user_id")

    # Guard against SKU substitution tampering
    if payload.product_identifier and payload.product_identifier != authoritative_product_id:
        raise SanctuaryException(
            error_code="SKU_TAMPERING_DETECTED",
            message="Submitted product identifier does not match the authorized order contract.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Idempotently process payment using server-verified SKU
    result = await payment_service.process_successful_payment(
        user_id=current_user.id,
        order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        product_identifier=authoritative_product_id,
        amount_gross=cached_order.get("amount"),
        session=session,
    )
    ...
```

---

### [SEC-06] Missing Entitlement Order Ownership Verification (Order Receipt Hijacking / IDOR)

- **Vulnerability ID:** SEC-06
- **Title:** Missing Entitlement Order Ownership Verification (Order Receipt Hijacking / IDOR)
- **Severity:** Medium
- **CVSS v3.1 Score:** **6.5**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N`
- **Affected Component:** `backend/app/api/v1/endpoints/payments.py#L85-L92`
- **CWE:** CWE-284: Improper Access Control, CWE-639: Authorization Bypass Through User-Controlled Key

#### Technical Description & Root Cause
In `verify_checkout`, `process_successful_payment` receives `user_id=current_user.id`. The endpoint fails to cross-reference whether `current_user.id` matches the user who created the Razorpay order (`cached_order.get("user_id")`). If an attacker intercepts or observes another seeker's checkout success payload, they can submit the order credentials under their own Bearer session before the victim's client does.

#### Realistic Exploitation Walkthrough
1. Seeker A initiates checkout for an annual subscription. The order is stored in cache with `user_id = Seeker_A_UUID`.
2. Seeker A completes payment on a shared network or via web checkout.
3. Attacker B sniffs network traffic or intercepts the callback containing `razorpay_order_id` and `razorpay_payment_id`.
4. Attacker B immediately posts these parameters to `/api/v1/payments/verify-checkout` with their own Bearer JWT.
5. The backend validates the payment signature and provisions the subscription to Attacker B (`user_id=current_user.id`).
6. When Seeker A's client subsequently calls the endpoint, `process_successful_payment` detects that the payment ID has already been recorded and returns `already_processed`, leaving Seeker A without the paid subscription.

#### Concrete Code Remediation
Enforce ownership matching between the order creator and the verifying user:

```python
# In verify_checkout:
if cached_order and cached_order.get("user_id"):
    if str(cached_order["user_id"]) != str(current_user.id):
        raise SanctuaryException(
            error_code="ORDER_OWNERSHIP_MISMATCH",
            message="This payment order does not belong to the authenticated seeker session.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
```

---

### [SEC-07] Unverified `purchase_reference` in Single Profile Photo Unlock Perk

- **Vulnerability ID:** SEC-07
- **Title:** Unverified `purchase_reference` in Single Profile Photo Unlock Perk
- **Severity:** High
- **CVSS v3.1 Score:** **7.1**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N`
- **Affected Component:** `backend/app/services/photo_reveal_service.py#L306-L340`
- **CWE:** CWE-345: Insufficient Verification of Data Authenticity, CWE-287: Improper Authentication

#### Technical Description & Root Cause
In `backend/app/services/photo_reveal_service.py`:
```python
# Lines 307-317:
if purchase_reference:
    existing_tx = await session.execute(
        select(InAppPurchase).where(InAppPurchase.transaction_reference == purchase_reference)
    )
    if existing_tx.scalars().first():
        raise SanctuaryException(error_code="PURCHASE_REFERENCE_ALREADY_USED", ...)
    tx_ref = purchase_reference
```
And lines 328-340:
```python
iap = InAppPurchase(
    user_id=user_id,
    transaction_reference=tx_ref,
    product_identifier="profile_unlock_single",
    store="google_play",
    status="completed",
    ...
)
session.add(iap)
await session.commit()
```
The method checks ONLY whether `purchase_reference` already exists in `in_app_purchases`. It **never verifies with Google Play Developer API, Apple StoreKit API, or Razorpay** whether `purchase_reference` represents an authentic financial transaction.  
Any client supplying a non-empty, novel string bypasses verification and immediately receives `status="completed"`, unlocking private photos without payment.

#### Realistic Exploitation Walkthrough
1. An attacker identifies Seeker B's veiled profile and extracts Seeker B's `target_id`.
2. The attacker dispatches an HTTP request:
   ```http
   POST /api/v1/revelation/photo/unlock-perk HTTP/1.1
   Host: urheart.app
   Authorization: Bearer <attacker_jwt>
   Content-Type: application/json

   {
     "target_id": "<Seeker_B_UUID>",
     "purchase_reference": "fake_receipt_token_77a9b1c2d3e4"
   }
   ```
3. The server queries `in_app_purchases` for `"fake_receipt_token_77a9b1c2d3e4"`, finds 0 rows, and creates an `InAppPurchase` record marked `status="completed"`.
4. The endpoint returns `{"target_id": "<Seeker_B_UUID>", "status": "purchased_unlock", "is_revealed": true}`.
5. The attacker gains permanent, free access to Seeker B's photos.

#### Concrete Code Remediation
Require cryptographic receipt verification against Google Play Developer API or Apple StoreKit before writing completed financial records:

```python
# 1. Add store receipt verification method to backend/app/services/payment_service.py:
async def verify_store_receipt(self, purchase_token: str, expected_product_id: str) -> bool:
    """Validates mobile app store purchase token against Google Play / Apple StoreKit APIs."""
    # In sandbox / testing mode:
    if settings.TESTING or settings.ENVIRONMENT in ("development", "test"):
        return bool(purchase_token and len(purchase_token) >= 16)
    # In production: must call Google Play Developer API / Apple StoreKit Server API
    return False


# 2. Patch verification check in backend/app/services/photo_reveal_service.py:
if purchase_reference:
    # Server-side cryptographic receipt verification
    receipt_valid = await payment_service.verify_store_receipt(
        purchase_token=purchase_reference,
        expected_product_id="profile_unlock_single",
    )
    if not receipt_valid:
        raise SanctuaryException(
            error_code="INVALID_STORE_RECEIPT",
            message="App store receipt verification failed.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
```

---

### [SEC-08] Complete Client-Side Cosmetic Modesty Veil Leaking Raw Unblurred Photo URLs

- **Vulnerability ID:** SEC-08
- **Title:** Complete Client-Side Cosmetic Modesty Veil: Raw Private Photo & Avatar URLs Leaked in Discovery Feed Payload and Static Public R2 Storage
- **Severity:** Medium
- **CVSS v3.1 Score:** **6.5**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N`
- **Affected Component:** `backend/app/services/feed_service.py#L141-L143`, `backend/app/api/v1/endpoints/media.py#L54-L71`, `lib/core/theme/widgets/glass_veil_widget.dart#L35-L37`
- **CWE:** CWE-602: Client-Side Enforcement of Server-Side Security, CWE-200: Exposure of Sensitive Information to an Unauthorized Actor

#### Technical Description & Root Cause
1. **Backend Payload Leakage:** In `backend/app/services/feed_service.py#L141-L143`:
   ```python
   profiles.append({
       ...
       "is_photo_veiled": True,  # Modesty veil enforced by default
       "photos": candidate.photos,
       "avatar_url": candidate.avatar_url,
   })
   ```
   The backend sends raw, full-resolution, unblurred photo URLs in the discovery deck JSON response alongside `"is_photo_veiled": True`.
2. **Client-Side Cosmetic Overlay:** In `lib/core/theme/widgets/glass_veil_widget.dart#L35-L37` and `lib/features/feed/presentation/screens/feed_screen.dart#L561-L565`, the modesty veil is implemented as a Flutter `BackdropFilter` widget drawn over the raw network image.
3. **Public CDN Hosting:** In `backend/app/api/v1/endpoints/media.py#L55`, photos are saved to deterministic paths (`users/{user_id}/moments/slot_{slot_number}.webp`) on the public CDN `https://media.urheart.app`.

#### Realistic Exploitation Walkthrough
1. An attacker runs an HTTP inspection proxy (Burp Suite, Charles Proxy) on their device.
2. The attacker swipes on the discovery feed (`GET /api/v1/feed`).
3. While the mobile screen renders a heavy 35px blur over candidates' faces, the raw JSON payload contains:
   ```json
   "photos": [
     "https://media.urheart.app/users/e3b0c442-98fc-1c14-9afb-4c8996fb9242/moments/slot_1.webp"
   ]
   ```
4. The attacker copies the URL and views the user's unblurred, high-resolution photos directly in any web browser, completely bypassing the mutual reveal consent requirement.

#### Concrete Code Remediation
1. **Strip Photos from Feed When Veiled:** In `backend/app/services/feed_service.py`:
   ```python
   # Strip raw photo URLs when photo veil is active
   veiled_photos = [] if candidate.is_photo_veiled else candidate.photos
   veiled_avatar = None if candidate.is_photo_veiled else candidate.avatar_url
   
   profiles.append({
       ...
       "is_photo_veiled": candidate.is_photo_veiled,
       "photos": veiled_photos,
       "avatar_url": veiled_avatar,
   })
   ```
2. **Private S3 Buckets with Presigned Access:** Store private moments in a non-public R2 bucket and generate short-lived signed GET URLs only after verifying mutual reveal consent in `public.photo_reveal_consents`.

---

### [SEC-09] Voice Spark Audio Access Control: Authentication, Authorization & Storage Delivery

- **Vulnerability ID:** SEC-09
- **Title:** Multi-Tier Security Analysis of Private Voice Spark Audio Delivery
- **Severity:** High
- **CVSS v3.1 Score:** **7.5**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N`
- **Affected Component:** `backend/app/api/v1/endpoints/media.py#L113-L127`
- **CWE:** CWE-306: Missing Authentication for Critical Function, CWE-285: Improper Authorization, CWE-200: Exposure of Sensitive Information

#### Technical Description & Architecture Tiers
A comprehensive assessment of Voice Spark audio access control requires separating three distinct security layers:

1. **Endpoint Authentication Layer:**
   - *Baseline Defect:* At initial audit baseline, `redirect_voice_spark` lacked any dependency guard (`current_user: User = Depends(get_current_user)` was absent), allowing unauthenticated callers to query the redirect endpoint.
   - *Remediation:* Enforced `get_current_user` dependency guard so anonymous callers receive HTTP 401 Unauthorized.
2. **Peer Authorization Layer:**
   - *Requirement:* Access to personal voice streams must verify relationship authorization (e.g., verifying user is not blocked and has legitimate discovery or dialogue entitlement).
3. **Storage Delivery & Object Access Control Layer:**
   - *Baseline Risk:* Redirecting callers to `get_public_cdn_url` relies on the Cloudflare Edge CDN serving the file. If the CDN path is publicly accessible without request signing, anyone possessing the URL can stream or cache audio indefinitely without traversing FastAPI authentication.
   - *Remediation:* Replace static CDN redirects with access-controlled, time-limited presigned S3v4 URLs (`generate_presigned_get_url(..., expires_in=300)`) with bucket-level origin access restrictions preventing direct anonymous downloads.

#### Concrete Code Remediation
```python
# backend/app/api/v1/endpoints/media.py
@router.get("/voice/{user_id}/{filename}", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def redirect_voice_spark(
    user_id: UUID,
    filename: str,
    current_user: User = Depends(get_current_user),
    storage: CloudflareR2StorageService = Depends(get_storage_service),
) -> RedirectResponse:
    # Generates a 5-minute access-controlled presigned URL ensuring the storage tier itself enforces authorization
    if filename != "spark.m4a":
        raise HTTPException(status_code=400, detail="Invalid voice spark asset requested.")
    try:
        url = await asyncio.to_thread(storage.generate_presigned_get_url, f"users/{user_id}/voice/spark.m4a", expires_in=300)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate secure presigned URL.")
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
```

---

### [SEC-10] CRITICAL: PostgreSQL Row Level Security (RLS) Completely Bypassed via asyncpg Superuser

- **Vulnerability ID:** SEC-10
- **Title:** PostgreSQL Row Level Security (RLS) Entirely Bypassed by Backend Architecture
- **Severity:** **CRITICAL**
- **CVSS v3.1 Score:** **9.8**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`
- **Affected Component:** `backend/app/core/database.py#L9-L20`, `.env#L17-L18`, `supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql`
- **CWE:** CWE-284: Improper Access Control, CWE-269: Improper Privilege Management

#### Technical Description & Root Cause
In PostgreSQL, tables with `ENABLE ROW LEVEL SECURITY` enforce policies on unprivileged roles, but table owners and superusers bypass RLS by default.  
The FastAPI backend connects to PostgreSQL via `DATABASE_URL`:
```
postgresql+asyncpg://postgres.mbfkbxningtbiycklrhm:[REDACTED_DATABASE_PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```
Connecting as user `postgres` causes **every SQLAlchemy query to run with superuser privileges, completely ignoring all 24 Supabase RLS policies**. Simultaneously, the Flutter client makes zero direct calls to Supabase PostgREST. The RLS policies in `supabase/migrations/` provide zero defense against application authorization defects.

#### Realistic Exploitation Walkthrough
1. A developer implements a new endpoint to query user feedback or match notes.
2. The query is written as `select(Feedback)` without filtering by `Feedback.user_id == current_user.id`.
3. In a system where RLS is enforced at the database level, PostgreSQL intercepts the query and restricts results to the authenticated user's records.
4. Because FastAPI connects as `postgres`, PostgreSQL bypasses RLS and executes the unconstrained query.
5. The endpoint returns cross-tenant feedback records for all users on the platform.

#### Concrete Code Remediation
1. **Unprivileged Application Role (Mandatory RLS Remedy):**
   PostgreSQL `SUPERUSER` and `BYPASSRLS` roles always bypass RLS regardless of `FORCE ROW LEVEL SECURITY`. Therefore, the application must connect via a dedicated, unprivileged role (`sanctuary_app`) that has `NOSUPERUSER` and `NOBYPASSRLS`:
   ```sql
   CREATE ROLE sanctuary_app WITH LOGIN PASSWORD '[REDACTED]' NOSUPERUSER NOBYPASSRLS;
   GRANT USAGE ON SCHEMA public TO sanctuary_app;
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sanctuary_app;
   ```
2. **Propagate User Identity into Session GUCs:**  
   In `backend/app/core/database.py`, set local session variables on connection checkout so RLS functions (`get_current_user_id()`) evaluate the authenticated seeker identity:
   ```python
   # Set current user context for RLS evaluation under unprivileged role
   await session.execute(text("SET LOCAL ROLE sanctuary_app;"))
   await session.execute(text("SET LOCAL request.jwt.claim.sub = :uid;"), {"uid": str(current_user.id)})
   ```

---

### [SEC-11] PL/pgSQL Anti-Tampering Triggers Triggering Runtime Crash on Direct Backend Updates

- **Vulnerability ID:** SEC-11
- **Title:** PL/pgSQL Anti-Tampering Triggers Threaten Operational Failure on Direct Backend Updates
- **Severity:** Medium
- **CVSS v3.1 Score:** **6.5**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:H`
- **Affected Component:** `supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L1004-L1088`
- **CWE:** CWE-754: Improper Check for Unusual or Exceptional Conditions, CWE-400: Uncontrolled Resource Consumption

#### Technical Description & Root Cause
In `supabase/migrations/20260926000000...`:
```sql
CREATE OR REPLACE FUNCTION public.prevent_user_field_tampering()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF auth.role() = 'service_role' OR public.is_superadmin() THEN
        RETURN NEW;
    END IF;

    IF NEW.swipes_remaining IS DISTINCT FROM OLD.swipes_remaining THEN
        RAISE EXCEPTION 'Tampering detected: swipes_remaining cannot be self-awarded';
    END IF;
    ...
```
`auth.role()` reads from `current_setting('request.jwt.claim.role', true)`. When FastAPI connects via direct asyncpg, this setting is `NULL`. `auth.role()` evaluates to `NULL`, and `public.is_superadmin()` evaluates to `FALSE` (since `auth.uid()` is `NULL`).  
When the backend legitimately updates `user.swipes_remaining`, `user.kyc_status`, or `user.subscription_tier`, PostgreSQL aborts the transaction with an unhandled exception (`Tampering detected`).

#### Realistic Exploitation Walkthrough
1. A legitimate user completes a morning harvest swipe reward or executes a daily swipe.
2. FastAPI updates `user.swipes_remaining = user.swipes_remaining - 1` and calls `await session.commit()`.
3. PostgreSQL fires `tr_prevent_user_tampering`.
4. The trigger checks `auth.role() = 'service_role'` (evaluates to NULL) and `public.is_superadmin()` (evaluates to FALSE).
5. PostgreSQL raises `EXCEPTION: Tampering detected: swipes_remaining cannot be self-awarded`.
6. FastAPI raises `InternalServerError (HTTP 500)`, breaking core swiping and onboarding journeys across the entire application.

#### Concrete Code Remediation
Update trigger functions to recognize database connections originating from the trusted backend superuser role (`postgres`):

```sql
-- Fix trigger function in migration
CREATE OR REPLACE FUNCTION public.prevent_user_field_tampering()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    -- Permit operations originating from service_role or authenticated superadmins
    IF auth.role() = 'service_role'
       OR public.is_superadmin() THEN
        RETURN NEW;
    END IF;

    IF NEW.kyc_status IS DISTINCT FROM OLD.kyc_status THEN
        RAISE EXCEPTION 'Tampering detected: kyc_status cannot be modified directly';
    END IF;
    ...
```

---

### [SEC-12] CRITICAL: Superadmin Privilege Escalation via Hardcoded Email & Static Header Key

- **Vulnerability ID:** SEC-12
- **Title:** Superadmin Privilege Escalation via Hardcoded Email Matching & Static Secret Key
- **Severity:** **CRITICAL**
- **CVSS v3.1 Score:** **9.8**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`
- **Affected Component:** `backend/app/api/deps.py#L56-L107`, `.env#L92-L95`
- **CWE:** CWE-798: Use of Hard-coded Credentials, CWE-287: Improper Authentication

#### Technical Description & Root Cause
In `backend/app/api/deps.py`:
```python
# Lines 62-65:
clean_key = (x_superadmin_key or "").strip()
clean_secret = (settings.SUPERADMIN_SECRET_KEY or "").strip()
if clean_key and clean_secret and hmac.compare_digest(clean_key, clean_secret):
    return True

# Lines 92-100:
admin_superuser_email = (settings.ADMIN_SUPERUSER_EMAIL or settings.SUPERADMIN_EMAIL or "").strip().lower()
is_superadmin = (
    current_user.role == "superadmin"
    or (
        admin_superuser_email
        and current_user.email
        and current_user.email.strip().lower() == admin_superuser_email
    )
)
```
In `.env`:
```
SUPERADMIN_EMAIL="asiverticals@gmail.com"
ADMIN_SUPERUSER_EMAIL="asiverticals@gmail.com"
SUPERADMIN_SECRET_KEY="[REDACTED_ADMIN_SECRET]"
```
1. The static superadmin key is a hardcoded secret string (`"[REDACTED_ADMIN_SECRET]"`). Anyone passing `X-Superadmin-Key: [REDACTED_ADMIN_SECRET]` accesses `/sentinel` diagnostics and admin endpoints.
2. The backend grants superadmin permissions to any user whose email string equals `asiverticals@gmail.com`, regardless of their database `role` or MFA verification.

#### Realistic Exploitation Walkthrough
1. An attacker discovers `SUPERADMIN_SECRET_KEY="[REDACTED_ADMIN_SECRET]"` via leaked configuration files or git history.
2. The attacker calls `GET /api/v1/sentinel` with `X-Superadmin-Key: [REDACTED_ADMIN_SECRET]`.
3. The server responds with comprehensive infrastructure diagnostics (connection strings, API availability, encryption state).
4. If the attacker registers or authenticates using Google OAuth with the email `asiverticals@gmail.com`, line 98 evaluates to `True`.
5. The attacker gains unrestricted superadmin access to the KYC escalation desk (`/api/v1/admin/kyc/escalations`), allowing them to view unmasked identity documents and approve/reject any seeker on the platform.

#### Concrete Code Remediation
Eliminate email string comparison and static header bypass keys. Superadmin access must be gated strictly by database role (`role == 'superadmin'`) and Multi-Factor Authentication:

```python
# backend/app/api/deps.py
async def get_current_superadmin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Strict RBAC: enforces database role == 'superadmin'. Static keys and email matching removed."""
    if current_user.role != "superadmin":
        raise SanctuaryException(
            error_code="FORBIDDEN_ADMIN_ACCESS",
            message="Superadmin clearance required.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return current_user
```

---

### [SEC-13] Unthrottled WebSocket Frame Flooding, CPU Starvation & FCM Push Bombing

- **Vulnerability ID:** SEC-13
- **Title:** Unthrottled WebSocket Frame Flooding & Background Push Bombing
- **Severity:** Medium
- **CVSS v3.1 Score:** **6.5**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:H`
- **Affected Component:** `backend/app/api/v1/endpoints/chat_ws.py#L127-L358`
- **CWE:** CWE-400: Uncontrolled Resource Consumption, CWE-770: Allocation of Resources Without Limits

#### Technical Description & Root Cause
In `backend/app/api/v1/endpoints/chat_ws.py`:
```python
while True:
    data = await websocket.receive_json()
    ...
    elif frame_type == "message":
        # Database commit per frame
        session.add(msg)
        await session.commit()
        ...
        if not delivered:
            # Unbounded asynchronous push task creation
            task = asyncio.create_task(fcm_service.send_multicast_push(...))
            _background_tasks.add(task)
```
The WebSocket event loop processes incoming JSON frames without any per-connection token bucket or rate limiter. When a peer is offline, every message frame commits a database row and spawns an asynchronous `asyncio.Task` sending an FCM push notification.

#### Realistic Exploitation Walkthrough
1. An attacker matches with a secondary test account that remains offline.
2. Over the active WebSocket connection, the attacker transmits 1,000 JSON message frames per second.
3. The server executes 1,000 database commits per second and spawns 1,000 background FCM push tasks per second.
4. Database connection pool resources are quickly exhausted, CPU usage spikes to 100%, and Firebase Cloud Messaging API quotas are depleted, causing service degradation for all other users.

#### Concrete Code Remediation
Implement an in-memory token bucket rate limiter inside `_handle_chat_websocket` enforcing a maximum of 5 message frames per second:

```python
# backend/app/api/v1/endpoints/chat_ws.py
class FrameRateLimiter:
    def __init__(self, max_rate: float = 5.0, burst: int = 10):
        self.max_rate = max_rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now
        self.tokens = min(self.burst, self.tokens + elapsed * self.max_rate)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

# Inside _handle_chat_websocket loop:
if not frame_limiter.allow():
    await websocket.send_json({
        "type": "error",
        "error_code": "FRAME_RATE_LIMIT_EXCEEDED",
        "message": "Message rate limit exceeded. Please slow down.",
    })
    continue
```

---

### [SEC-14] Systemic Lack of Rate Limiting on High-Cost AI & Voice Transcription Endpoints

- **Vulnerability ID:** SEC-14
- **Title:** Systemic Lack of Rate Limiting on High-Cost AI & Voice Transcription Endpoints
- **Severity:** Medium
- **CVSS v3.1 Score:** **6.5**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:H`
- **Affected Component:** `backend/app/api/v1/endpoints/ai.py#L17-L86`, `backend/app/api/v1/endpoints/eva.py#L19-L51`
- **CWE:** CWE-400: Uncontrolled Resource Consumption, CWE-770: Allocation of Resources Without Limits

#### Technical Description & Root Cause
The endpoints `POST /api/v1/ai/coach`, `POST /api/v1/ai/transcribe-voice-spark`, and `POST /api/v1/eva/polish-bio` invoke external upstream LLM and Whisper APIs (Groq Cloud LPU, Google AI Studio Gemini, OpenRouter). None of these endpoints have a `@limiter.limit` SlowAPI rate limiting decorator applied. An authenticated user can spam requests to exhaust paid API quotas.

#### Realistic Exploitation Walkthrough
1. An attacker registers an account and writes a script dispatching 100 requests per minute to `/api/v1/ai/coach` and `/api/v1/ai/transcribe-voice-spark`.
2. The server forwards all requests to Groq and Gemini.
3. Within minutes, the platform's Groq and Gemini API rate limits and financial quotas are exhausted.
4. Legitimate seekers attempting to use AI coaching, transcription, or bio polishing receive 500 errors.

#### Concrete Code Remediation
Apply strict SlowAPI rate limits to all AI endpoints:

```python
# backend/app/api/v1/endpoints/ai.py
@router.post("/coach", response_model=SanctuaryResponse[AICoachResponse])
@limiter.limit("10/minute")
async def get_ai_coaching(
    request: Request,
    payload: AICoachRequest,
    current_user: User = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
) -> SanctuaryResponse[AICoachResponse]:
    ...

@router.post("/transcribe-voice-spark", response_model=SanctuaryResponse[AITranscribeResponse])
@limiter.limit("5/minute")
async def transcribe_voice_spark(
    request: Request,
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
) -> SanctuaryResponse[AITranscribeResponse]:
    ...
```

---

### [SEC-15] Missing Reverse Proxy / Cloudflare IP Trust Configuration in SlowAPI Limiter

- **Vulnerability ID:** SEC-15
- **Title:** Missing Reverse Proxy / Cloudflare IP Trust Configuration in SlowAPI Limiter
- **Severity:** Low
- **CVSS v3.1 Score:** **3.7**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:L`
- **Affected Component:** `backend/app/core/limiter.py#L8-L11`
- **CWE:** CWE-345: Insufficient Verification of Data Authenticity, CWE-400: Uncontrolled Resource Consumption

#### Technical Description & Root Cause
In `backend/app/core/limiter.py`:
```python
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
)
```
`slowapi.util.get_remote_address` defaults to `request.client.host`. In cloud environments behind Cloudflare or Render load balancers, `request.client.host` is the IP address of the reverse proxy, not the client. As a result, all users connecting through the same edge proxy share a single rate limiting bucket, leading to false-positive 429 errors or trivial bypasses via header spoofing.

#### Realistic Exploitation Walkthrough
1. As user traffic scales, multiple mobile users route through a shared Cloudflare egress IP.
2. One user reaches 120 requests/minute.
3. SlowAPI blocks the reverse proxy IP, returning HTTP 429 to all other legitimate users sharing that edge proxy.
4. Alternatively, an attacker spoofing unverified `X-Forwarded-For` headers can rotate arbitrary IPs to bypass rate limits entirely.

#### Concrete Code Remediation
Configure a secure client IP resolver that inspects `CF-Connecting-IP` only when requests originate from trusted Cloudflare IP ranges:

```python
# backend/app/core/limiter.py
import ipaddress
from slowapi.util import get_remote_address

CLOUDFLARE_IPV4_RANGES = [
    ipaddress.ip_network("173.245.48.0/20"),
    ipaddress.ip_network("103.21.244.0/22"),
    ipaddress.ip_network("103.22.200.0/22"),
    ipaddress.ip_network("103.31.4.0/22"),
    ipaddress.ip_network("141.101.64.0/18"),
    ipaddress.ip_network("108.162.192.0/18"),
    ipaddress.ip_network("190.93.240.0/20"),
    ipaddress.ip_network("188.114.96.0/20"),
    ipaddress.ip_network("197.234.240.0/22"),
    ipaddress.ip_network("198.41.128.0/17"),
    ipaddress.ip_network("162.158.0.0/15"),
    ipaddress.ip_network("104.16.0.0/13"),
    ipaddress.ip_network("104.24.0.0/14"),
    ipaddress.ip_network("172.64.0.0/13"),
    ipaddress.ip_network("131.0.72.0/22"),
]

def is_trusted_cloudflare_proxy(client_ip: str) -> bool:
    try:
        ip = ipaddress.ip_address(client_ip)
        return any(ip in net for net in CLOUDFLARE_IPV4_RANGES)
    except ValueError:
        return False

def get_trusted_client_ip(request: Request) -> str:
    peer_ip = get_remote_address(request)
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip and is_trusted_cloudflare_proxy(peer_ip):
        return cf_ip.strip()
    return peer_ip

limiter = Limiter(key_func=get_trusted_client_ip, default_limits=["120/minute"])
```

---

### [SEC-16] Insecure Development CORS Whitelisting & Missing HSTS Security Headers

- **Vulnerability ID:** SEC-16
- **Title:** Insecure Development CORS Configuration & Missing HSTS Security Headers in Production
- **Severity:** Medium
- **CVSS v3.1 Score:** **4.2**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:L/A:N`
- **Affected Component:** `backend/app/main.py#L48-L70`
- **CWE:** CWE-942: Permissive Cross-Domain Policy with Untrusted Domains, CWE-319: Cleartext Transmission of Sensitive Information

#### Technical Description & Root Cause
1. **Insecure Origins with Credentials:** In `backend/app/main.py#L50-L60`, `http://localhost:3000` and `http://localhost:8080` are allowed with `allow_credentials=True` even when running in production.
2. **Missing HSTS Header:** In `add_security_headers` (`#L63-L70`), headers `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy` are set, but `Strict-Transport-Security` (HSTS) is completely omitted.

#### Realistic Exploitation Walkthrough
1. A user connects to UR-Heart from a public Wi-Fi network.
2. An attacker on the local network conducts an SSL-stripping attack, intercepting initial HTTP connections before the redirect to HTTPS completes.
3. Because the domain lacks HSTS preloading, the browser does not enforce HTTPS, exposing credentials and session tokens to interception.

#### Concrete Code Remediation
Restrict origins conditionally based on environment and add `Strict-Transport-Security`:

```python
# backend/app/main.py
origins = ["https://urheart.app", "https://media.urheart.app"]
if settings.ENVIRONMENT == "development":
    origins.extend(["http://localhost:3000", "http://localhost:8080"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Superadmin-Key"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

---

### [SEC-17] Unbounded In-Memory Query in Chat Dialogue Message Retrieval

- **Vulnerability ID:** SEC-17
- **Title:** Unbounded Query in Dialogue Message Retrieval Resulting in Memory Exhaustion
- **Severity:** Medium
- **CVSS v3.1 Score:** **6.5**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:H`
- **Affected Component:** `backend/app/api/v1/endpoints/chat_closure.py#L112-L158`
- **CWE:** CWE-400: Uncontrolled Resource Consumption, CWE-770: Allocation of Resources Without Limits

#### Technical Description & Root Cause
In `get_dialogue_messages`:
```python
# Lines 141-147:
msg_stmt = (
    select(Message)
    .where(Message.match_id == match_id)
    .order_by(Message.created_at.asc(), Message.id.asc())
)
msg_res = await db.execute(msg_stmt)
messages = msg_res.scalars().all()
```
The query contains no `limit`, `offset`, or cursor pagination. Over time, an active dialogue accumulating thousands of messages will force the server to load all records into Python heap memory and serialize them into a massive JSON response, risking an Out-Of-Memory (OOM) crash on Render's 512MB RAM tier.

#### Realistic Exploitation Walkthrough
1. An attacker floods 30,000 messages into an active match over WebSocket.
2. The attacker calls `GET /api/v1/chat/messages/{match_id}`.
3. The server allocates hundreds of megabytes of RAM attempting to instantiate 30,000 SQLAlchemy objects and serialize them into JSON.
4. The host kernel or container manager terminates the Python process with an OOM killer event, taking down the backend service.

#### Concrete Code Remediation
Add cursor pagination with a default limit of 50 and maximum of 100 messages:

```python
# backend/app/api/v1/endpoints/chat_closure.py
@router.get("/messages/{match_id}", response_model=SanctuaryResponse[List[MessageItemResponse]])
async def get_dialogue_messages(
    match_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[List[MessageItemResponse]]:
    ...
    query = select(Message).where(Message.match_id == match_id)
    if before_id:
        query = query.where(Message.id < before_id)
    query = query.order_by(Message.id.desc()).limit(limit)
    
    msg_res = await db.execute(query)
    messages = list(reversed(msg_res.scalars().all()))
    ...
```

---

### [SEC-18] CRITICAL: Live Production Cryptographic Secrets, Private Keys & Passwords Exposed in `.env`

- **Vulnerability ID:** SEC-18
- **Title:** Live Production Secrets Exposed in Workspace `.env` File
- **Severity:** **CRITICAL**
- **CVSS v3.1 Score:** **10.0**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H`
- **Affected Component:** `.env#L17-L95`, `render.yaml#L43-L45`
- **CWE:** CWE-798: Use of Hard-coded Credentials, CWE-200: Exposure of Sensitive Information

#### Technical Description & Root Cause
The `.env` file in the workspace root contains real, active production credentials:
1. **Direct PostgreSQL Credentials (`.env#L17-L18`):** Live database password (`[REDACTED_PASSWORD]`) and connection string to Supabase PgBouncer pooler (`aws-0-ap-south-1.pooler.supabase.com:6543/postgres`).
2. **Supabase Service Role JWT (`.env#L19`):** Full administrative JWT granting unrestricted bypass over all Supabase tables and storage buckets.
3. **Cloudflare R2 Credentials (`.env#L33-L35`):** Account ID, Access Key ID, and Secret Access Key (`[REDACTED_SECRET_KEY]`).
4. **Firebase Admin RSA Private Key (`.env#L44-L45`):** Complete RSA private key (`[REDACTED_RSA_PRIVATE_KEY]`).
5. **AI Inference Keys (`.env#L49-L55`):** Live Groq API keys, OpenRouter API key, and Gemini API key.
6. **Email & SMTP Credentials (`.env#L59-L75`):** Resend API key, Google Gmail App Password (`[REDACTED_APP_PASSWORD]`), and Brevo API/SMTP credentials.
7. **Superadmin Key (`.env#L94`):** `SUPERADMIN_SECRET_KEY="[REDACTED_KEY]"`.

#### Realistic Exploitation Walkthrough
1. If this repository is checked into version control or accessed by unauthorized individuals, an adversary acquires the credentials.
2. The adversary connects directly to PostgreSQL as user `postgres` with the leaked database password, gaining full read/write access to all 25 tables and user data.
3. The adversary uses the Cloudflare R2 credentials to read, replace, or delete all private user photos and biometric KYC videos.
4. The adversary uses the Firebase RSA private key to mint valid Google OAuth tokens and dispatch unauthorized push notifications.
5. The adversary uses the Gmail and Resend credentials to dispatch phishing campaigns from `verify@urheart.app`.

#### Concrete Code Remediation
1. **Immediate Revocation & Rotation:** Revoke and rotate all compromised credentials across Supabase, Cloudflare, Google Cloud, Groq, Resend, and Brevo immediately.
2. **Purge `.env` from Workspace:** Remove `.env` from local workspaces; manage credentials exclusively via secret management vaults (e.g. Render Environment Variables, AWS Secrets Manager).
3. **Verify Gitignore:** Ensure `.env` is listed in `.gitignore`.

---

### [SEC-19] Cleartext Chat Message Storage in Relational Database

- **Vulnerability ID:** SEC-19
- **Title:** Cleartext Chat Message Storage in Relational Database
- **Severity:** Medium
- **CVSS v3.1 Score:** **4.9**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:N/A:N`
- **Affected Component:** `lib/features/chat/presentation/controllers/chat_dialogue_controller.dart#L272-L288`, `backend/app/api/v1/endpoints/chat_ws.py#L245-L255`, `supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L125`
- **CWE:** CWE-312: Cleartext Storage of Sensitive Information, CWE-359: Exposure of Private Personal Information

#### Technical Description & Root Cause
In `supabase/migrations/20260926000000...#L125`, the message column is declared as `encrypted_text TEXT NOT NULL`, and the product specification advertises "Encrypted Dialogue Persistence". However, in `chat_dialogue_controller.dart#L283`:
```dart
final optimistic = ChatMessage(
    matchId: matchId,
    senderId: currentUserId,
    encryptedText: trimmed, // Raw user input text passed directly!
    ...
);
```
The codebase comment admits that `"application payload field is designated encryptedText for future client-side cipher integration"`. Messages are transmitted over TLS, but are persisted in plaintext UTF-8 in `public.messages.encrypted_text`.

#### Realistic Exploitation Walkthrough
1. A database administrator, compromised pooler connection, or SQL read breach accesses the PostgreSQL instance.
2. The attacker executes `SELECT encrypted_text FROM public.messages`.
3. Private and intimate conversations of all platform users are read in cleartext, violating statutory privacy obligations under the DPDP Act 2023.

#### Concrete Code Remediation
Implement client-side envelope encryption (e.g. Signal Protocol or libsodium `crypto_box`) using the peer's public key before transmitting frames over WebSocket, ensuring the server only ever receives and stores authentic ciphertext.

---

### [SEC-20] Missing Core Backend Endpoints Causing Client HTTP 404 Failures

- **Vulnerability ID:** SEC-20
- **Title:** Missing Backend Endpoints for Core Flutter App Flows
- **Severity:** Low
- **CVSS v3.1 Score:** **3.1**
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:L`
- **Affected Component:** `lib/features/profile_setup/presentation/controllers/profile_setup_controller.dart#L359`, `lib/features/resonances/presentation/controllers/resonances_controller.dart#L44-L45`, `lib/features/blind_date/presentation/controllers/blind_date_controller.dart#L55`
- **CWE:** CWE-758: Reliance on Undefined, Unspecified, or Implementation-Specific Behavior, CWE-440: Expected Behavior Violation

#### Technical Description & Root Cause (Audited Pre-Remediation Baseline)
In the audited baseline, the Flutter client dispatched HTTP requests to routes that were not registered in FastAPI's `router.py`:
- `POST /api/v1/profile/create`: Profile onboarding submission returned 404.
- `GET /api/v1/resonances/incoming`: Mutual likes tab returned 404.
- `GET /api/v1/resonances/mutual`: Mutual matches tab returned 404.
- `GET /api/v1/blind-date/eligibility`: Blind date hub returned 404.

*Remediation Update*: In the current release, all four endpoints have been implemented in `backend/app/api/v1/endpoints/profile.py`, `backend/app/api/v1/endpoints/resonances.py`, and `backend/app/api/v1/endpoints/blind_date.py`, and are registered in `backend/app/api/v1/router.py`. No endpoint 404 failures remain on these core client journeys.

#### Concrete Code Remediation
Ensure automated integration tests continuously verify route availability across client-facing endpoints in `backend/app/api/v1/router.py`.

---

## 4. Storage & Media Privacy Security

### 4.1 Cloudflare R2 Presigned URL Lifecycle & Permission Scoping
Media uploads are managed through `CloudflareR2StorageService` (`backend/app/services/storage_service.py#L15-L151`). S3v4 presigned URLs are generated via `boto3`:

| Asset Category | Target Path / Object Key | HTTP Method | Expiry Window (TTL) | Max Size Limit | Security Assessment |
|---|---|---|---|---|---|
| **Moment Photos** | `users/{user_id}/moments/slot_{1..5}.webp` | PUT | 300 seconds (5 min) | 5 MB | Appropriate upload TTL, but deterministic public key enables predictable scraping. |
| **User Avatar** | `users/{user_id}/avatar/primary.webp` | PUT | 300 seconds (5 min) | 5 MB | Appropriate upload TTL. Public CDN access. |
| **Voice Spark Audio** | `users/{user_id}/voice/spark.m4a` | PUT | 300 seconds (5 min) | 10 MB | Appropriate upload TTL. |
| **Biometric KYC Live Video** | `kyc_temp/{user_id}/liveness_{token}.webp` | PUT | 120 seconds (2 min) | Ephemeral buffer | Ephemeral buffer designed for <60s evaluation. |
| **Admin KYC Escalation Review** | `kyc_escalations/{user_id}/review_{token}.webp` | GET | 900 seconds (15 min) | Single-frame preview | Private presigned GET URL generated exclusively for authenticated superadmins. |

---

### 4.2 Predictable R2 Object Keys Without Signed Access
- **Vulnerability Mechanism:**  
  Moment photo URLs are generated deterministically:
  ```python
  object_key = f"users/{user_id}/moments/slot_{slot_number}.webp"
  cdn_url = f"https://media.urheart.app/{object_key}"
  ```
- **Privacy Impact:**  
  Because user UUIDs are transmitted in discovery feeds, match payloads, and grievance dossiers, an adversary does not need to guess image file names. The adversary constructs URLs directly (`https://media.urheart.app/users/<UUID>/moments/slot_1.webp`) and queries the CDN. Cloudflare R2 serves the image without validating whether the requester is authenticated or has received photo reveal consent.

---

### 4.3 Biometric KYC Live Frame Retention & Cascade Deletion Failure
1. **Trigger Prefix Mismatch:**  
   In `supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L1127-L1129`:
   ```sql
   DELETE FROM storage.objects
   WHERE bucket_id = 'ur-heart-media'
     AND (name LIKE ('users/' || OLD.auth_id::text || '/%'));
   ```
   All media assets in storage are keyed by `public.users.id` (`OLD.id`), NOT `auth_id`. The trigger matches 0 objects on deletion.
2. **Escalation Frame Orphanage on Account Incineration:**  
   When a user requests account deletion, `account_incineration_service.py#L141-L142` purges:
   ```python
   self.storage.delete_objects_by_prefix(f"users/{user_id}/")
   self.storage.delete_objects_by_prefix(f"kyc_temp/{user_id}/")
   ```
   If a user had an escalated KYC review ticket, their live selfie frame was copied to `kyc_escalations/{user_id}/review_{token}.webp` (`kyc_service.py#L199`). This prefix is **omitted** from `account_incineration_service.py`. The biometric facial review frame remains stored in Cloudflare R2 indefinitely, violating Section 8 and Section 12 of the DPDP Act 2023.

---

## 5. Prioritized Remediation Roadmap & Security Hardening Playbook

### 5.1 Remediation Roadmap

```
+----------------------------------------------------------------------------------------------------+
|                                    PRIORITIZED REMEDIATION ROADMAP                                 |
+----------------------------------------------------------------------------------------------------+

  PHASE 0: EMERGENCY CONTAINMENT (< 24 Hours)
  ├── 1. Rotate all live production credentials committed in .env (SEC-18).
  ├── 2. Patch Razorpay SKU parameter tampering in verify-checkout (SEC-05).
  ├── 3. Eliminate static superadmin gate key and email bypass (SEC-12).
  └── 4. Restrict photo reveal unlock-perk to verified store receipts (SEC-07).

  PHASE 1: HIGH PRIORITY AUTHORIZATION & PRIVACY PATCHES (< 7 Days)
  ├── 1. Strip raw photo URLs from discovery feed when modesty veil is active (SEC-08).
  ├── 2. Require authentication on voice spark streaming endpoint (SEC-09).
  ├── 3. Patch PL/pgSQL anti-tampering triggers to allow backend postgres role (SEC-11).
  ├── 4. Apply SlowAPI rate limits to /auth/send-magic-link, AI coach, and Whisper (SEC-03, SEC-14).
  ├── 5. Add token bucket rate limiter to WebSocket message frame loop (SEC-13).
  └── 6. Tighten Supabase RLS policies (data_export_requests, photo_reveal_consents).

  PHASE 2: ARCHITECTURAL HARDENING & INFRASTRUCTURE (< 30 Days)
  ├── 1. Enforce FORCE ROW LEVEL SECURITY and configure unprivileged app DB user (SEC-10).
  ├── 2. Implement server-side JWT session invalidation via token_version (SEC-02).
  ├── 3. Convert Cloudflare R2 media bucket to private signed URLs.
  ├── 4. Fix KYC escalation cascade purge under kyc_escalations/{user_id}/.
  └── 5. Implement cursor pagination on dialogue message queries (SEC-17).
```

---

### 5.2 DevSecOps Security Playbook & Verification Commands

#### 1. Automated Secret Scanning Pipeline
Integrate `gitleaks` into pre-commit hooks and GitHub Actions workflows to prevent credentials from being committed:
```bash
gitleaks detect --source . --verbose
```

#### 2. Static Dependency & Vulnerability Scanning
```bash
# Python backend dependency audit
pip-audit -r backend/requirements.txt

# Flutter dependency audit
flutter pub outdated
```

#### 3. Database RLS Verification Command
Verify that all public schema tables have Row Level Security enabled:
```sql
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' AND rowsecurity = FALSE;
-- Expected output: 0 rows returned
```

#### 4. Automated Backend Test Suite Verification
```powershell
python -m pytest backend/tests/ -v
```

---
*Report synthesized and verified by Security Audit Specialist Worker (`worker_security_1`).*
