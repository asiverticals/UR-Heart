# Project: UR-Heart Production Web Admin Portal

## Architecture
- **Framework**: FastAPI (Python 3.11) with SQLAlchemy ORM and PostgreSQL / SQLite.
- **Serving Location**: Directly served by FastAPI at `GET /admin` (Dashboard) and `GET /admin/login` (Auth Portal).
- **Backend APIs**: Dedicated endpoints under `/admin/api/*` and existing `/api/v1/admin/*`.
- **UI Architecture**: Standalone, responsive HTML5/CSS3/Vanilla JS embedded directly in FastAPI `HTMLResponse` (following established `backend/app/api/web_pages.py` architecture without introducing fragile template file dependencies).
- **Aesthetic**: Sanctuary Dark-Gold Glass Styling:
  - Deep Onyx background (`#07080B`)
  - Charcoal Glass panels & cards (`#141923` with 1px border `rgba(212, 175, 55, 0.2)` and `backdrop-filter: blur(12px)`)
  - Sacred Gold typography & accents (`#D4AF37`, `#F3E5AB`, `#996515`)
  - Semantic Status Accents: Crimson Gold (`#FF4D4D`), Emerald Glow (`#10B981`), Amber Warning (`#F59E0B`).
- **Security & Gatekeeper**:
  - Exclusively for `asiverticals@gmail.com`.
  - Secret key loaded from `.env`: `SUPERADMIN_SECRET_KEY` (fallback `settings.SUPERADMIN_SECRET_KEY`).
  - Signed HttpOnly Session Cookie with expiration and gatekeeper middleware redirecting unauthenticated requests to `/admin/login`.
  - SlowAPI rate-limiting on login endpoint.
