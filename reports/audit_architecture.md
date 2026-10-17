# End-to-End System Architecture, Module Connectivity & Contract Re-Audit Report

**Target Platform:** UR-Heart Sanctuary (`lib/`, `backend/`, `supabase/`)  
**Auditor:** Teamwork Architecture Specialist & QA Team (Worker 1)  
**Date:** October 16, 2026  
**Methodology:** Full Static AST Parsing, Dependency Graph Synthesis, Client-Server Schema Verification, Dual-Database Parity Inspection (Supabase PostgreSQL Migrations vs. SQLAlchemy Declarative Models), Test Suite Verification  
**Status:** COMPLETE (100% Empirically Verified)

---

## 1. Executive Summary & Architecture Health Score

### 1.1 Executive Summary
An exhaustive, from-scratch static and dependency audit was performed across all source files in the UR-Heart platform repository: the Flutter mobile client (`lib/`), the FastAPI backend service (`backend/`), and the Supabase PostgreSQL database schemas and Row Level Security (RLS) migrations (`supabase/`).

The UR-Heart application possesses an advanced, emotionally intentional design language (the "Glass Sanctuary" aesthetic), well-structured domain layering, and thoughtful statutory privacy engineering designed around India's Digital Personal Data Protection (DPDP) Act 2023.

However, a rigorous inspection of the codebase reveals **severe architectural fault lines, silent runtime breakages, and database desynchronization** that prevent the platform from operating reliably in production:

1. **Critical Client-Server Contract Breakages (Silent Failures):**
   - **Resonances Admirer Reciprocation:** When a seeker attempts to like back or pass an admirer from the Resonances tab, `lib/features/resonances/presentation/controllers/resonances_controller.dart#L67-L70` dispatches `{'target_id': targetId, 'swipe_type': swipeType}` to `POST /api/v1/feed/swipe`. Because `backend/app/schemas/feed.py#L9-L15` requires `action` and strictly enforces `model_config = ConfigDict(extra="forbid")`, FastAPI rejects every request with `HTTP 422 Unprocessable Entity`. Because the controller swallows errors in an empty `catch (_) { return false; }` block, the swipe fails silently without user feedback, permanently breaking mutual match creation from the Resonances screen.
   - **Profile Editing Dead-End:** In `lib/features/profile/presentation/screens/my_persona_screen.dart#L397`, tapping "Edit Profile & Media" navigates the seeker to `/profile-setup`. When the seeker saves changes, `profile_setup_controller.dart#L359` hits `POST /api/v1/profile/create`. The backend endpoint (`backend/app/api/v1/endpoints/profile.py#L39-L44`) checks `if current_user.is_profile_completed` and throws `HTTP 400 Bad Request` (`PROFILE_ALREADY_COMPLETED`). There is **no `PUT /profile` or `PATCH /profile` endpoint implemented anywhere in the backend**, making it structurally impossible for existing users to update their bio, profession, education, or photos.

2. **Severe Database Schema Desynchronization (PostgreSQL vs. SQLAlchemy):**
   - **`grievance_dossiers` Type & Constraint Crash:** In Supabase migration `20260926000000_phase1_database_foundation_and_rls.sql#L487`, the primary key is `BIGINT GENERATED ALWAYS AS IDENTITY`. In the SQLAlchemy model `backend/app/models/domain/legal.py#L123`, the primary key is defined as `UniversalUUID`. PostgreSQL cannot cast a 128-bit UUID into a 64-bit integer identity, crashing insertions. Furthermore, the migration enforces `CHECK (status IN ('under_review', 'actioned', 'dismissed'))`, while SQLAlchemy defines `status = "acknowledged"` and `backend/app/services/legal_vault_service.py#L146` inserts `"acknowledged"`, immediately violating the check constraint and rolling back the transaction.
   - **`admin_kyc_escalations` Missing NOT-NULL Columns:** PostgreSQL table requires `declared_age INT2 NOT NULL`, `anchor_photo_url TEXT NOT NULL`, `kyc_video_url TEXT NOT NULL`, and `groq_reasoning VARCHAR(255) NOT NULL`. The SQLAlchemy model (`admin_telemetry.py#L22-L42`) uses a UUID primary key (instead of `BIGINT IDENTITY`) and completely omits `declared_age` and `groq_reasoning`, while naming photo columns `selfie_storage_url` and `id_card_storage_url`. Any admin escalation insert fails on Postgres with a NOT NULL constraint violation.
   - **`blind_date_messages` Column Drift:** PostgreSQL defines `ciphertext TEXT NOT NULL` with a UUID PK (`supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L382-L386`). The SQLAlchemy model (`blind_date.py#L122-L138`) defines a `BIGINT` PK and expects column `encrypted_text TEXT`. Querying blind date messages crashes with `column "encrypted_text" does not exist`.
   - **`device_fcm_tokens` Column & PK Divergence:** PostgreSQL defines `id UUID PRIMARY KEY` and column `active BOOLEAN NOT NULL DEFAULT TRUE`. SQLAlchemy defines `id BIGINT PK` and column `is_active BOOLEAN`.
   - **`ad_reward_ledger` Check Constraint Collisions:** Migration `20261015120000_sync_schema_and_fix_incineration.sql#L41-L54` restricts `ad_type` to 11 specific strings. Backend service `backend/app/services/ad_ssv_service.py#L307-L345` writes `'quick_reflection'`, `'deep_resonance'`, `'sacred_bridge_reveal'`, `'morning_harvest_unlock'`, and `'daily_streak_boost'`, none of which exist in the constraint, causing database transaction rollbacks upon rewarded ad completion.
   - **Zombie Domain Model `WhatsappRevealToken`:** Dropped via SQL migration `20261015120000_sync_schema_and_fix_incineration.sql#L116`, but still defined in `backend/app/models/domain/revelation.py#L16-L48`, exported in `__init__.py`, and asserted in tests.

3. **Orphaned High-Value Components & Phantom Navigation Routes:**
   - **`SeekerProfileDetailScreen` (726 lines):** A fully implemented, production-grade profile detail screen complete with 35px progressive modesty blur unmasking, 7-second voice spark player, micro-perk instant unmasking (₹39), and DPDP fuzzed coordinates is completely unreachable from the UI. Neither `feed_screen.dart` nor `resonances_screen.dart` provides an `onTap` route to push this screen.
   - **6 Stub Screens:** Six routes across `lib/` render raw 14–20 line text placeholders (`eva_sanctuary_screen.dart`, `magic_link_screen.dart`, `blind_date_hub_screen.dart`, `blind_date_session_screen.dart`, `ignored_profiles_screen.dart`, `app_info_screen.dart`).
   - **Uninitialized Notification Service:** `lib/core/services/notification_service.dart` defines `notificationServiceProvider`, but it is never read or initialized in `main.dart` or any controller. FCM device registration is never triggered on startup.
   - **Orphaned Controller:** `lib/features/blind_date/presentation/controllers/blind_date_controller.dart` is never watched or referenced by any UI component.
   - **3 Redundant Shims:** Re-export shims exist in `features/rewards/...`, `features/settings/...`, and `features/auth/presentation/providers/...`.

4. **Test Suite Environmental Mirage:**
   - All 181 backend unit/integration tests pass with 100% success (`python -m pytest backend/tests`) because tests execute against in-memory SQLite fixtures (`Base.metadata.create_all(bind=engine)`). SQLite's dynamic type affinity accepts UUID strings in BigInt columns and ignores table check constraints, masking the hard PostgreSQL production crashes.
   - All 71 Flutter widget and unit tests pass (`flutter test`) because tests mock `SanctuaryHttpClient` with synthetic JSON responses, masking the Pydantic schema validation failures.

---

### 1.2 Architectural Health Score

```
┌────────────────────────────────────────────────────────────────────────┐
│                   UR-HEART ARCHITECTURAL HEALTH SCORE                  │
├───────────────────────────────────┬──────────────┬────────┬────────────┤
│ Dimension                         │ Weight (%)   │ Score  │ Weighted   │
├───────────────────────────────────┼──────────────┼────────┼────────────┤
│ 1. Frontend Structural Integrity  │ 25%          │ 74/100 │ 18.50      │
│ 2. Client-Server Contract Harmony │ 30%          │ 62/100 │ 18.60      │
│ 3. Database-Model Synchronization │ 30%          │ 58/100 │ 17.40      │
│ 4. Test Parity & Verification     │ 15%          │ 68/100 │ 10.20      │
├───────────────────────────────────┴──────────────┴────────┼────────────┤
│ OVERALL ARCHITECTURAL HEALTH SCORE                        │ 64.7 / 100 │
│ Grade: C+ (SUB-PRODUCTION / REQUIRES REMEDIATION)         │            │
└───────────────────────────────────────────────────────────┴────────────┘
```

---

## 2. Complete Directory & File Inventory

### 2.1 File Count Summary Across Subsystems

| Subsystem | Root Path | Total Files | Source Files | Test Files | Artifacts / Metadata |
|---|---|---|---|---|---|
| **Flutter Mobile Client** | `lib/` | 65 | 65 Dart files | 17 (in `test/`) | `pubspec.yaml`, `pubspec.lock` |
| **FastAPI Backend** | `backend/` | 326 (118 source) | 106 `.py` + 6 non-`.py` | 21 test files | 208 `__pycache__` artifacts |
| **Supabase PostgreSQL** | `supabase/` | 4 | 4 SQL migration files | 0 | 24 active tables, 54 RLS policies |
| **Combined System** | **Workspace** | **395** | **177 source files** | **38 test files** | **208 byte-compiled** |

