# E2E Test Infra: UR-Heart Web Admin Portal

## Test Philosophy
- **Requirement-Driven & Opaque-Box**: Derived strictly from `ORIGINAL_REQUEST.md` and regulatory statutes (DPDP Act 2023, IT Rules 2021).
- **Zero-Dependency on Implementation Quirks**: Exercises endpoints via standard HTTP clients (`httpx.AsyncClient` / `TestClient`).
- **Methodology**: Category-Partition, Boundary Value Analysis, Pairwise Interaction, and Real-World Operational Scenarios.

## Feature Inventory & Test Matrix
| # | Feature | Requirement | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Scenario) |
|---|---------|-------------|:-----------------:|:-----------------:|:-----------------:|:-----------------:|
| 1 | Superadmin Authentication | R2.1 | 5 | 5 | ✓ | ✓ |
| 2 | Gatekeeper Route Protection & Redirect | R2.2 | 5 | 5 | ✓ | ✓ |
| 3 | Admin Rate Limiting & Logout | R2.2 | 5 | 5 | ✓ | ✓ |
| 4 | Immutable Admin Audit Log Engine | R1.7, R4.3 | 5 | 5 | ✓ | ✓ |
| 5 | KYC Escalation Adjudication | R1.1, R4.1 | 5 | 5 | ✓ | ✓ |
| 6 | Emergency NCII & Grievance SLA Desk | R1.2, R4.1 | 5 | 5 | ✓ | ✓ |
| 7 | Seeker Ban/Unban & Quarantine | R1.3, R4.1 | 5 | 5 | ✓ | ✓ |
| 8 | Monetization Ledger & Dispute Grants | R1.4, R4.1 | 5 | 5 | ✓ | ✓ |
| 9 | DPDP Vault & Live Telemetry KPIs | R1.5, R1.6 | 5 | 5 | ✓ | ✓ |
| 10 | Standalone Web Portal UI (`/admin`) | R3.1, R3.2 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Runner**: Pytest with `pytest-asyncio`
  - Command: `python -m pytest backend/tests/test_admin_portal.py -v`
  - Overall Regression Command: `python -m pytest backend/tests -q` (309 existing + new admin tests must all pass with 0 failures)
  - Flutter Regression Command: `flutter test` (168 tests must all pass) + `flutter analyze` (0 issues)
- **Directory Layout**:
  - `backend/tests/test_admin_portal.py`: Comprehensive test suite for all admin portal functionality.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Expected Outcome |
|---|----------|--------------------|------------------|
| 1 | Emergency NCII 24h Takedown Workflow | F1, F2, F6, F4 | Superadmin logs in, sorts grievances by remaining SLA, inspects 24h ticket, marks `actioned` with statutory notes, and verifies audit entry in `admin_audit_logs`. |
| 2 | Biometric KYC Adjudication with Ephemeral Purge | F1, F2, F5, F4 | Superadmin views pending KYC queue, reviews 15-min presigned URLs, approves valid seeker, verifies status becomes `approved` and audit log is recorded. |
| 3 | Seeker Underage Quarantine & Account Ban Management | F1, F2, F7, F4 | Superadmin searches seeker, toggles account ban (setting `deleted_at`, revoking tokens), verifies user cannot authenticate, and restores account. |
| 4 | Monetization Customer Support Dispute Resolution | F1, F2, F8, F4 | Superadmin inspects failed/pending transaction, manually grants 100 Sparks to seeker wallet, verifies `reward_balance` increases, and audit log captures reason. |
| 5 | Brute Force Attack & Unauthorized Infiltration Rejection | F1, F2, F3 | Adversary attempts login with non-superadmin email or wrong secret, attempts unauthenticated GET `/admin`, verified all attempts are rejected and redirected. |

## Acceptance Criteria
- 100% of new admin portal tests pass.
- 100% of existing 309 Python tests pass with 0 failures.
- 100% of existing 168 Flutter tests pass with 0 failures.
- `flutter analyze` reports 0 issues.
- Zero git pushes executed.
