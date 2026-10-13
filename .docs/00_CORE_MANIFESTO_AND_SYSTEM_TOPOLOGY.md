1. Executive System Manifesto & Anti-"Vibe-Code" Philosophy
UR-Heart ("The Sacred Sanctuary") ek intentional, privacy-first romantic kinship network hai. Iska primary engineering goal superficial swipe gamification, algorithmic loneliness extraction, unsolicited photo exposure, aur predatory recurring subscription paywalls ko eradicate karna hai.
MD

+ 1

Antigravity aur kisi bhi autonomous coding engine ke liye mandatory directive: Zero Ambiguity, Zero Superficial Scaffolding ("Vibe-Coding"), Zero Unhandled Error States, aur Bilateral Symmetry.

MD

Non-Negotiable Engineering Rules
Zero Dynamic JSON in Domain Layers: Domain logic aur state transitions ke andar plain Python dict ya dynamic Dart Map<String, dynamic> ka direct unchecked manipulation strictly prohibited hai. Har input/output bound Pydantic v2 validation models (backend/app/schemas/) ya immutable compile-time null-safe Dart classes (@immutable) ke through hona chahiye.
MD

+ 1

Explicit Error Containment: Koi bhi silent failure ya generic unhandled exception allow nahi hai. Har domain failure SanctuaryException ke structured error contract ko adhere karega:
MD

+ 1

JSON

{
  "success": false,
  "error_code": "STRING_IDENTIFIER",
  "message": "Human readable sanctuary message",
  "timestamp": "2026-10-13T07:38:00Z"
}

MD

1. Idempotency & Replay Immunity: Har financial order (orders, in_app_purchases), reward credit (ad_reward_ledger), aur client chat message (messages) database UNIQUE constraints aur deterministic idempotency keys (order_id, ssv_transaction_id, client_id) se guarded rahega. Duplicate callback par application crash nahi karegi, balki idempotent HTTP 200 return karegi.
2. Ponytail Minimalism Standard: Har layer me standard library constructs aur native framework capabilities ko priority do. Bina strong architectural justification ke koi naya third-party package add nahi hoga. Har necessary shortcut par mandatory annotation standard implement hoga:
MD

+ 3

Python

# shortcut: <limit description>, <when to upgrade>

MD

1. Multi-Cloud Architecture & System Topology
System ko aise design kiya gaya hai ki ye bina kisi upfront credit card requirement ke 10,000 active seekers tak seamlessly scale kare. Cloudflare R2, Azure Blob, aur Heroku strictly pluggable fallback adapters ke roop me exist karte hain jo tabhi initialize hote hain jab unke environment variables explicitly present hon.
MD