---

### 2.2 Flutter Client (`lib/`) Inventory (65 Files)

The mobile client is architected around feature-first organization with Riverpod state management and GoRouter declarative navigation.

```
lib/
├── main.dart                                               # Application entrypoint (ProviderScope initialization)
├── core/                                                   # Core platform infrastructure (16 files)
│   ├── app/
│   │   ├── app_router.dart                                 # GoRouter route declarations & auth/RBAC guards (190 lines)
│   │   └── ur_heart_app.dart                               # MaterialApp configuration & theme bindings (40 lines)
│   ├── billing/
│   │   └── sanctuary_billing_service.dart                  # Store catalog, balance polling & ad reward claim client (38 lines)
│   ├── constants/
│   │   └── app_typography.dart                             # Typography tokens: Playfair Display serif & Inter sans (92 lines)
│   ├── network/
│   │   └── sanctuary_http_client.dart                      # HTTP client with JWT interceptor, auto-refresh & error mapper (176 lines)
│   ├── services/
│   │   ├── device_fingerprint_service.dart                 # SHA-256 hardware device hashing for DPDP age gate (48 lines)
│   │   ├── notification_service.dart                       # FCM channel configuration & push token sync [ORPHANED] (96 lines)
│   │   ├── slumber_service.dart                            # Circadian clock engine & night slumber multiplier (54 lines)
│   │   └── window_security_service.dart                    # Hardware screenshot & window protection (FLAG_SECURE = 8192) (52 lines)
│   ├── storage/
│   │   └── secure_session_storage.dart                     # FlutterSecureStorage wrapper for tokens & auth stream (95 lines)
│   └── theme/
│       ├── glass_performance_controller.dart               # Dynamic low-power glass blur optimizer (68 lines)
│       ├── glass_tokens.dart                               # Glassmorphism tokens: specular borders, fills, and colors (148 lines)
│       ├── theme_controller.dart                           # Riverpod dark/light theme state notifier (46 lines)
│       └── widgets/
│           ├── glass_navigation_shell_bars.dart            # Frosted glass top app bar & floating bottom nav bar (214 lines)
│           ├── glass_veil_widget.dart                      # 35px Gaussian backdrop blur for photo modesty veil (118 lines)
│           └── sanctuary_glass_container.dart              # Core frosted glass container with gradient & specular border (104 lines)
└── features/                                               # Feature modules (48 files across 14 directories)
    ├── admin/presentation/screens/
    │   └── superadmin_kyc_desk_screen.dart                 # Superadmin biometric verification queue (168 lines)
    ├── ai_sanctuary/presentation/screens/
    │   └── eva_sanctuary_screen.dart                       # [EMPTY STUB] 15-line placeholder for AI coach
    ├── auth/presentation/
    │   ├── controllers/auth_controller.dart                # Riverpod StateNotifier managing OTP, magic links, & JWTs (395 lines)
    │   ├── providers/auth_controller.dart                  # [REDUNDANT SHIM] 2-line re-export
    │   ├── screens/
    │   │   ├── age_gate_auth_screen.dart                   # DPDP Act 2023 §9 statutory age gate & OTP flow (320 lines)
    │   │   ├── consent_screen.dart                         # DPDP statutory consent notice & explicit agreement (248 lines)
    │   │   └── magic_link_screen.dart                      # [EMPTY STUB] 17-line placeholder for magic link callback
    │   └── widgets/
    │       └── underage_quarantine_dialog.dart             # Statutory 1-year device quarantine modal for minors (112 lines)
    ├── blind_date/presentation/
    │   ├── controllers/blind_date_controller.dart          # [ORPHANED CONTROLLER] Queue join/leave & MAU check (90 lines)
    │   └── screens/
    │       ├── blind_date_hub_screen.dart                  # [EMPTY STUB] 15-line placeholder
    │       └── blind_date_session_screen.dart              # [EMPTY STUB] 20-line placeholder
    ├── chat/
    │   ├── data/chat_websocket_service.dart                # WebSocket client with heartbeat, reconnect, & ticket auth (148 lines)
    │   ├── domain/models/chat_message.dart                 # Immutable ChatMessage model (48 lines)
    │   └── presentation/
    │       ├── controllers/chat_dialogue_controller.dart   # Chat dialogue state, message sending & closure handling (385 lines)
    │       ├── screens/
    │       │   ├── chats_list_screen.dart                  # Active match list & recent conversation previews (332 lines)
    │       │   └── chat_dialogue_screen.dart               # Real-time dialogue UI with modesty unmasking & closure (485 lines)
    │       └── widgets/pass_with_grace_dialog.dart         # Mutual closure dialog providing respectful parting notes (136 lines)
    ├── feed/
    │   ├── domain/models/discovery_profile.dart            # DiscoveryProfile model with photo veil & fuzzed distance (112 lines)
    │   └── presentation/
    │       ├── controllers/feed_controller.dart            # 10-swipe daily deck controller & swipe action dispatcher (186 lines)
    │       └── screens/
    │           ├── feed_screen.dart                        # 10-swipe discovery deck UI with 35px veil & voice sparks (1056 lines)
    │           └── ignored_profiles_screen.dart            # [EMPTY STUB] 15-line placeholder
    ├── growth/
    │   ├── data/
    │   │   ├── ad_waterfall_service.dart                   # 5-network SSV ad provider mediation service (142 lines)
    │   │   ├── payment_service.dart                        # Razorpay native checkout & payment verification client (134 lines)
    │   │   └── store_catalog_model.dart                    # Store SKU & entitlement catalog definitions (84 lines)
    │   └── presentation/
    │       ├── controllers/growth_hub_controller.dart      # Balances, ad reward claiming & slumber multiplier state (178 lines)
    │       ├── screens/growth_hub_screen.dart              # Currency balances, store catalog & ad watch UI (412 lines)
    │       └── widgets/
    │           ├── morning_harvest_dialog.dart             # Morning slumber reward claim popup (128 lines)
    │           └── streak_gauge_widget.dart                # Circular mindful streak progress indicator (116 lines)
    ├── legal_vault/presentation/
    │   ├── controllers/vault_controller.dart               # Nominee designation, grievance filing & data export state (264 lines)
    │   ├── screens/vault_legal_screen.dart                 # Statutory DPDP legal hub, nominee form & grievance list (495 lines)
    │   └── widgets/account_incineration_dialog.dart        # 48-hour irrevocable account incineration confirmation (168 lines)
    ├── navigation/presentation/
    │   ├── controllers/navigation_provider.dart            # Bottom nav index provider (18 lines)
    │   └── screens/sanctuary_navigation_shell.dart         # Scaffolding holding 4 primary tabs: Feed, Resonances, Chats, Growth (142 lines)
    ├── profile/presentation/
    │   ├── controllers/seeker_profile_controller.dart      # Remote profile loading, reveal request & micro-perk state (204 lines)
    │   └── screens/
    │       ├── my_persona_screen.dart                      # Current user profile viewer, QR code & settings link (529 lines)
    │       └── seeker_profile_detail_screen.dart           # [ORPHANED] 726-line detailed profile viewer with photo carousel
    ├── profile_setup/presentation/
    │   ├── controllers/profile_setup_controller.dart       # Onboarding form state, photo uploads & KYC liveness (450 lines)
    │   ├── screens/profile_setup_screen.dart               # Step-by-step onboarding wizard (580 lines)
    │   └── widgets/
    │       ├── eva_polish_modal.dart                       # AI bio polish assistant modal (112 lines)
    │       ├── kyc_liveness_modal.dart                     # Camera preview for facial liveness challenge (164 lines)
    │       ├── photo_slot_grid.dart                        # 6-slot photo upload grid with reordering (210 lines)
    │       └── voice_spark_recorder_widget.dart            # 7-second audio prompt recorder (185 lines)
    ├── resonances/presentation/
    │   ├── controllers/resonances_controller.dart          # [RUNTIME BROKEN] Incoming likes & mutual matches controller (88 lines)
    │   └── screens/resonances_screen.dart                  # Dual-tab view: Mutual Resonances & Secret Admirers (436 lines)
    ├── rewards/presentation/screens/
    │   └── growth_hub_screen.dart                          # [REDUNDANT SHIM] 3-line re-export to features/growth
    └── settings/presentation/screens/
        ├── app_info_screen.dart                            # [EMPTY STUB] 15-line placeholder
        ├── sanctuary_settings_screen.dart                  # Sound, haptics, privacy & legal settings (340 lines)
        └── superadmin_kyc_desk_screen.dart                 # [REDUNDANT SHIM] 2-line re-export to features/admin
```

---

### 2.3 Backend Service (`backend/`) Inventory (118 Files)

The backend is built with FastAPI, SQLAlchemy 2.0 async ORM, and Pydantic v2 schemas.