- **Audit Logging**:
  - Every mutating action writes an immutable record to `admin_audit_logs` (`AdminAuditLog`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Superadmin Authentication | Login at `/admin/login` and `POST /admin/api/login` verifying `asiverticals@gmail.com` + `SUPERADMIN_SECRET_KEY` from `.env` | M1 | ORIGINAL_REQUEST § R2 |
| 2 | Gatekeeper Session Middleware | Enforce session cookie on `/admin/*`, redirecting unauthenticated requests to `/admin/login` | M1 | ORIGINAL_REQUEST § R2 |
| 3 | Admin Rate Limiting & Logout | SlowAPI brute force protection on login and session invalidation on `/admin/api/logout` | M1 | ORIGINAL_REQUEST § R2 |
| 4 | Immutable Admin Audit Engine | Centralized `log_admin_action` service recording admin email, action, target type, target id, ip, details to `admin_audit_logs` | M2 | ORIGINAL_REQUEST § R1.7, R4.3 |
| 5 | KYC Escalation Adjudication API | View pending KYC queue with 15-min presigned R2 URLs, approve/reject decision with biometric frame purge and audit record | M2 | ORIGINAL_REQUEST § R1.1, R4.1 |
| 6 | Grievance & Emergency NCII API | Query dossiers sorted by 24h statutory countdown SLA, resolve with status check constraints and audit record | M2 | ORIGINAL_REQUEST § R1.2, R4.1 |
| 7 | Seeker User Management API | Search seekers, inspect profile & quarantine status, 1-click ban/unban (`deleted_at` + session revocation), quarantine release | M2 | ORIGINAL_REQUEST § R1.3, R4.1 |
| 8 | Monetization Ledger & Dispute API | Query payments (`in_app_purchases`, `pending_web_entitlements`), manual sparks grant, manual pass/perk grant with audit record | M2 | ORIGINAL_REQUEST § R1.4, R4.1 |
| 9 | DPDP Compliance & Telemetry API | Query data export requests, nominee designations, consent logs, incineration records, and live system KPIs (DAU/MAU/FCM) | M2 | ORIGINAL_REQUEST § R1.5, R1.6 |
| 10 | Standalone Web Admin UI at `/admin` | Sanctuary dark-gold glass responsive single-page portal with tabbed views, KPI cards, tables, modal drawers, and live countdowns | M3 | ORIGINAL_REQUEST § R3 |
| 11 | Operations Overview & KPI Hub | Tab 1: Live metrics (Total Seekers, DAU, MAU, Pending KYC, Emergency NCII Tickets, 24h Revenue, Active FCM Devices) | M3 | ORIGINAL_REQUEST § R3.2 |
| 12 | Biometric KYC Adjudication Desk | Tab 2: Side-by-side frame review, Groq match score, Approve/Reject modals with reason selector | M3 | ORIGINAL_REQUEST § R3.2 |
| 13 | Grievance & NCII Moderation Desk | Tab 3: SLA sorted triage table, 24h countdown timer badges, evidence inspector drawer, resolution action modal | M3 | ORIGINAL_REQUEST § R3.2 |
| 14 | Seeker User Management Console | Tab 4: Live search, profile viewer, ban/unban toggle, quarantine appeals table | M3 | ORIGINAL_REQUEST § R3.2 |
| 15 | Monetization & Entitlements Desk | Tab 5: Transaction ledger, store filter, manual Sparks grant tool, manual pass grant tool | M3 | ORIGINAL_REQUEST § R3.2 |
| 16 | DPDP Compliance & Privacy Vault | Tab 6: Data export queue, nominee records, consent audit trail, account incineration certificates | M3 | ORIGINAL_REQUEST § R3.2 |
| 17 | Real-Time System Audit Log | Tab 7: Interactive table of `admin_audit_logs` with JSON payload inspection | M3 | ORIGINAL_REQUEST § R3.2 |
| 18 | Automated Pytest Suite for Admin | Complete pytest test coverage for auth, gatekeeper, all admin APIs, audit logs, and security | M4 | ORIGINAL_REQUEST § R5.1 |
| 19 | Existing Test Suite Verification | Verification that all 309 Python tests pass, 168 Flutter tests pass, and flutter analyze has 0 issues | M4 | ORIGINAL_REQUEST § R5.2 |
| 20 | Forensic Integrity & Zero-Push Audit | Static and runtime audit ensuring zero cheating, zero git pushes, and zero repository clutter | M4 | ORIGINAL_REQUEST § R5.3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Superadmin Auth & Gatekeeper | Login portal, credentials validation against `.env`, session cookie, gatekeeper middleware, logout, rate limiting | none | PLANNED |
| M2 | Admin Backend APIs & Audit Engine | Centralized audit logger, KYC endpoints, Grievance/NCII endpoints, Seeker ban/unban, Monetization & Sparks grant, DPDP & Telemetry APIs | M1 | PLANNED |
| M3 | Sanctuary Dark-Gold Admin Web UI | Standalone `/admin` dashboard with Sanctuary aesthetic, 7 interactive tabs, KPI cards, modals, live timers, and API fetch wiring | M1, M2 | PLANNED |
| M4 | Dual-Track E2E Test Suite & Full System Verification | Automated pytest suite for all admin features, verification of existing 309 Python + 168 Flutter tests + flutter analyze, Forensic Integrity Audit | M1, M2, M3 | PLANNED |

## Interface Contracts
### Superadmin Auth ↔ Gatekeeper Middleware
- **Login Request**: `POST /admin/api/login` payload `{"email": "asiverticals@gmail.com", "secret_key": "..."}`.
- **Login Response**: Sets HttpOnly, SameSite=Lax, Secure cookie `sanctuary_admin_session` containing HMAC-signed session token. Returns `{"success": true, "redirect_url": "/admin"}`.
- **Gatekeeper Middleware**:
  - Path prefix: `/admin` and `/admin/*`.
  - Excluded paths: `/admin/login`, `/admin/api/login`.
  - Behavior: If `sanctuary_admin_session` is missing or signature fails verification:
    - HTML request (Accept header contains `text/html` or path does not contain `/api/`): HTTP 303 Redirect to `/admin/login`.
    - API request (`/admin/api/*`): HTTP 401 Unauthorized `{"detail": "Admin authentication required"}`.

### Admin APIs ↔ Admin Audit Engine
- **Function**: `log_admin_action(session: Session, admin_email: str, action: str, target_type: str, target_id: str, details: dict, ip_address: Optional[str]) -> AdminAuditLog`
- **Guarantees**: Flushes/commits audit record inside current or independent transaction to ensure immutability.

### Grievance API Contract
- `GET /admin/api/grievances?category=&status=&limit=&offset=` -> `[{"dossier_reference_id", "violation_category", "status", "sla_deadline_at", "remaining_sla_seconds", "evidence_text", "created_at"}]`
- `POST /admin/api/grievances/{dossier_id}/resolve` -> payload `{"status": "actioned"|"dismissed"|"investigating"|"closed", "resolution_summary": "..."}` -> strictly validated against `GrievanceDossier` status check constraints.

### Seeker Management API Contract
- `GET /admin/api/users?query=&status=&limit=&offset=` -> `[{"id", "email", "handle", "is_banned", "is_quarantined", "reward_balance", "created_at"}]` (with masked contact bridge).
- `POST /admin/api/users/{user_id}/toggle-ban` -> payload `{"reason": "..."}` -> toggles `deleted_at`, increments `token_version`, writes audit log.

### Monetization Dispute API Contract
- `POST /admin/api/users/{user_id}/grant-sparks` -> payload `{"sparks_amount": 100, "reason": "Customer dispute resolution"}` -> updates `User.reward_balance`, writes audit log.
- `POST /admin/api/users/{user_id}/grant-pass` -> payload `{"sku": "pass_monthly", "reason": "Missing purchase recovery"}` -> activates entitlement, writes audit log.

## Code Layout
- `backend/app/api/admin_portal.py`: Main administrative router containing `/admin` (dashboard HTML), `/admin/login` (login HTML), session auth handlers, gatekeeper dependency, and `/admin/api/*` JSON endpoints.
- `backend/app/services/admin_audit_service.py`: Centralized audit logging utility.
- `backend/app/main.py`: Include `admin_portal.py` router and mount admin gatekeeper middleware.
- `backend/tests/test_admin_portal.py`: Automated pytest test suite for all admin functionality.