+ 1

                                  ┌────────────────────────────────────────────────────────┐
                                  │             CLIENT LAYER (Flutter 3.x)                 │
                                  │  • Native Android (.apk/.aab)   • iOS/Desktop PWA      │
                                  │  • FLAG_SECURE Window Shield   • Keystore Storage Vault│
                                  │  • Riverpod State Management   • Frosted Glass UI/UX   │
                                  └───────────────────────────┬────────────────────────────┘
                                                              │
                                                              ▼
                                  ┌────────────────────────────────────────────────────────┐
                                  │         EDGE GATEWAY & CDN (https://urheart.app)       │
                                  │  • Cloudflare SSL, DNS & CDN   • Web Security Headers  │
                                  │  • IP Sanitization             • DDoS Protection       │
                                  └───────────────────────────┬────────────────────────────┘
                                                              │
                                                              ▼
                                  ┌────────────────────────────────────────────────────────┐
                                  │         APPLICATION SERVER (FastAPI on Render)         │
                                  │  • Stateless JWT HS256         • 28 Router Modules     │
                                  │  • UptimeRobot HEAD Keep-Alive • WSS Relay (<5ms RAM)  │
                                  │  • 3-Engine AI Reasoning       • Multi-Payment Gateway │
                                  └───────────────┬────────────────────────┬───────────────┘
                                                  │                        │
                        ┌─────────────────────────┴────────┐      ┌────────┴─────────────────────────┐
                        ▼                                  ▼      ▼                                  ▼
        ┌────────────────────────────────┐ ┌────────────────────────────────┐ ┌────────────────────────────────┐
        │       DATABASE PERSISTENCE     │ │         STORAGE ADAPTER        │ │      THIRD-PARTY ENGINES       │
        │  • Supabase PostgreSQL 15+     │ │  • Supabase Storage (Default)  │ │  • Firebase Console (FCM v1)   │
        │  • 24 Relational Master Tables │ │  • Cloudflare R2 Dual Adapter  │ │  • Razorpay / Cashfree UPI     │
        │  • 100% RLS Enabled            │ │  • Azure Blob Dual Adapter     │ │  • 5-Network Ad SSV Waterfall  │
        │  • PgBouncer Port 6543         │ │  • <60s Ephemeral KYC Purge    │ │  • Google Play Billing v3      │
        └────────────────────────────────┘ └────────────────────────────────┘ └────────────────────────────────┘

MD

Production Infrastructure Breakdown
Primary Compute (Render Web Service): backend/Dockerfile based on python:3.11-slim, system packages tesseract-ocr, tesseract-ocr-eng, libgl1, aur curl. Free tier ke 512MB RAM ceiling ko respect karne ke liye single-worker Uvicorn configuration compulsory hai:
MD

+ 1

Bash

uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1

MD

Sleepless Uptime Sentinel: Render free instance 15 minute ke idle state par spin-down ho jata hai. Is cold-start ko eliminate karne ke liye UptimeRobot har 5 minute me HTTP HEAD /health aur HTTP HEAD / trigger karta hai. Endpoint 0ms database overhead ke sath empty body aur mandatory header X-Sanctuary-Alive: true return karta hai.
MD

+ 2

Primary Database (Supabase PostgreSQL 15+): Connection pooling PgBouncer port 6543 (transaction mode) ke through routed hai. Sabhi 24 tables par Row Level Security (RLS) active hai.
MD

+ 1

Primary Media Storage (Supabase Storage Bucket ur-heart-media): Zero-card fallback tier. Public upload allowed nahi hai; RLS rule enforced hai path format users/{auth.uid()}/moments/slot_[1-5].webp par, max payload size 100 KB, MIME-type strictly image/webp.
MD

+ 1

Secondary Storage Adapters: Cloudflare R2 (S3v4 API) aur Azure Blob Storage dynamically instantiate honge agar unke credentials .env me provide kiye gaye hon.
MD

1. The 7 Non-Negotiable Architectural Invariants
Antigravity ko har code change aur module rebuild ke waqt in 7 invariants ko strictly enforce karna hai:

Strict Type Safety & Schema Contracts: Dart Null Safety client par enforce rahegi. Python backend par Pydantic v2 strict models use honge. Database boundary par explicit SQL types aur check constraints rahenge.
MD

+ 2

Zero-Card Deployment Guarantee: Core application logic kisi aise cloud service par hardcode depend nahi karegi jisme boot karne ke liye paid credit card validation mandatory ho. Cloudflare R2/Azure/Heroku strictly pluggable interfaces hain.
MD

+ 1

Directory Structure Symmetry: Codebase structure deterministic hoga:
MD

backend/app/api/v1/endpoints/: Strictly 28 router files, no inline raw SQL (services layer call compulsory).
MD

backend/app/models/domain/: Exactly 24 SQLAlchemy models mapped 1:1 to database tables.
MD

lib/core/: Security vaults, tokens, themes, native platform channels, base clients.
MD

lib/features/<module>/: Strictly modular clean architecture (presentation/, controllers/, domain/, data/).
MD

Error Taxonomy & Fail-Safe Containment: SanctuaryException hierarchy ka use hoga. Production environment (ENVIRONMENT=production) me internal server error tracebacks, raw SQL error strings, ya file paths client ko leak nahi honge.
MD

+ 1

Idempotency & Replay Defense: Har billing webhook, ad reward callback, aur user message unique idempotency keys se register honge.
MD

Rate Limiting & Anti-Abuse Cooldowns:

Global IP limiter: 120 requests/minute.
MD

Auth endpoints: 10 requests/minute.
MD

AI Companion / Wingman: 20 requests/minute.
MD

Ad SSV claim route: 30 requests/minute with mandatory 2.0 seconds server-side cooldown between sequential claims.
MD

Ponytail Code Discipline: Minimum lines of code, standard library first, zero unrequested feature additions, zero over-engineering.
MD

1. Monorepo Directory Layout & File Taxonomy
Plaintext

ur-heart-sanctuary/
├── .docs/                                     # 12 Ground-Truth Engineering Files
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/                 # 28 Modular Router Files
│   │   │       └── router.py                  # Master APIRouter aggregator
│   │   ├── core/
│   │   │   ├── config.py                      # Pydantic BaseSettings (All env vars)
│   │   │   ├── database.py                    # Async SQLAlchemy session engine
│   │   │   ├── exceptions.py                  # SanctuaryException taxonomy
│   │   │   └── security.py                    # JWT, hashing, encryption utils
│   │   ├── models/
│   │   │   └── domain/                        # 24 SQLAlchemy 2.0 ORM Models
│   │   ├── schemas/                           # Pydantic v2 Request/Response contracts
│   │   ├── services/                          # Business logic, Adapters, AI & Billing
│   │   └── main.py                            # FastAPI Lifespan, CORS, Middleware
│   ├── tests/                                 # Pytest Verification Suites
│   ├── Dockerfile                             # Python 3.11-slim + Tesseract container
│   ├── Procfile                               # Heroku dyno execution specification
│   └── requirements.txt                       # Backend Python dependencies
├── lib/
│   ├── core/
│   │   ├── ads/                               # Ad mediation, SSV verifier & auction
│   │   ├── app/                               # ur_heart_app.dart & entry shell
│   │   ├── constants/                         # app_typography.dart & layout tokens
│   │   ├── services/                          # Notification, WebSocket, WindowSecurity
│   │   ├── storage/                           # secure_session_storage.dart (Keystore)
│   │   └── theme/                             # glass_tokens.dart, colors & themes
│   ├── features/
│   │   ├── ai_sanctuary/                      # Eva/Arjun & Wingman conversational coaching
│   │   ├── auth/                              # Consent, 18+ Age Gate, Magic Link
│   │   ├── blind_date/                        # 180s/300s Veil chat & queue system
│   │   ├── chat/                              # 1:1 E2EE real-time dialogue chamber
│   │   ├── feed/                              # Discovery card deck & swipe engine
│   │   ├── growth/                            # Streak multipliers & growth mechanics
│   │   ├── legal_vault/                       # DPDP data portability, nominee, erasure
│   │   ├── navigation/                        # Sanctuary navigation shell & PWA banner
│   │   ├── profile/                           # MyPersona & Seeker details + Voice Spark
│   │   ├── profile_setup/                     # Onboarding, 5-slot upload, KYC selfie
│   │   ├── resonances/                        # Mutual resonance & incoming like views
│   │   ├── rewards/                           # Sovereign store, Razorpay/Cashfree
│   │   └── settings/                          # Privacy toggles, Incognito, KYC desk
│   └── main.dart                              # Flutter client entry point
├── supabase/
│   └── migrations/                            # Immutable sequential SQL migrations
├── web/
│   ├── firebase-messaging-sw.js               # Background push notification worker
│   ├── index.html                             # iOS Safari standalone meta tags
│   ├── manifest.json                          # PWA install configuration
│   └── sw.js                                  # Service Worker offline asset cache
└── test/                                      # Verified Flutter test suites

MD

1. Master Environment Configuration (backend/app/core/config.py)
Backend server configuration Pydantic v2 BaseSettings par build hoga. Production startup par validate_production_secrets() run hoga jo missing ya insecure keys par application ko immediately fail-fast shut down kar dega.
MD

+ 1

Variable Name Type Default Value Production Requirement & Fallback Behavior
ENVIRONMENT str "development" Set to "production" on live deployments.
PORT int 10000 
Port for Uvicorn binding. Render assigns automatically via $PORT.
MD

+ 1

TESTING bool False 
Agar True hai toh mock ad assertions allow honge. Production me strictly False.
MD

+ 1

DATABASE_URL str "" 
Supabase PgBouncer PostgreSQL connection string (Port 6543).
MD

SUPABASE_URL str "" 
Supabase project API gateway URL ([https://xyz.supabase.co](https://xyz.supabase.co)).
MD

SUPABASE_SERVICE_ROLE_KEY str "" 
Elevated service role key for system operations and bypasses.
MD

JWT_SECRET_KEY str "" 
Min 32 characters in production. Validation fails fast if < 32.
MD

+ 1

JWT_ALGORITHM str "HS256" 
Cryptographic algorithm for stateless bearer tokens.
MD

ACCESS_TOKEN_EXPIRE_MINUTES int 60 
User session access token lifetime.
MD

REFRESH_TOKEN_EXPIRE_DAYS int 30 
Refresh token lifecycle window.
MD

WS_TICKET_EXPIRE_SECONDS int 60 
Single-use ticket lifetime for WebSocket upgrade.
MD

BLIND_DATE_MIN_ACTIVE_USERS int 1000000 
Condition C1 milestone gate threshold.
MD

ENABLE_BLIND_DATE_OVERRIDE bool False 
Condition C1 test override flag. Default False.
MD

+ 1

ENABLE_GLOBAL_USD_BILLING bool False 
Condition C2 monetization gate. Default False (INR priority).
MD

+ 1

PASSPORT_MIN_ACTIVE_USERS int 1000000 
Condition C3 passport milestone threshold.
MD

ENABLE_PASSPORT_OVERRIDE bool False 
Condition C3 test override flag. Default False.
MD

+ 1

PAYMENT_GATEWAY str "razorpay" 
Selection flag: "razorpay" ya "cashfree".
MD

RAZORPAY_KEY_ID str "" 
Razorpay public key ID.
MD

RAZORPAY_KEY_SECRET str "" 
Razorpay secret for HMAC signature verification.
MD

RAZORPAY_WEBHOOK_SECRET str "" 
Secret for verifying incoming Razorpay webhooks.
MD

CASHFREE_CLIENT_ID str "" 
Cashfree API Client ID.
MD

CASHFREE_SECRET_KEY str "" 
Cashfree API Secret Key.
MD

CLOUDFLARE_ACCOUNT_ID str "" 
Optional: Cloudflare R2 Account Identifier.
MD

R2_ACCESS_KEY_ID str "" 
Optional: Cloudflare R2 S3v4 access key.
MD

R2_SECRET_ACCESS_KEY str "" 
Optional: Cloudflare R2 S3v4 secret.
MD

R2_BUCKET_NAME str "ur-heart-media" Cloudflare R2 storage bucket identifier.
GOOGLE_SERVER_CLIENT_ID str "" 
OAuth2 Google Sign-in RS256 token verification audience.
MD

FIREBASE_PROJECT_ID str "" 
Firebase project ID for FCM v1 HTTP notifications.
MD

FIREBASE_SERVICE_ACCOUNT_JSON str "{}" Serialized service account credential JSON for push dispatch.
GROQ_API_KEY str "" 
API key for Groq Vision KYC and Llama 3.3 70B icebreakers.
MD

GEMINI_API_KEY str "" 
API key for Gemini 2.5 Flash Wingman coaching.
MD

ADMIN_SUPERUSER_EMAIL str "" 
Superadmin account identifier for administrative escalation. Must be explicitly set in environment variables; empty default fails validate_production_secrets() in production.
MD

1. Sleepless Keep-Alive Sentinel Architecture
Render ka free-tier web container 15 minutes of inactivity ke baad process suspend kar deta hai. UR-Heart bina paid dyno upgrade ke 100% operational availability maintain karne ke liye specialized Sleepless Sentinel Protocol implement karta hai:
MD

+ 1

Sentinel Execution Flow
Pinger: External UptimeRobot monitor har 300 seconds (5 minutes) me HTTP HEAD [https://urheart.app/health](https://urheart.app/health) aur HTTP HEAD [https://urheart.app/](https://urheart.app/) dispatch karta hai.
MD

0ms DB Overhead Guarantee: Health check routes database connection pool par query execute nahi karte. Ye process memory level par response compile karke turant dispatch karte hain.
MD

+ 1

HTTP Header Assertion: Response headers me X-Sanctuary-Alive: true aur Cache-Control: no-cache, no-store, must-revalidate send hota hai.
MD

Zero-Byte Body on HEAD: HEAD request aane par Uvicorn empty body stream karta hai, jisse network bandwidth consumption negligible rehti hai.
MD

Implementation Reference (backend/app/api/v1/endpoints/health.py)
Python

from fastapi import APIRouter, Response, status

router = APIRouter(tags=["HealthSentinel"])

@router.api_route("/health", methods=["GET", "HEAD"], status_code=status.HTTP_200_OK)
async def health_check_sentinel(response: Response):
    response.headers["X-Sanctuary-Alive"] = "true"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return {"status": "alive", "sanctuary": "active", "db_overhead_ms": 0}

1. Antigravity Operational Directives
Jab Antigravity autonomous development mode me chale, use in precise ground rules ko follow karna hoga:

Read-First Protocol: Kisi bhi code generation session ke starting me Antigravity .docs/00_CORE_MANIFESTO_AND_SYSTEM_TOPOLOGY.md aur task-specific targeted doc (e.g., 01_ for UI, 02_/03_ for DB, etc.) ko read karega.

No Hallucinated Packages: dependencies add karte waqt sirf requirements.txt aur pubspec.yaml me already listed tested packages ko use karna hai.
MD

Atomic Verification Gate: Har step ke baad compilation aur tests verify honge. Red test suite ke sath file modify karna strictly prohibited hai.
MD