```
backend/
├── .env / .env.example                                     # Environment configuration (secrets, DB URL, keys)
├── alembic.ini                                             # Database migration configuration
├── Procfile                                                # Web server process runner: uvicorn app.main:app
├── requirements.txt                                        # Python dependency definitions
├── alembic/
│   ├── env.py                                              # Alembic database connection context
│   ├── script.py.mako                                      # Migration file template
│   └── versions/
│       └── 20261015_0001_add_peer_incinerated_to_closure_status.py # Enum migration
├── app/
│   ├── main.py                                             # FastAPI app instance, CORS, security headers, exception handlers (138 lines)
│   ├── api/
│   │   ├── deps.py                                         # Authentication & database dependencies (get_current_user, get_db)
│   │   └── v1/
│   │       ├── router.py                                   # Central APIRouter mounting all 20 endpoint modules (92 lines)
│   │       └── endpoints/ (22 endpoint files)
│   │           ├── admin_kyc.py                            # Superadmin review of escalated KYC records
│   │           ├── ads.py                                  # Google AdMob SSV verification & reward provisioning
│   │           ├── ai.py                                   # AI wingman chat & audio spark transcription
│   │           ├── auth.py                                 # Passwordless OTP, magic links, Google OAuth & token refresh
│   │           ├── blind_date.py                           # Blind Date eligibility, queueing, session creation
│   │           ├── blocking.py                             # User block list, block action & unblock action
│   │           ├── chat_closure.py                         # Mindful mutual closure ("Pass with Grace") protocol
│   │           ├── chat_ws.py                              # Ticket issuing & WebSocket route (/ws/chat/{match_id})
│   │           ├── eva.py                                  # Eva AI profile bio generator & reflection polish
│   │           ├── feed.py                                 # Discovery feed deck generation & swipe processing
│   │           ├── health.py                               # Uptime sentinel, database probe & diagnostic ping
│   │           ├── incineration.py                         # Statutory account deletion & 48-hour vaporization cascade
│   │           ├── kyc.py                                  # Selfie presigned upload & Groq LLM facial liveness verification
│   │           ├── legal.py                                # Nominee registration, grievance filing & data export
│   │           ├── media.py                                # Cloudflare R2 presigned URLs & voice spark streaming
│   │           ├── notifications.py                        # FCM push token registration & preference updates
│   │           ├── payments.py                             # Razorpay order creation, checkout verification & webhooks
│   │           ├── profile.py                              # Profile onboarding [MISSING PUT/PATCH UPDATE ROUTE]
│   │           ├── resonances.py                           # Incoming admirers list & mutual matches query
│   │           ├── revelation.py                           # Photo reveal request, response, status & instant perk unmasking
│   │           ├── store.py                                # Store catalog items & seeker balance ledger
│   │           └── streak.py                               # Mindful streak status, heartbeat & morning harvest claim
│   ├── core/ (7 files)
│   │   ├── config.py                                       # Pydantic Settings model with production secret validation
│   │   ├── database.py                                     # SQLAlchemy async_sessionmaker & engine setup
│   │   ├── exceptions.py                                   # Custom SanctuaryException hierarchy & error codes
│   │   ├── limiter.py                                      # SlowAPI Redis/memory rate limiter configurations
│   │   ├── security.py                                     # JWT token minting/verification & Fernet contact bridge encryption
│   │   ├── ws_manager.py                                   # In-memory WebSocket connection manager & broadcast relay
│   │   └── ws_ticket_store.py                              # Single-use 60-second WebSocket connection ticket storage
│   ├── models/domain/ (8 files)
│   │   ├── base.py                                         # SQLAlchemy Base, UniversalUUID & BigIntPK type abstractions
│   │   ├── user.py                                         # User model (demographics, quotas, streaks, encrypted bridge)
│   │   ├── match_and_chat.py                               # Swipe, Match, Message, and BlockedUser models
│   │   ├── monetization.py                                 # AdRewardLedger, ProcessedAdTransaction, InAppPurchase models
│   │   ├── revelation.py                                   # ContactRevealToken, PhotoRevealConsent, [ZOMBIE] WhatsappRevealToken
│   │   ├── blind_date.py                                   # BlindDateQueue, BlindDateSession, BlindDateMessage models
│   │   ├── legal.py                                        # GrievanceDossier, DataNominee, DataExportRequest, ConsentAuditLog models
│   │   └── admin_telemetry.py                              # AdminKycEscalation, DeviceFcmToken, AdminAuditLog models
│   ├── schemas/ (16 files)
│   │   ├── base_response.py                                # Unified SanctuaryResponse[T] envelope
│   │   ├── auth.py, profile.py, feed.py, chat.py           # Domain Pydantic request/response schemas
│   │   ├── revelation.py, monetization.py, streak.py       # Feature Pydantic schemas
│   │   ├── legal.py, admin.py, ai.py, eva.py               # Compliance and administration schemas
│   │   └── kyc.py, media.py, notification.py, blind_date.py# Media, notifications, and speed dating schemas
│   └── services/ (16 files)
│       ├── account_incineration_service.py                 # Multi-table cascade account deletion & log scrubbing
│       ├── ad_ssv_service.py                               # AdMob SSV ECDSA signature verification & reward provisioning
│       ├── admin_service.py                                # KYC escalation approval/rejection logic
│       ├── ai_service.py                                   # Groq LLM integration for wingman chat & Whisper audio transcription
│       ├── auth_service.py                                 # Passwordless OTP verification & token lifecycle
│       ├── billing_entitlement_service.py                  # Store perk purchase & quota replenishment
│       ├── email_service.py                                # SMTP / Resend email dispatcher
│       ├── eva_service.py                                  # Groq LLM bio polish engine
│       ├── fcm_service.py                                  # Firebase Cloud Messaging HTTP v1 push notifications
│       ├── feed_service.py                                 # 10-swipe discovery deck generator & geo-fuzzing
│       ├── kyc_service.py                                  # Biometric liveness validation & age verification
│       ├── legal_vault_service.py                          # Grievance registration & DPDP data export packager
│       ├── payment_service.py                              # Razorpay signature verification & webhook processor
│       ├── photo_reveal_service.py                         # Bilateral photo unmasking workflow
│       ├── storage_service.py                              # Cloudflare R2 presigned URL signer & S3 asset manager
│       └── streak_engine.py                                # Mindful streak calculator & morning harvest bonus
└── tests/ (21 test files, 181 passing tests)
```

---

### 2.4 Supabase Database Migrations (`supabase/migrations/`) (4 Files)

| File Name | Date Prefix | Lines | Purpose & Contents |
|---|---|---|---|
| `20260926000000_phase1_database_foundation_and_rls.sql` | 2026-09-26 | 1271 | Core schema definition: 24 tables, 54 Row Level Security (RLS) policies, foreign key cascades, triggers (`update_updated_at_column`, `check_blind_date_message_sender`), and utility security functions (`get_current_user_id()`, `is_superadmin()`). |
| `20261013050000_phase1_retention_and_constraint_alignment.sql` | 2026-10-13 | 15 | Adds retention constraints and aligns check constraints across messaging tables. |
| `20261013213000_phase2_consumed_magic_tokens.sql` | 2026-10-13 | 18 | Creates `public.consumed_magic_tokens` table for single-use cryptographic JTI tracking to prevent magic link replay attacks. |
| `20261015120000_sync_schema_and_fix_incineration.sql` | 2026-10-15 | 156 | Drops legacy `whatsapp_reveal_tokens` table, updates `chk_ad_reward_ledger_ad_type`, alters `matches` to make user IDs nullable for the account incineration "vaporization paradox" fix. |

---

## 3. Full-System End-to-End Dependency Graph (All 8 Journeys)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                             END-TO-END SYSTEM DEPENDENCY ARCHITECTURE                            │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

```
[Flutter UI Layer]             [Network & State]            [FastAPI Backend]            [Database Layer]
                                                            
AgeGateAuthScreen              AuthController               /api/v1/auth/verify-otp      users
ConsentScreen                  SanctuaryHttpClient          /api/v1/auth/refresh         consent_audit_logs
                                                            /api/v1/auth/register-intent consumed_magic_tokens
──────────────────────────────────────────────────────────────────────────────────────────────────────────
ProfileSetupScreen             ProfileSetupController       /api/v1/profile/create [400] users (no PUT route)
MyPersonaScreen                SecureSessionStorage         /api/v1/media/presigned-url  user_photos (embedded)
                                                            /api/v1/eva/polish-bio       
──────────────────────────────────────────────────────────────────────────────────────────────────────────
FeedScreen                     FeedController               /api/v1/feed                 swipes
GlassVeilWidget (35px blur)    DiscoveryProfile             /api/v1/feed/swipe           matches
VoiceSparkButton                                                                         users
──────────────────────────────────────────────────────────────────────────────────────────────────────────
ResonancesScreen               ResonancesController [422]   /api/v1/resonances/incoming  swipes
(Mutual & Admirers)            SanctuaryHttpClient          /api/v1/resonances/mutual    matches
                                                            /api/v1/feed/swipe           
──────────────────────────────────────────────────────────────────────────────────────────────────────────
SeekerProfileDetailScreen      SeekerProfileController      /api/v1/revelation/photo/... photo_reveal_consents
[ORPHANED - No UI Entry]       WindowSecurityService        /api/v1/revelation/profile   users
                                                            /api/v1/revelation/respond*  (*no Flutter caller)
──────────────────────────────────────────────────────────────────────────────────────────────────────────
ChatsListScreen                ChatDialogueController       /api/v1/chat/ws-ticket       matches
ChatDialogueScreen             ChatWebSocketService         /api/v1/chat/messages/{id}   messages
PassWithGraceDialog            SanctuaryGlassContainer      /api/v1/chat/close-with-grace
                                                            WebSocket: /ws/chat/{id}     
──────────────────────────────────────────────────────────────────────────────────────────────────────────
GrowthHubScreen                GrowthHubController          /api/v1/store/catalog        ad_reward_ledger [FAIL]
MorningHarvestDialog           AdWaterfallService           /api/v1/store/balances       processed_ad_tx
StreakGaugeWidget              PaymentService (Razorpay)    /api/v1/ads/claim-reward     in_app_purchases
                               SanctuaryBillingService      /api/v1/payments/create-order
──────────────────────────────────────────────────────────────────────────────────────────────────────────
VaultLegalScreen               VaultController              /api/v1/legal/nominee        data_nominees
AccountIncinerationDialog      SanctuaryHttpClient          /api/v1/legal/grievance[FAIL]grievance_dossiers[FAIL]
SuperadminKycDeskScreen                                     /api/v1/legal/data-export    data_export_requests
                                                            /api/v1/legal/account        admin_kyc_escalations[FAIL]
                                                            /api/v1/admin/kyc/escalations
```

### Detailed Trace of the 8 Core Journeys:

1. **Journey 1: Authentication, Consent & Onboarding**
   - **Frontend UI:** `lib/features/auth/presentation/screens/age_gate_auth_screen.dart` -> `consent_screen.dart` -> `underage_quarantine_dialog.dart`.
   - **State & Networking:** `auth_controller.dart` -> `device_fingerprint_service.dart` -> `sanctuary_http_client.dart` -> `secure_session_storage.dart`.
   - **Backend Endpoints:** `POST /api/v1/auth/register-intent` -> `POST /api/v1/auth/verify-magic-link` -> `POST /api/v1/auth/google-sync` -> `POST /api/v1/auth/refresh` -> `GET /api/v1/auth/me`.
   - **Service & Domain Layer:** `auth_service.py` -> `jwt_handler` -> `User` model (`backend/app/models/domain/user.py`).
   - **Database Tables:** `public.users`, `public.underage_quarantine_registry`, `public.consent_audit_logs`, `public.consumed_magic_tokens`.
   - **Status:** **FUNCTIONAL.**

2. **Journey 2: Profile Setup & Persona Management**
   - **Frontend UI:** `lib/features/profile_setup/presentation/screens/profile_setup_screen.dart` -> `my_persona_screen.dart` -> `photo_slot_grid.dart` -> `voice_spark_recorder_widget.dart` -> `eva_polish_modal.dart`.
   - **State & Networking:** `profile_setup_controller.dart` -> `sanctuary_http_client.dart`.
   - **Backend Endpoints:** `POST /api/v1/media/presigned-url` -> `DELETE /api/v1/media/moment/{slot_number}` -> `POST /api/v1/eva/polish-bio` -> `POST /api/v1/profile/create`.
   - **Service & Domain Layer:** `storage_service.py`, `eva_service.py`, `backend/app/api/v1/endpoints/profile.py`.
   - **Database Tables:** `public.users`.
   - **Status:** **BROKEN FOR EDITS.** Initial profile creation succeeds. However, attempting to edit an established profile from `my_persona_screen.dart` routes to `/profile-setup`, calling `POST /api/v1/profile/create`, which raises HTTP 400 `PROFILE_ALREADY_COMPLETED`. Missing `PUT /api/v1/profile`.

3. **Journey 3: Discovery Feed & Swiping Deck**
   - **Frontend UI:** `lib/features/feed/presentation/screens/feed_screen.dart` -> `glass_veil_widget.dart` -> `sanctuary_glass_container.dart`.
   - **State & Networking:** `feed_controller.dart` -> `discovery_profile.dart` -> `sanctuary_http_client.dart`.
   - **Backend Endpoints:** `GET /api/v1/feed` -> `POST /api/v1/feed/swipe`.
   - **Service & Domain Layer:** `feed_service.py` -> `backend/app/models/domain/match_and_chat.py` (`Swipe`, `Match`).
   - **Database Tables:** `public.users`, `public.swipes`, `public.matches`.
   - **Status:** **PARTIAL / DISCONNECTED.** Swiping works, but discovery cards cannot be tapped to open `SeekerProfileDetailScreen`.

4. **Journey 4: Resonances & Bilateral Match Reciprocation**
   - **Frontend UI:** `lib/features/resonances/presentation/screens/resonances_screen.dart` (TabBar: Mutual Matches & Secret Admirers).
   - **State & Networking:** `resonances_controller.dart` -> `sanctuary_http_client.dart`.
   - **Backend Endpoints:** `GET /api/v1/resonances/incoming` -> `GET /api/v1/resonances/mutual` -> `POST /api/v1/feed/swipe`.
   - **Service & Domain Layer:** `resonances.py`, `feed_service.py`, `SwipeRequest` schema (`feed.py`).
   - **Database Tables:** `public.swipes`, `public.matches`.
   - **Status:** **CRITICAL RUNTIME FAILURE.** `resonances_controller.dart#L69` sends `swipe_type: swipeType` instead of `action: swipeType`. Pydantic forbids extra fields; server returns HTTP 422. Silently fails; admirers cannot be liked back.

5. **Journey 5: Photo Reveal & Perceptual Modesty Veil**
   - **Frontend UI:** `lib/features/profile/presentation/screens/seeker_profile_detail_screen.dart` -> `glass_veil_widget.dart`.
   - **State & Networking:** `seeker_profile_controller.dart` -> `sanctuary_http_client.dart`.
   - **Backend Endpoints:** `GET /api/v1/revelation/photo/status/{target_id}` -> `POST /api/v1/revelation/photo/request` -> `POST /api/v1/revelation/photo/unlock-perk` -> `POST /api/v1/revelation/photo/respond`.
   - **Service & Domain Layer:** `photo_reveal_service.py` -> `PhotoRevealConsent` model (`revelation.py`).
   - **Database Tables:** `public.photo_reveal_consents`, `public.users`.
   - **Status:** **ORPHANED UI / INCOMPLETE RECIPROCATION.** `SeekerProfileDetailScreen` is disconnected from navigation. The backend endpoint `POST /api/v1/revelation/photo/respond` has no calling UI in Flutter.

6. **Journey 6: Ephemeral Chat, WebSocket Relay & Mindful Closure**
   - **Frontend UI:** `lib/features/chat/presentation/screens/chats_list_screen.dart` -> `chat_dialogue_screen.dart` -> `pass_with_grace_dialog.dart`.
   - **State & Networking:** `chat_dialogue_controller.dart` -> `chat_websocket_service.dart` -> `sanctuary_http_client.dart`.
   - **Backend Endpoints:** `POST /api/v1/chat/ws-ticket` -> `GET /api/v1/chat/messages/{match_id}` -> WebSocket `/ws/chat/{match_id}` -> `POST /api/v1/chat/close-with-grace` -> `POST /api/v1/users/{peer_id}/block`.
   - **Service & Domain Layer:** `chat_ws.py`, `chat_closure.py`, `ws_manager.py`, `ws_ticket_store.py`, `match_and_chat.py`.
   - **Database Tables:** `public.matches`, `public.messages`, `public.blocked_users`.
   - **Status:** **FUNCTIONAL.**

7. **Journey 7: Mindful Streaks, In-App Currency & Rewarded Ads SSV**
   - **Frontend UI:** `lib/features/growth/presentation/screens/growth_hub_screen.dart` -> `morning_harvest_dialog.dart` -> `streak_gauge_widget.dart`.
   - **State & Networking:** `growth_hub_controller.dart` -> `ad_waterfall_service.dart` -> `payment_service.dart` -> `sanctuary_billing_service.dart`.
   - **Backend Endpoints:** `GET /api/v1/store/catalog` -> `GET /api/v1/store/balances` -> `GET /api/v1/ads/status` -> `POST /api/v1/ads/claim-reward` -> `POST /api/v1/streak/claim-morning-harvest` -> `POST /api/v1/payments/create-order` -> `POST /api/v1/payments/verify-checkout`.
   - **Service & Domain Layer:** `store.py`, `ads.py`, `payments.py`, `streak.py`, `ad_ssv_service.py`, `streak_engine.py`, `payment_service.py`.
   - **Database Tables:** `public.ad_reward_ledger`, `public.processed_ad_transactions`, `public.in_app_purchases`, `public.pending_web_entitlements`, `public.users`.
   - **Status:** **DATABASE CHECK CONSTRAINT CRASH.** `ad_ssv_service.py` writes reward types not in PostgreSQL check constraint `chk_ad_reward_ledger_ad_type`, causing rollbacks on reward claims.

8. **Journey 8: Legal Vault, DPDP Incineration & Admin KYC Escalation**
   - **Frontend UI:** `lib/features/legal_vault/presentation/screens/vault_legal_screen.dart` -> `account_incineration_dialog.dart` -> `superadmin_kyc_desk_screen.dart`.
   - **State & Networking:** `vault_controller.dart` -> `sanctuary_http_client.dart`.
   - **Backend Endpoints:** `GET /api/v1/legal/nominee` -> `POST /api/v1/legal/nominee` -> `GET /api/v1/legal/grievances` -> `POST /api/v1/legal/grievance` -> `POST /api/v1/legal/data-export` -> `DELETE /api/v1/legal/account` -> `GET /api/v1/admin/kyc/escalations` -> `POST /api/v1/admin/kyc/{id}/decide`.
   - **Service & Domain Layer:** `legal.py`, `incineration.py`, `admin_kyc.py`, `legal_vault_service.py`, `account_incineration_service.py`, `admin_service.py`.
   - **Database Tables:** `public.data_nominees`, `public.grievance_dossiers`, `public.data_export_requests`, `public.admin_kyc_escalations`, `public.admin_audit_logs`.
   - **Status:** **DATABASE SCHEMA CRASH.** Type mismatch (`BIGINT` in SQL vs `UUID` in SQLAlchemy) and constraint violation (`"acknowledged"` status) crash `grievance_dossiers`. Missing NOT-NULL columns (`declared_age`) crash `admin_kyc_escalations`.

---

## 4. Comprehensive Disconnected & Orphaned Modules Catalog

### 4.1 Orphaned Screens & Components Catalog

| Category | Component / File | Lines | Exact Code Citation | Architectural Impact | Dead Code vs. Integration Gap | Action Required |
|---|---|---|---|---|---|---|
| **Orphaned Screen** | `SeekerProfileDetailScreen` | 726 | `lib/features/profile/presentation/screens/seeker_profile_detail_screen.dart#L13-L726` | Fully implemented photo carousel, 35px progressive veil unmasking, voice spark playback, ₹39 instant unmasking perk, and DPDP fuzzed coordinates. Route `/seeker-detail` is registered in `app_router.dart#L167-L176` and `window_security_service.dart#L12`, but zero components in `feed_screen.dart` or `resonances_screen.dart` call `context.push('/seeker-detail')`. Users cannot view detailed profile attributes. | **Missing Integration Gap** | In `lib/features/feed/presentation/screens/feed_screen.dart#L551`, wrap `SanctuaryGlassContainer` with `InkWell(onTap: () => context.push('/seeker-detail', extra: topProfile))`. Add card tap in `resonances_screen.dart`. |
| **Empty Stub** | `EvaSanctuaryScreen` | 15 | `lib/features/ai_sanctuary/presentation/screens/eva_sanctuary_screen.dart#L1-L15` | Displays `Text('EvaSanctuaryScreen')`. Route `/eva-sanctuary` is registered in `app_router.dart#L182-L185` but never navigated to. | **Dead Code Stub** | Implement AI wingman chat interface connecting to `POST /api/v1/ai/coach` or remove route from `app_router.dart`. |
| **Empty Stub** | `MagicLinkScreen` | 17 | `lib/features/auth/presentation/screens/magic_link_screen.dart#L1-L17` | Displays `Text('MagicLinkScreen')`. Route `/magic-link` registered in `app_router.dart#L94-L98`. Bypassed in production by Supabase OTP auth flow. | **Dead Code Stub** | Wire token consumption to `POST /api/v1/auth/verify-magic-link` or remove route and screen. |
| **Empty Stub** | `BlindDateHubScreen` | 15 | `lib/features/blind_date/presentation/screens/blind_date_hub_screen.dart#L1-L15` | Displays `Text('BlindDateHubScreen')`. Route `/blind-date` in `app_router.dart#L125-L128`. No entry points from main navigation shell. | **Missing Integration Gap** | Implement 3-minute blind date audio sanctuary hub or guard with feature flag. |
| **Empty Stub** | `BlindDateSessionScreen` | 20 | `lib/features/blind_date/presentation/screens/blind_date_session_screen.dart#L1-L20` | Displays `Text('BlindDateSessionScreen (sessionId: $sessionId)')`. Route `/blind-date-session` in `app_router.dart#L130-L136`. | **Missing Integration Gap** | Wire to `BlindDateSession` real-time audio/chat state or archive. |
| **Empty Stub** | `IgnoredProfilesScreen` | 15 | `lib/features/feed/presentation/screens/ignored_profiles_screen.dart#L1-L15` | Displays `Text('IgnoredProfilesScreen')`. Route `/ignored-profiles` in `app_router.dart#L178-L181`. Never referenced. | **Dead Code Stub** | Wire to unblock/undo pass screen or remove. |
| **Empty Stub** | `AppInfoScreen` | 15 | `lib/features/settings/presentation/screens/app_info_screen.dart#L1-L15` | Displays `Text('AppInfoScreen')`. Route `/app-info` in `app_router.dart#L163-L166`. Settings screen links to modal dialogs instead. | **Dead Code Stub** | Replace with statutory version/license viewer or delete. |
| **Orphaned Service** | `notificationServiceProvider` | 96 | `lib/core/services/notification_service.dart#L23-L26` | `NotificationService` provider is declared, but never read, watched, or initialized in `main.dart` or any controller. FCM device push token registration (`POST /api/v1/notifications/device-token`) is never executed on app launch. | **Missing Integration Gap** | In `main.dart` or `ur_heart_app.dart`, call `ref.read(notificationServiceProvider).syncDeviceToken(...)` after successful authentication. |
| **Orphaned Controller** | `blindDateControllerProvider` | 90 | `lib/features/blind_date/presentation/controllers/blind_date_controller.dart#L85-L89` | Implements MAU milestone eligibility polling and queue join/leave; never referenced by any widget in `lib/`. | **Missing Integration Gap** | Bind controller to `BlindDateHubScreen`. |
| **Redundant Shim** | `rewards/growth_hub_screen.dart` | 3 | `lib/features/rewards/presentation/screens/growth_hub_screen.dart#L1-L3` | Re-exports `lib/features/growth/presentation/screens/growth_hub_screen.dart`. | **Redundant Artifact** | Delete file; ensure all imports reference `features/growth/...`. |
| **Redundant Shim** | `settings/superadmin_kyc_desk_screen.dart` | 2 | `lib/features/settings/presentation/screens/superadmin_kyc_desk_screen.dart#L1-L2` | Re-exports `lib/features/admin/presentation/screens/superadmin_kyc_desk_screen.dart`. | **Redundant Artifact** | Delete file; update imports to `features/admin/...`. |
| **Redundant Shim** | `auth/providers/auth_controller.dart` | 2 | `lib/features/auth/presentation/providers/auth_controller.dart#L1-L2` | Re-exports `lib/features/auth/presentation/controllers/auth_controller.dart`. | **Redundant Artifact** | Delete file; update imports to `features/auth/presentation/controllers/...`. |

---

## 5. Backend API Endpoints & Contract Audit

### 5.1 Complete Backend Route Ledger (46 Distinct Operations)

| Prefix | Method | Endpoint Path | Operation ID / Handler | Request Body Model | Response Model | Callers in Flutter |
|---|---|---|---|---|---|---|
| Root | `GET, HEAD` | `/` | `root_sentinel` | None | `Response / JSONResponse` | UptimeRobot / ping |
| Root | `GET, HEAD` | `/health` | `health_sentinel` | None | `SanctuaryResponse[HealthResponse]` | Health probe |
| Root | `GET` | `/sentinel` | `superadmin_sentinel_diagnostics` | None | `SanctuaryResponse[Dict[str, Any]]` | Superadmin diagnostics |
| WebSocket | `WS` | `/ws/chat/{match_id}` | `chat_websocket_endpoint` | Query ticket | Binary / JSON frame | `chat_websocket_service.dart#L87` |
| `/auth` | `POST` | `/api/v1/auth/register-intent` | `register_intent` | `RegisterIntentRequest` | `SanctuaryResponse[dict]` | `auth_controller.dart#L213` |
| `/auth` | `POST` | `/api/v1/auth/send-magic-link` | `send_magic_link` | `MagicLinkSendRequest` | `SanctuaryResponse[dict]` | `auth_controller.dart#L292` |
| `/auth` | `POST` | `/api/v1/auth/google-sync` | `google_sync` | `GoogleSyncRequest` | `SanctuaryResponse[AuthTokensResponse]` | `auth_controller.dart#L317` |
| `/auth` | `POST` | `/api/v1/auth/verify-magic-link` | `verify_magic_link` | `MagicLinkVerifyRequest` | `SanctuaryResponse[AuthTokensResponse]` | `auth_controller.dart#L371` |
| `/auth` | `POST` | `/api/v1/auth/refresh` | `refresh_token` | `RefreshTokenRequest` | `SanctuaryResponse[TokenRefreshResponse]` | `sanctuary_http_client.dart#L57` |
| `/auth` | `GET` | `/api/v1/auth/me` | `get_current_seeker` | None | `SanctuaryResponse[dict]` | `my_persona_screen.dart#L39` |
| `/ai` | `POST` | `/api/v1/ai/coach` | `ai_coach` | `AICoachRequest` | `SanctuaryResponse[AICoachResponse]` | **DEAD (0 callers)** |
| `/ai` | `POST` | `/api/v1/ai/transcribe-voice-spark` | `transcribe_voice_spark` | `VoiceSparkTranscribeRequest` | `SanctuaryResponse[VoiceSparkTranscribeResponse]` | **DEAD (0 callers)** |
| `/eva` | `POST` | `/api/v1/eva/polish-bio` | `polish_bio` | `EvaBioRequest` | `SanctuaryResponse[EvaBioResponse]` | `eva_polish_modal.dart#L72` |
| `/media` | `POST` | `/api/v1/media/presigned-url` | `request_presigned_upload_url` | `PresignedUploadRequest` | `SanctuaryResponse[PresignedUploadResponse]` | `profile_setup_controller.dart#L163` |
| `/media` | `DELETE`| `/api/v1/media/moment/{slot_number}` | `delete_moment_asset` | Path `slot_number` | `SanctuaryResponse[Dict[str, Any]]` | `profile_setup_controller.dart#L231` |
| `/media` | `GET` | `/api/v1/media/voice/{user_id}/{filename}` | `redirect_voice_spark` | Path parameters | `RedirectResponse (307)` | Audio streaming |
| `/kyc` | `POST` | `/api/v1/kyc/presigned-upload` | `request_kyc_presigned_url` | `KYCPresignedRequest` | `SanctuaryResponse[KYCPresignedResponse]` | `profile_setup_controller.dart#L379` |
| `/kyc` | `POST` | `/api/v1/kyc/verify-liveness` | `verify_liveness` | `KYCLivenessRequest` | `SanctuaryResponse[KYCVerificationResponse]` | `profile_setup_controller.dart#L401` |
| `/kyc` | `GET` | `/api/v1/kyc/status` | `get_kyc_status` | None | `SanctuaryResponse[KYCStatusResponse]` | **DEAD (0 callers)** |
| `/admin/kyc`| `GET` | `/api/v1/admin/kyc/escalations` | `get_escalations` | Query params | `SanctuaryResponse[List[AdminKycEscalationResponse]]` | `superadmin_kyc_desk_screen.dart#L37` |
| `/admin/kyc`| `POST`| `/api/v1/admin/kyc/{id}/decide` | `decide_escalation` | `AdminKycDecisionRequest` | `SanctuaryResponse[Dict[str, Any]]` | `superadmin_kyc_desk_screen.dart#L77` |
| `/feed` | `GET` | `/api/v1/feed` | `get_feed` | Query params | `SanctuaryResponse[FeedDeckResponse]` | `feed_controller.dart#L55` |
| `/feed` | `POST` | `/api/v1/feed/swipe` | `swipe` | `SwipeRequest` (`action`) | `SanctuaryResponse[SwipeResponse]` | `feed_controller.dart#L126`, `resonances_controller.dart#L67` **[422 MISMATCH]** |
| `/revelation`| `GET`| `/api/v1/revelation/photo/status/{target_id}` | `get_photo_reveal_status` | Path `target_id` | `SanctuaryResponse[PhotoRevealStatusResponse]` | `seeker_profile_controller.dart#L71` |
| `/revelation`| `POST`| `/api/v1/revelation/photo/request` | `request_photo_reveal` | `PhotoRevealActionRequest` | `SanctuaryResponse[PhotoRevealStatusResponse]` | `seeker_profile_controller.dart#L139` |
| `/revelation`| `POST`| `/api/v1/revelation/photo/unlock-perk` | `unlock_photo_with_perk` | `PhotoRevealActionRequest` | `SanctuaryResponse[PhotoRevealStatusResponse]` | `seeker_profile_controller.dart#L178` |
| `/revelation`| `POST`| `/api/v1/revelation/photo/respond` | `respond_to_photo_reveal` | `PhotoRevealActionRequest` | `SanctuaryResponse[PhotoRevealStatusResponse]` | **DEAD (0 callers)** |
| `/revelation`| `GET` | `/api/v1/revelation/profile/{target_id}` | `get_seeker_public_profile` | Path `target_id` | `SanctuaryResponse[DiscoveryProfileResponse]` | `seeker_profile_controller.dart#L84` |
| `/streak` | `GET` | `/api/v1/streak/status` | `get_streak_status` | None | `SanctuaryResponse[StreakStatusResponse]` | **DEAD (0 callers)** |
| `/streak` | `POST` | `/api/v1/streak/heartbeat` | `streak_heartbeat` | None | `SanctuaryResponse[StreakHeartbeatResponse]` | **DEAD (0 callers)** |
| `/streak` | `POST` | `/api/v1/streak/claim-morning-harvest` | `claim_morning_harvest` | `MorningHarvestClaimRequest` | `SanctuaryResponse[MorningHarvestClaimResponse]` | `morning_harvest_dialog.dart#L75` |
| `/chat` | `POST` | `/api/v1/chat/ws-ticket` | `generate_ws_ticket` | None | `SanctuaryResponse[WSTicketResponse]` | `chat_websocket_service.dart#L55` |
| `/chat` | `GET` | `/api/v1/chat/messages/{match_id}` | `get_match_messages` | Path `match_id` | `SanctuaryResponse[List[ChatMessageResponse]]` | `chat_dialogue_controller.dart#L115` |
| `/chat` | `POST` | `/api/v1/chat/close-with-grace` | `close_chat_with_grace` | `ChatClosureRequest` | `SanctuaryResponse[dict]` | `chat_dialogue_controller.dart#L330` |
| `/notifications`|`POST`| `/api/v1/notifications/device-token` | `register_device_token` | `DeviceTokenRegisterRequest` | `SanctuaryResponse[dict]` | `notification_service.dart#L63` **[ORPHANED]** |
| `/notifications`|`DELETE`| `/api/v1/notifications/device-token`| `unregister_device_token` | `DeviceTokenUnregisterRequest` | `SanctuaryResponse[dict]` | `notification_service.dart#L75` |
| `/notifications`|`PUT` | `/api/v1/notifications/preferences` | `update_notification_preferences` | `NotificationPreferencesRequest` | `SanctuaryResponse[dict]` | `notification_service.dart#L83` |
| `/store` | `GET` | `/api/v1/store/catalog` | `get_store_catalog` | None | `SanctuaryResponse[StoreCatalogResponse]` | `sanctuary_billing_service.dart#L31` |
| `/store` | `GET` | `/api/v1/store/balances` | `get_store_balances` | None | `SanctuaryResponse[StoreBalancesResponse]` | `sanctuary_billing_service.dart#L35` |
| `/payments` | `POST` | `/api/v1/payments/create-order` | `create_razorpay_order` | `CreateOrderRequest` | `SanctuaryResponse[CreateOrderResponse]` | `payment_service.dart#L59` |
| `/payments` | `POST` | `/api/v1/payments/verify-checkout` | `verify_checkout` | `VerifyPaymentRequest` | `SanctuaryResponse[PaymentVerificationResponse]` | `payment_service.dart#L97` |
| `/payments` | `POST` | `/api/v1/payments/webhook/{gateway}` | Webhook handlers | Raw payload + Signature header | `{"status": "ok"}` | Gateway webhooks |
| `/payments` | `POST` | `/api/v1/payments/claim-web-entitlement`| `claim_web_entitlement` | Raw dict | `SanctuaryResponse[dict]` | **DEAD (0 callers)** |
| `/ads` | `GET` | `/api/v1/ads/status` | `get_ads_status` | None | `{"status": "ready"}` **[UNENVELOPED]** | `ad_waterfall_service.dart#L61` |
| `/ads` | `POST` | `/api/v1/ads/claim-reward` | `claim_reward` | **Raw Dict[str, Any]** | `SanctuaryResponse[dict]` | `sanctuary_billing_service.dart#L21` |
| `/legal` | `POST` | `/api/v1/legal/grievance` | `submit_grievance` | `GrievanceSubmissionRequest` | `SanctuaryResponse[GrievanceResponse]` | `vault_controller.dart#L203` |
| `/legal` | `GET` | `/api/v1/legal/grievances` | `list_grievances` | None | `SanctuaryResponse[List[GrievanceResponse]]` | `vault_controller.dart#L125` |
| `/legal` | `GET,POST`| `/api/v1/legal/nominee` | `get/register_nominee` | `NomineeRegistrationRequest` | `SanctuaryResponse[NomineeResponse]` | `vault_controller.dart#L124, L165` |
| `/legal` | `POST` | `/api/v1/legal/data-export` | `export_personal_data` | None | `SanctuaryResponse[DataExportResponse]` | `vault_controller.dart#L245` |
| `/legal` | `DELETE`| `/api/v1/legal/account` | `incinerate_account` | `AccountIncinerationRequest` | `SanctuaryResponse[dict]` | `account_incineration_dialog.dart#L96` |
| `/legal` | `GET` | `/api/v1/legal/{policy}` | Policy document getters | None | `SanctuaryResponse[dict]` | **DEAD (Static text in Flutter)** |
| `/profile` | `POST` | `/api/v1/profile/create` | `create_profile` | `ProfileCreate` | `SanctuaryResponse[dict]` | `profile_setup_controller.dart#L359` |
| `/profile` | **PUT** | **MISSING** | **NONE** | **N/A** | **N/A** | **CRITICAL: No edit endpoint exists!** |
| `/resonances`| `GET` | `/api/v1/resonances/incoming` | `get_incoming_resonances` | None | `SanctuaryResponse[dict]` | `resonances_controller.dart#L45` |
| `/resonances`| `GET` | `/api/v1/resonances/mutual` | `get_mutual_resonances` | None | `SanctuaryResponse[dict]` | `resonances_controller.dart#L46`, `chats_list_screen.dart#L39` |
| `/blind-date`| `GET` | `/api/v1/blind-date/eligibility` | `check_eligibility` | None | `SanctuaryResponse[dict]` | `blind_date_controller.dart#L55` |
| `/blind-date`| `POST`| `/api/v1/blind-date/queue/join` | `join_queue` | Raw body `{}` | `SanctuaryResponse[dict]` | `blind_date_controller.dart#L72` |
| `/users` | `GET` | `/api/v1/users/blocked` | `list_blocked_users` | None | `SanctuaryResponse[List[BlockedUserResponse]]` | **DEAD (0 callers)** |
| `/users` | `POST` | `/api/v1/users/{target_id}/block` | `block_user` | `BlockUserRequest` | `SanctuaryResponse[Dict[str, Any]]` | `chat_dialogue_controller.dart#L359` |
| `/users` | `DELETE`| `/api/v1/users/{target_id}/block` | `unblock_user` | Path `target_id` | `SanctuaryResponse[Dict[str, Any]]` | **DEAD (0 callers)** |

---

### 5.2 Critical Contract Mismatch Details

#### 1. Resonances Swipe Reciprocation: HTTP 422 Unprocessable Entity
- **Backend Schema:** `backend/app/schemas/feed.py#L9-L15`:
  ```python
  class SwipeRequest(BaseModel):
      target_id: uuid.UUID
      action: SwipeAction = Field(..., description="Action taken on profile: pass, like, super_like")
      direct_letter_text: Optional[str] = Field(None, max_length=280)
      model_config = ConfigDict(extra="forbid")
  ```
- **Flutter Invocation:** `lib/features/resonances/presentation/controllers/resonances_controller.dart#L67-L70`:
  ```dart
  await _client.post('/api/v1/feed/swipe', body: {
    'target_id': targetId,
    'swipe_type': swipeType,  // BUG: Must be 'action'
  });
  ```
- **Runtime Result:** FastAPI throws 422 with two validation errors:
  1. `{'type': 'missing', 'loc': ('body', 'action'), 'msg': 'Field required'}`
  2. `{'type': 'extra_forbidden', 'loc': ('body', 'swipe_type'), 'msg': 'Extra inputs are not permitted'}`
- **Behavioral Impact:** Admirers in the Resonances tab can NEVER be liked back or passed. Tapping "Resonate" or "Pass with Grace" triggers a snackbar error or fails silently.

#### 2. Profile Editing Dead-End: HTTP 400 Bad Request
- **Flutter Invocation:** `lib/features/profile/presentation/screens/my_persona_screen.dart#L397`:
  ```dart
  onTap: () => context.push('/profile-setup'),
  ```
  In `profile_setup_controller.dart#L359`:
  ```dart
  await _client.post('/api/v1/profile/create', body: payload);
  ```
- **Backend Rejection:** `backend/app/api/v1/endpoints/profile.py#L39-L44`:
  ```python
  if current_user.is_profile_completed:
      raise SanctuaryException(
          error_code="PROFILE_ALREADY_COMPLETED",
          message="Seeker profile has already been onboarded.",
          status_code=status.HTTP_400_BAD_REQUEST,
      )
  ```
- **Behavioral Impact:** No profile editing functionality exists. Any seeker attempting to edit their bio, education, or media is rejected with HTTP 400.

---

## 6. Database Schema Synchronization Audit

### 6.1 Discrepancy Matrix: PostgreSQL Migrations vs. SQLAlchemy Models

| Database Table | Property | Supabase PostgreSQL Migration (`supabase/migrations/`) | SQLAlchemy Declarative Model (`backend/app/models/domain/`) | Severity & Runtime Impact |
|---|---|---|---|---|
| `grievance_dossiers` | **Primary Key** | `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY` (`20260926...#L487`) | `id: UniversalUUID = mapped_column(default=uuid.uuid4, primary_key=True)` (`legal.py#L123`) | **CRITICAL:** PostgreSQL throws error: `column "id" is of type bigint but expression is of type uuid`. |
| `grievance_dossiers` | **Status Check Constraint** | `CHECK (status IN ('under_review', 'actioned', 'dismissed'))` (`20260926...#L493`) | `status: String(20) default="acknowledged"`, server default `"acknowledged"` (`legal.py#L141`). `legal_vault_service.py#L146` sets `status="acknowledged"`. | **CRITICAL:** Inserting grievance immediately violates PostgreSQL check constraint; transaction aborted. |
| `grievance_dossiers` | **Missing Columns** | Columns `statutory_notes`, `sla_deadline_at`, `resolved_at` DO NOT EXIST in SQL. Postgres has `resolution_summary` and `actioned_at`. | Model defines `statutory_notes TEXT`, `sla_deadline_at TIMESTAMPTZ`, `resolved_at TIMESTAMPTZ`. | **CRITICAL:** Queries on `GrievanceDossier` fail with `column "statutory_notes" does not exist`. |
| `admin_kyc_escalations` | **Primary Key** | `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY` (`20260926...#L539`) | `id: UniversalUUID = mapped_column(default=uuid.uuid4, primary_key=True)` (`admin_telemetry.py#L22`) | **CRITICAL:** Type mismatch on identity column prevents all inserts. |
| `admin_kyc_escalations` | **Missing NOT-NULL Columns** | Postgres requires: `declared_age INT2 NOT NULL`, `anchor_photo_url TEXT NOT NULL`, `kyc_video_url TEXT NOT NULL`, `groq_reasoning VARCHAR(255) NOT NULL`. | Model completely omits `declared_age` and `groq_reasoning`. Model names photo fields `selfie_storage_url` and `id_card_storage_url`. | **CRITICAL:** Inserts fail with `null value in column "declared_age" violates not-null constraint`. |
| `blind_date_messages` | **Primary Key** | `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` (`20260926...#L382`) | `id: BigIntPK = mapped_column(primary_key=True, autoincrement=True)` (`blind_date.py#L122`) | **HIGH:** Primary key type collision (UUID vs BigInt). |
| `blind_date_messages` | **Column Name Mismatch** | Column name is `ciphertext TEXT NOT NULL` (`20260926...#L386`) | Column name is `encrypted_text: Mapped[str] = mapped_column(Text)` (`blind_date.py#L138`) | **CRITICAL:** Querying messages fails with `column "encrypted_text" does not exist`. |
| `device_fcm_tokens` | **Primary Key & Columns** | `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`. Column name is `active BOOLEAN NOT NULL DEFAULT TRUE`. Has `installation_id`, `last_seen_at`. | `id: BigIntPK`. Column name is `is_active BOOLEAN`. Lacks `installation_id` and `last_seen_at`. | **HIGH:** Querying tokens fails with `column "is_active" does not exist`. |
| `ad_reward_ledger` | **Check Constraint** | `CHECK (ad_type IN ('daily_harvest_boost', 'extra_swipes', 'instant_reveal_key', 'super_like', 'instant_bridge_pass', 'streak_freeze', 'rewind_pass', 'compass_teleport', 'ad_free_24h', 'profile_spotlight', 'incognito_hour'))` (`20261015...#L41-L54`) | `backend/app/services/ad_ssv_service.py#L307-L345` writes: `'quick_reflection'`, `'deep_resonance'`, `'sacred_bridge_reveal'`, `'morning_harvest_unlock'`, `'daily_streak_boost'`. | **CRITICAL:** Check constraint violation rolls back transaction when user claims rewarded ad. |
| `whatsapp_reveal_tokens` | **Zombie Model** | DROPPED in migration `20261015120000_sync_schema_and_fix_incineration.sql#L116` (`DROP TABLE IF EXISTS public.whatsapp_reveal_tokens CASCADE;`). | Model still defined in `backend/app/models/domain/revelation.py#L16-L48`, exported in `__init__.py`, and asserted in tests. | **MEDIUM:** Zombie code cluttering domain models and schemas. |

---

## 7. Evaluation of Recent Architecture Fixes & Regressions

A chronological inspection of recent git commits (`d969b75`, `a19cd23`, `048ef37`, `71773c1`, `d01c162`, `ea72b90`, `2b70b86`, `61b228f`) reveals the progression of architecture fixes and newly introduced regressions:

### 7.1 Successful Fixes Verified
1. **Chat Closure Protocol & Peer Incineration (`20261015120000_sync_schema_and_fix_incineration.sql`):**
   - Altered `matches.closure_status` check constraint to include `'peer_incinerated'`.
   - Made `matches.user1_id` and `matches.user2_id` nullable (`ON DELETE SET NULL`) to resolve the "Vaporization Paradox" where deleting User A destroyed the entire match row for User B.
2. **Cryptographic Single-Use JTI Tracking (`20261013213000_phase2_consumed_magic_tokens.sql`):**
   - Implemented `consumed_magic_tokens` to defeat magic link replay attacks.
3. **Hardware Window Security (`FLAG_SECURE = 8192`):**
   - Enforced across authenticated routes (`/seeker-detail`, `/chat-dialogue`, `/main`) in `lib/core/services/window_security_service.dart`.
4. **FastAPI Lifespan Sentry Crash:**
   - Commit `71773c1` correctly imported `logging` in `main.py`, fixing boot crashes on Render.

### 7.2 Regressions & Blind Spots Uncovered
1. **Commit `61b228f` Introduced Resonances Contract Breakage:**
   - When wiring `ResonancesScreen` and `ResonancesController`, the request body was specified as `{'target_id': targetId, 'swipe_type': swipeType}` without validating against `SwipeRequest(action=...)`.
2. **Commit `61b228f` Introduced Profile Editing Dead-End:**
   - Added `onTap: () => context.push('/profile-setup')` in `my_persona_screen.dart`, pointing an onboarded seeker to the creation wizard without providing a `PUT /profile` backend route.
3. **Commit `61b228f` Created Database Constraint Divergence:**
   - Applied `chk_ad_reward_ledger_ad_type` to PostgreSQL with 11 reward names, but failed to update `ad_ssv_service.py` which was already emitting 5 completely different ad types.
4. **The SQLite Test Harness Mirage:**
   - The test suite (`backend/tests/`) runs against in-memory SQLite (`sqlite+aiosqlite:///:memory:`).
   - Because `Base.metadata.create_all()` creates tables directly from Python models (bypassing `.sql` migration files), SQLite never executes the PostgreSQL check constraints, and its loose type checking allows UUID strings into BigInt fields.
   - This allowed 181 tests to pass while leaving devastating PostgreSQL crashes latent in production.

---

## 8. Prioritized, Actionable Remediation Plan

### 8.1 Phase 1 (P0): Critical Client-Server & Database Crash Fixes

#### Step 1: Fix `ResonancesController` Swipe Request Payload
In `lib/features/resonances/presentation/controllers/resonances_controller.dart#L67-L70`:
```diff
     try {
       await _client.post('/api/v1/feed/swipe', body: {
         'target_id': targetId,
-        'swipe_type': swipeType,
+        'action': swipeType,
       });
     } catch (_) {
       return false;
```

#### Step 2: Implement `PUT /api/v1/profile` Endpoint
In `backend/app/schemas/profile.py`, define `ProfileUpdate`:
```python
class ProfileUpdate(BaseModel):
    bio: Optional[str] = Field(None, max_length=500)
    profession: Optional[str] = Field(None, max_length=100)
    education: Optional[str] = Field(None, max_length=100)
    photos: Optional[List[str]] = None
    avatar_url: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    voice_spark_url: Optional[str] = None
    voice_spark_duration: Optional[float] = None
```
In `backend/app/api/v1/endpoints/profile.py`, add route:
```python
@router.put("", response_model=SanctuaryResponse[Dict[str, Any]])
@router.put("/", response_model=SanctuaryResponse[Dict[str, Any]])
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    if payload.bio is not None:
        current_user.bio = payload.bio
    if payload.profession is not None:
        current_user.profession = payload.profession
    if payload.education is not None:
        current_user.education = payload.education
    if payload.photos is not None:
        current_user.photos = payload.photos
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    if payload.latitude is not None:
        current_user.latitude = payload.latitude
    if payload.longitude is not None:
        current_user.longitude = payload.longitude
    if payload.voice_spark_url is not None:
        current_user.voice_spark_url = payload.voice_spark_url
    if payload.voice_spark_duration is not None:
        current_user.voice_spark_duration = Decimal(str(payload.voice_spark_duration))

    await db.commit()
    await db.refresh(current_user)
    return SanctuaryResponse(data={"id": str(current_user.id), "full_name": current_user.full_name}, message="Profile updated.")
```

#### Step 3: Connect `SeekerProfileDetailScreen` to Navigation
In `lib/features/feed/presentation/screens/feed_screen.dart#L551`:
Wrap discovery card in `GestureDetector`:
```dart
return GestureDetector(
  onTap: () => context.push('/seeker-detail', extra: topProfile),
  child: ClipRRect(
    borderRadius: BorderRadius.circular(24.0),
    child: SanctuaryGlassContainer( ... ),
  ),
);
```

#### Step 4: Harmonize Database Schemas & Migrations
Create migration `supabase/migrations/20261016150000_harmonize_schema_types_and_constraints.sql`:
```sql
-- 1. Align grievance_dossiers check constraint & columns
ALTER TABLE public.grievance_dossiers 
    DROP CONSTRAINT IF EXISTS grievance_dossiers_status_check;
ALTER TABLE public.grievance_dossiers 
    ADD CONSTRAINT grievance_dossiers_status_check 
    CHECK (status IN ('under_review', 'actioned', 'dismissed', 'acknowledged', 'investigating', 'closed'));
ALTER TABLE public.grievance_dossiers 
    ADD COLUMN IF NOT EXISTS statutory_notes TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS sla_deadline_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;

-- 2. Align ad_reward_ledger check constraint with ad_ssv_service.py
ALTER TABLE public.ad_reward_ledger 
    DROP CONSTRAINT IF EXISTS chk_ad_reward_ledger_ad_type;
ALTER TABLE public.ad_reward_ledger 
    ADD CONSTRAINT chk_ad_reward_ledger_ad_type 
    CHECK (ad_type IN (
        'quick_reflection', 'deep_resonance', 'sacred_bridge_reveal', 
        'morning_harvest_unlock', 'daily_streak_boost', 'whatsapp_reveal',
        'daily_harvest_boost', 'extra_swipes', 'instant_reveal_key', 
        'super_like', 'instant_bridge_pass', 'streak_freeze', 
        'rewind_pass', 'compass_teleport', 'ad_free_24h', 
        'profile_spotlight', 'incognito_hour'
    ));

-- 3. Align blind_date_messages column name
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'blind_date_messages' 
          AND column_name = 'ciphertext'
    ) THEN
        ALTER TABLE public.blind_date_messages RENAME COLUMN ciphertext TO encrypted_text;
    END IF;
END $$;

-- 4. Align device_fcm_tokens column name
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'device_fcm_tokens' 
          AND column_name = 'active'
    ) THEN
        ALTER TABLE public.device_fcm_tokens RENAME COLUMN active TO is_active;
    END IF;
END $$;
```

Update SQLAlchemy models:
- In `backend/app/models/domain/legal.py`: Set `GrievanceDossier.id` to `BigIntPK` (matching PostgreSQL `BIGINT GENERATED ALWAYS AS IDENTITY`).
- In `backend/app/models/domain/admin_telemetry.py`: Set `AdminKycEscalation.id` to `BigIntPK`. Add `declared_age: Mapped[int] = mapped_column(SmallInteger, nullable=False)` and `groq_reasoning: Mapped[str] = mapped_column(String(255), nullable=False)`.
- In `backend/app/models/domain/blind_date.py`: Set `BlindDateMessage.id` to `UniversalUUID` (matching Postgres `UUID PRIMARY KEY`).
- In `backend/app/models/domain/admin_telemetry.py`: Set `DeviceFcmToken.id` to `UniversalUUID`.
- Prune `WhatsappRevealToken` from `revelation.py` and `__init__.py`.

---

### 8.2 Phase 2 (P1): Module Reconnection & Clean-Up

1. **Initialize Notification Service:**
   In `lib/core/app/ur_heart_app.dart#L12-L14`:
   ```dart
   ref.listen(authStateProvider, (previous, next) {
     if (next.value == true) {
       ref.read(notificationServiceProvider).syncDeviceToken('sample_device_fcm_token');
     }
   });
   ```
2. **Prune 3 Redundant Shims:**
   - Delete `lib/features/rewards/presentation/screens/growth_hub_screen.dart`.
   - Delete `lib/features/settings/presentation/screens/superadmin_kyc_desk_screen.dart`.
   - Delete `lib/features/auth/presentation/providers/auth_controller.dart`.
   - Update any legacy import references.
3. **Implement or Guard Stub Screens:**
   - Replace `app_info_screen.dart` with a static copyright, build version, and licenses viewer.
   - Either build the `BlindDateHubScreen` with queue join controls or remove the `/blind-date` route.

---

### 8.3 Phase 3 (P2): Pydantic Schema Hardening & Testing Parity

1. **Type Untyped Endpoints:**
   - Replace `Dict[str, Any]` in `POST /api/v1/ads/claim-reward` with `AdRewardClaimRequest(reward_type: str, ad_unit_id: str, verification_token: str)`.
   - Replace 18 `SanctuaryResponse[dict]` return types with concrete Pydantic schemas.
2. **PostgreSQL CI/CD Test Pipeline:**
   - Configure a GitHub Actions test job utilizing `postgres:16-alpine` running all `supabase/migrations/*.sql` scripts prior to pytest execution to eliminate SQLite environmental false positives.

---

## 9. Verification & Invalidation Commands

To independently verify all architectural findings and test execution:

```bash
# 1. Verify 181 Backend Pytest Suite Execution
$env:PYTHONPATH="."
python -m pytest backend/tests

# 2. Verify 71 Flutter Test Suite Execution
flutter test

# 3. Empirically Verify Resonances Swipe 422 Rejection
python -c "
from backend.app.schemas.feed import SwipeRequest
import pydantic
try:
    SwipeRequest(target_id='00000000-0000-0000-0000-000000000000', swipe_type='like')
    print('UNEXPECTED: Accepted swipe_type!')
except pydantic.ValidationError as e:
    print('VERIFIED: 422 Rejection on swipe_type:', e.errors()[0]['type'], e.errors()[1]['type'])
"

# 4. Empirically Verify Absence of PUT/PATCH Profile Routes
python -c "
from backend.app.main import app
profile_routes = [r.path for r in app.routes if 'profile' in getattr(r, 'path', '')]
put_patch = [r.path for r in app.routes if 'profile' in getattr(r, 'path', '') and any(m in getattr(r, 'methods', set()) for m in ['PUT', 'PATCH'])]
print('Profile Routes Registered:', profile_routes)
print('PUT/PATCH Routes Found:', put_patch)
assert len(put_patch) == 0, 'Unexpected PUT/PATCH found!'
print('VERIFIED: Zero PUT or PATCH profile endpoints exist!')
"

# 5. Empirically Verify Database Schema Type Mismatch (GrievanceDossier PK)
python -c "
from backend.app.models.domain.legal import GrievanceDossier
print('SQLAlchemy GrievanceDossier ID Type:', type(GrievanceDossier.id.type))
with open('supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql') as f:
    sql = f.read()
import re
match = re.search(r'CREATE TABLE IF NOT EXISTS public\.grievance_dossiers\s*\(\s*id\s+([^,]+)', sql)
print('PostgreSQL Migration GrievanceDossier ID DDL:', match.group(1) if match else 'Not found')
"
```
