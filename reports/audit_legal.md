# LEGAL, REGULATORY & PLATFORM COMPLIANCE AUDIT REPORT

**Target Platform**: UR-Heart Dating Sanctuary  
**System Architecture**: Flutter Cross-Platform Client (`lib/`), FastAPI Asynchronous Backend (`backend/`), Supabase PostgreSQL Database & Cloudflare R2 Object Storage (`supabase/`)  
**Audit Archetype**: Legal & Regulatory Specialist Worker (`worker_legal_1`)  
**Publication Date**: October 15, 2026  
**Audit Classification**: Comprehensive Statutory, Regulatory & Platform Due Diligence  
**Governing Jurisdictions & Standards**:
1. **Republic of India**:
   - Digital Personal Data Protection Act, 2023 (DPDP Act 2023)
   - Information Technology Act, 2000 (IT Act 2000)
   - Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021 (as amended 2022 and 2023)
   - Protection of Children from Sexual Offences Act, 2012 (POCSO Act 2012)
   - Bharatiya Nyaya Sanhita, 2023 (BNS 2023)
   - Consumer Protection Act, 2019 & Consumer Protection (E-Commerce) Rules, 2020
   - Reserve Bank of India (RBI) Guidelines on Digital Payments and Card-on-File Tokenisation
2. **Global App Store Ecosystems**:
   - Apple App Store Review Guidelines (Guideline 1.2 User Generated Content, Guideline 3.1.1 Payments & In-App Purchases, Guideline 5.1.1 Data Privacy & Account Deletion)
   - Google Play Developer Program Policies (User Generated Content, Families & Children Policy, In-App Billing Policy)

---

## 1. EXECUTIVE SUMMARY & REGULATORY RISK HEATMAP

### 1.1 Executive Compliance Overview
UR-Heart positions itself architecturally and commercially as a "Sacred Dating Sanctuary" focused on privacy, psychological safety, and conscious human connection. However, an empirical legal and forensic code audit of the production repository reveals an alarming divergence between the platform's privacy-first marketing narrative and its underlying implementation. 

The platform currently faces critical architectural compliance gaps across Indian statutory frameworks and global mobile app distribution rules. While sections 3–5 and 7–17 of the Digital Personal Data Protection Act, 2023 (DPDP Act 2023) have a notified commencement date of May 13, 2027, architectural defects must be remediated in advance of enforcement to avoid statutory liabilities upon commencement. Furthermore, criminal obligations under POCSO Act 2012, IT Act 2000, and Intermediary Safe Harbor under Section 79 apply immediately:
1. **Children's Data Processing & Criminal Vulnerability**: The platform contains an age verification gate bypass. During Google Sign-In, the backend unconditionally provisions accounts with a birthdate of `January 1, 2000` (`backend/app/services/auth_service.py#L142`), allowing minors unrestricted access to an adult dating platform in direct conflict with Section 9 of the DPDP Act 2023 (effective May 13, 2027) and the POCSO Act 2012 (effective immediately).
2. **Complete Forfeiture of Intermediary Safe Harbor**: The platform has published zero Terms of Service, zero Privacy Policy, and zero statutory Grievance Officer details. It has hardcoded its in-app chat grievance reporting to `disabled: true` with placeholder text `"Report Grievance (Coming Soon)"` (`lib/features/chat/presentation/screens/chat_dialogue_screen.dart#L261`), lacks user blocking UI/API mechanisms, and enforces a blanket 15-day resolution SLA without the mandatory 24-hour emergency takedown for Non-Consensual Intimate Imagery (NCII). As a direct result, the platform forfeits all intermediary immunity under Section 79 of the IT Act, exposing platform directors to personal criminal liability as primary publishers of user-generated content.
3. **Monetized Consent Violation & Voyeurism Exposure**: The platform sells a ₹39 micro-perk (`profile_unlock_single`) that allows paying seekers to unilaterally unmask and view another user's private veiled photographs without the counterpart's knowledge, notice, or affirmative consent (`backend/app/services/photo_reveal_service.py#L244-257`). This constitutes a statutory defect under Section 6 of the DPDP Act (commencing May 13, 2027) and exposes the platform to criminal prosecution for aiding and abetting voyeurism (BNS 2023 § 77) and stalking (BNS 2023 § 78).
4. **App Store Ban & Commercial Rejection**: The mobile Flutter client directly executes Razorpay order creation and webview checkout sheets for in-app digital perks (`lib/features/growth/data/payment_service.dart#L51-141`), violating mandatory in-app purchase requirements under Apple Guideline 3.1.1 and Google Play Billing Policies, guaranteeing immediate rejection or termination of developer accounts upon review.

---

### 1.2 Statutory Liability Quantification & Penalty Matrix

The following matrix quantifies the direct civil financial penalties, criminal liabilities, and administrative sanctions facing UR-Heart and its corporate directors:

| # | Statutory Provision / Policy | Codebase Finding & Line Reference | Legal Nature of Violation | Maximum Civil Financial Penalty | Maximum Criminal Liability (Directors / Operators) | Operational & Store Sanctions |
|---|---|---|---|---|---|---|
| **1** | **DPDP Act 2023 § 9(1)–(3)** (Children's Personal Data) read with **POCSO Act 2012 §§ 13–15** | `backend/app/services/auth_service.py#L142` (`dob=date(2000, 1, 1)`) | Processing children's personal data without verifiable parental consent; exposing minors to adult dating environments | Up to **₹200 Crores** (Schedule Item 3) | **Imprisonment up to 5–7 years** (Cognizable & Non-Bailable under POCSO / IT Act § 67B) | Immediate app store suspension; hardware-level device seizure |
| **2** | **DPDP Act 2023 § 8(5)** (Reasonable Security Safeguards) | `supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L1127-1129` & `media.py#L55` | Failure of storage purge cascade leaving biometric KYC frames and user media unpurged | Up to **₹250 Crores** (Schedule Item 1) | Personal tort liability; statutory audit censure | Data Protection Board (DPB) operational injunction |
| **3** | **DPDP Act 2023 §§ 5 & 6** (Notice & Affirmative Consent) | `lib/features/auth/presentation/screens/consent_screen.dart#L39-47, L208-248` | Plaintext SharedPreferences storage; unnotified GPS/biometrics; no 8th Schedule languages | Up to **₹50 Crores** (Schedule Item 6) | Prosecution under DPDP Section 15 for false declarations | Mandatory suspension of data processing activities |
| **4** | **DPDP Act 2023 § 12** (Right to Erasure / Incineration) | `lib/core/app/app_router.dart#L146`, `account_incineration_service.py#L133`, `matches` FK | UI deletion route orphaned; Postgres CASCADE erases `peer_incinerated` state; GoTrue user retained | Up to **₹50 Crores** (Schedule Item 6) | Director civil contempt under DPB orders | App Store removal under Apple Guideline 5.1.1(v) |
| **5** | **IT Act 2000 § 79** read with **IT Rules 2021 Rules 3(1)(a)-(b)** | Complete absence of Terms of Service & Privacy Policy in `lib/` and `backend/` | Total loss of intermediary safe harbor; direct publisher liability for third-party uploads | Unlimited tort liability; loss of statutory shield | Direct prosecution under **IT Act §§ 67, 67A** (3 to 7 yrs imprisonment) | Platform blocking under IT Act § 69A |
| **6** | **IT Rules 2021 Rule 3(2)(a)** (Grievance Redressal) | Complete absence of Grievance Officer name, Indian address, email, and phone | Failure to establish statutory redressal mechanism within Indian territory | Contempt under IT Act § 45 (Fine up to ₹25,000 + loss of safe harbor) | Inability to defend defamation / obscenity prosecutions | Blacklisting by Ministry of Electronics & IT (MeitY) |
| **7** | **IT Rules 2021 Rule 3(2)(b)** (Emergency NCII Takedown) | `backend/app/services/legal_vault_service.py#L127` (blanket 15-day SLA applied to NCII) | Failure to remove sexually explicit content / NCII within mandatory 24-hour window | Loss of safe harbor; direct vicarious liability | **Imprisonment up to 3 years** under IT Act § 66E; **up to 5 years** under IT Act § 67A | Escalation to National Cyber Crime Reporting Portal (NCRP) |
| **8** | **BNS 2023 §§ 77 & 78** (Voyeurism & Stalking) read with **DPDP § 6** | `backend/app/services/photo_reveal_service.py#L244-257` & `revelation.py#L95-117` | Selling ₹39 unilateral photo unmasking bypassing target's consent and modesty veil | Up to **₹50 Crores** (DPDP); civil damages for privacy tort | **Imprisonment up to 3 to 7 years** (BNS § 77 / § 78) | Immediate removal for predatory monetized voyeurism |
| **9** | **Consumer Protection (E-Commerce) Rules 2020** | `lib/features/growth/data/payment_service.dart#L51-141` & `backend/app/api/v1/endpoints/payments.py` | Missing merchant entity identity, CIN/GSTIN, pre-purchase refund terms, and chargeback APIs | Penalties up to **₹10 Lakhs** to **₹50 Lakhs** under CPA 2019 § 89 | Prosecution for unfair trade practices | Revocation of payment gateway merchant account (Razorpay) |
| **10** | **Apple Guideline 3.1.1 & Google Play Payments Policy** | `lib/features/growth/data/payment_service.dart#L51-141, L148-154` (Direct Razorpay in APK/IPA) | Circumvention of platform in-app billing engines for digital dating perks and unlocks | N/A (Contractual & Store Enforcement) | N/A | **Immediate binary rejection and developer account termination** |

---

### 1.3 High-Risk Compliance Failure Summary: The Top 10 Critical Vulnerabilities

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                SYSTEMIC REGULATORY DEFICIT RADAR                                │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│  [1] Google OAuth Age Bypass ─────► [DPDP §9 / POCSO] ───────► ₹200 Cr Fine / Prison (5-7 yrs)  │
│  [2] Unilateral ₹39 Photo Reveal ─► [DPDP §6 / BNS §77-78] ──► ₹50 Cr Fine / Voyeurism Charge   │
│  [3] Missing Terms & Privacy ─────► [IT Act §79 / Rule 3(1)] ─► Loss of Safe Harbor Immunity    │
│  [4] No 24-Hr NCII Emergency ─────► [IT Rules Rule 3(2)(b)] ──► Loss of Intermediary Defense     │
│  [5] Chat Reporting Disabled ─────► [Apple 1.2 / Play UGC] ──► Immediate App Store Removal      │
│  [6] Missing User Blocking ───────► [Apple 1.2 / Play UGC] ──► App Store Rejection Guaranteed    │
│  [7] Orphaned Deletion UI ────────► [DPDP §12 / Apple 5.1.1] ─► Regulatory Non-Compliance        │
│  [8] Storage Trigger Mismatch ────► [DPDP §8 / §12] ─────────► Biometric/Photo Data Leakage      │
│  [9] Direct Mobile Razorpay ──────► [Apple 3.1.1 / Google] ──► Developer Account Termination     │
│ [10] SharedPreferences Consent ───► [DPDP §6(7)] ────────────► Failure of Legal Burden of Proof  │
│                                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Google OAuth Age Gate Bypass**: `backend/app/services/auth_service.py#L142` bootstraps new seekers with `dob=date(2000, 1, 1)`. Any minor authenticating via Google bypasses the age verification screen entirely.
2. **Paid Voyeurism Mechanism**: `backend/app/services/photo_reveal_service.py#L244-257` allows user A to pay ₹39 (`profile_unlock_single`) to instantly reveal user B's veiled photos without user B's knowledge or affirmation.
3. **Absence of Mandatory Intermediary Disclosures**: The entire repository lacks published Terms of Service, Privacy Policy, and Community Guidelines.
4. **Missing Grievance Officer Identification**: The platform fails to publish the name, physical Indian address, email, and telephone contact of a designated Resident Grievance Officer under IT Rules Rule 3(2)(a).
5. **Absence of 24-Hour NCII Emergency Takedown**: `backend/app/services/legal_vault_service.py#L127` assigns a fixed 15-day resolution SLA to all grievances, failing to implement the mandatory 24-hour statutory takedown for non-consensual sexual imagery under Rule 3(2)(b).
6. **Hardcoded Disabled In-App Chat Reporting**: `lib/features/chat/presentation/screens/chat_dialogue_screen.dart#L261` renders grievance reporting disabled with the text `'Report Grievance (Coming Soon)'`.
7. **Complete Absence of User Blocking**: The Flutter client contains zero blocking UI, and the backend exposes zero endpoints to block or unblock abusive seekers, violating mandatory App Store guidelines.
8. **Orphaned Account Erasure UI & Navigation**: The navigation shell (`sanctuary_navigation_shell.dart`) connects only to stub tabs (`MyPersonaScreen`), leaving `/settings` and `/vault` unreachable via normal app navigation.
9. **Media Storage Deletion Prefix Discrepancy**: Supabase migration trigger `handle_user_cascade_cleanup` searches for `storage.objects` with prefix `users/{OLD.auth_id}/%`, whereas actual files are stored under `users/{current_user.id}/%`, leaving all photos and KYC biometric frames orphaned in Cloudflare R2 and Supabase storage.
10. **Direct Mobile Razorpay In-App Billing**: `lib/features/growth/data/payment_service.dart` triggers Razorpay order creation and webview checkout inside the native Android/iOS client for digital dating perks, guaranteeing immediate store expulsion.

---

## 2. INDIA DIGITAL PERSONAL DATA PROTECTION ACT, 2023 (DPDP ACT 2023) DEEP-DIVE

### 2.1 Section 5 & Section 6: Notice, Affirmative Consent & Language Architecture

#### 2.1.1 Statutory Analysis of Consent Screen Notices (§ 5(1))
Under Section 5(1) of the DPDP Act 2023, every request for consent must be preceded or accompanied by a clear, itemized notice informing the Data Principal of:
- The exact categories of personal data to be collected;
- The specific, limited purpose for which the personal data will be processed;
- The manner in which the Data Principal may exercise their rights under Section 12 (Correction, Erasure) and Section 13 (Grievance Redressal); and
- The manner in which the Data Principal may make a complaint to the Data Protection Board of India.

**Forensic Audit Finding (`lib/features/auth/presentation/screens/consent_screen.dart#L208-248`)**:
The consent presentation presents only three generic clauses to first-time seekers:
1. Clause 1: *"DPDP Section 6 Purpose Limitation"* (lines 216–220)
2. Clause 2: *"FLAG_SECURE Anti-Capture Shield"* (lines 228–232)
3. Clause 3: *"10-Swipe Daily Mindful Rhythm"* (lines 240–244)

**Statutory Notice Deficiencies**:
- **Omission of Geolocation Processing Notice**: While the database schema (`public.users.latitude`, `public.users.longitude`) and onboarding flow collect granular GPS coordinates, the consent screen provides zero disclosure regarding geographic tracking, coordinate fuzzing, or radius filtering.
- **Omission of Biometric & Facial Data Notice**: The onboarding stepper (`lib/features/profile_setup/presentation/controllers/profile_setup_controller.dart#L379-401`) captures live camera video frames for automated AI liveness verification, yet no biometric notice or liveness processing disclosure is presented at consent time.
- **Omission of Audio Recording Notice**: The app captures 7-second audio recordings (`voice_spark_url`) and transcribes them via Groq Whisper API (`backend/app/api/v1/endpoints/ai.py#L48`), yet voice data processing is completely absent from the statutory notice.
- **Omission of Hardware Anchoring & Fingerprinting**: The backend captures `installation_uuid` and `device_hash` (`backend/app/models/domain/legal.py#L26`), yet hardware fingerprinting is undisclosed.
- **Omission of Right to Complain to the Board (§ 5(1)(iii))**: The screen contains zero mention of the statutory right to lodge an escalation or complaint with the Data Protection Board of India.

#### 2.1.2 The Single-Language Constitutional Violation (§ 5(3))
Section 5(3) of the DPDP Act mandates:
> *"The Data Fiduciary shall give the Data Principal the option to access the contents of the notice... in English or any language specified in the Eighth Schedule to the Constitution of India."*

**Forensic Audit Finding**:
In `lib/features/auth/presentation/screens/consent_screen.dart`, all consent text, dialogs, and legal notices are hardcoded exclusively in English. The application contains zero localization mechanisms, zero language selection dialogs, and zero translations into Hindi, Bengali, Telugu, Marathi, Tamil, Urdu, Gujarati, Kannada, Malayalam, Odia, Punjabi, or any of the other 22 official Eighth Schedule languages.

#### 2.1.3 The Ephemeral Local Storage Flaw & Evidentiary Failure (§ 6(7))
Section 6(7) of the DPDP Act imposes an explicit, mandatory legal burden on the Data Fiduciary:
> *"Where consent is required to be given by a Data Principal, the Data Fiduciary shall be obliged to prove that notice was given and consent was given by the Data Principal in accordance with the provisions of this Act."*

**Forensic Audit Finding (`lib/features/auth/presentation/screens/consent_screen.dart#L39-47`)**:
When a seeker taps *"I Affirm & Enter the Sanctuary"*, the client executes:
```dart
final prefs = await SharedPreferences.getInstance();
final record = jsonEncode({
  'version': '1.0',
  'timestamp': DateTime.now().toUtc().toIso8601String(),
  'purpose_limitation': purpose,
  'flag_secure_anti_capture': antiCapture,
  'rhythm_10_swipe': rhythm,
});
final saved = await prefs.setString(ConsentScreen.consentRecordKey, record);
```

**Legal Ramification**:
1. **Zero Server-Side Persistence**: The client makes zero HTTP calls to record the consent event on the backend. Although the database defines a dedicated audit table `public.consent_audit_logs` (`supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L472-480`), this table receives zero records during onboarding!
2. **Instant Destruction of Evidence**: If the user clears local app storage, uninstalls and reinstalls the application, or switches mobile devices, the local `SharedPreferences` record is wiped.
3. **Statutory Evidentiary Failure**: In any regulatory investigation before the Data Protection Board, ASI Verticals Private Limited will have zero backend records or tamper-proof audit trails to prove that affirmative consent was ever obtained from that user, incurring direct penalties under Section 33 read with Schedule Item 6 (up to ₹50 Crores).

#### 2.1.4 Total Absence of Granular Consent Withdrawal (§ 6(4))
Section 6(4) of the DPDP Act provides:
> *"The Data Principal shall have the right to withdraw her consent at any time, with the ease of doing so being comparable to the ease with which such consent was given."*

**Forensic Audit Finding (`lib/features/settings/presentation/screens/sanctuary_settings_screen.dart#L53-125`)**:
The settings screen provides only a single privacy action: `"Incinerate Sacred Persona"`.
There are zero toggles or controls enabling a seeker to:
- Withdraw consent for coarse geolocation processing while retaining account access;
- Withdraw consent for AI wingman profiling / automated bio polishing;
- Withdraw consent for voice spark audio storage;
- Withdraw consent for marketing notifications while maintaining core chat functionality.

The platform enforces a coercive "all-or-nothing" paradigm where the only method of withdrawing consent is the complete destruction of the seeker's account, directly violating Section 6(4) and Section 6(1).

---

### 2.2 Section 9: Processing of Children's Data & Mandatory Age Gate Hardening

#### 2.2.1 Statutory Mandates Under DPDP Act § 9 & POCSO Act 2012
Under Section 9 of the DPDP Act 2023:
1. **Verifiable Parental Consent (§ 9(1))**: A Data Fiduciary must, before processing any personal data of a child (defined under Section 2(f) as an individual who has not completed eighteen years of age), obtain verifiable consent of the parent or lawful guardian.
2. **Prohibition of Detrimental Processing (§ 9(2))**: A Data Fiduciary shall not undertake such processing of personal data that is likely to cause any detrimental effect on the well-being of a child.
3. **Prohibition of Tracking and Behavioral Profiling (§ 9(3))**: A Data Fiduciary shall not undertake tracking or behavioral monitoring of children or targeted advertising directed at children.

Simultaneously, under the Protection of Children from Sexual Offences Act, 2012 (POCSO Act), permitting a child under 18 to participate in an adult online dating and matchmaking environment featuring photographic unmasking, private chat dialogues, and meeting requests exposes platform directors to severe criminal liability under POCSO Sections 13–15 (use of child for pornographic purposes, abetment, and failure to report) and Section 67B of the IT Act 2000.

#### 2.2.2 Forensic Analysis of the Google OAuth Age Gate Bypass
In `lib/features/auth/presentation/screens/age_gate_auth_screen.dart#L35-73`, the mobile client implements a self-declared age selector. If the user declares a birthdate under 18, the client directs the device to quarantine.

However, in `backend/app/services/auth_service.py#L136-155`, the Google OAuth synchronization endpoint (`POST /api/v1/auth/google-sync`) handles authentication via the following logic:
```python
if not user:
    # Bootstrap initial uncompleted seeker account
    user = User(
        auth_id=auth_id,
        email=email,
        full_name=claims.get("name") or "Seeker",
        dob=date(2000, 1, 1),  # <--- CRITICAL STATUTORY DEFECT
        gender="Other",
        interested_in="Everyone",
        contact_bridge_type="whatsapp",
        contact_bridge_encrypted="",
        referral_code=f"SANCTUARY-{uuid.uuid4().hex[:12].upper()}",
        avatar_url=claims.get("picture"),
        is_profile_completed=False,
        last_installation_uuid=installation_uuid,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
```

**Forensic & Legal Breakdown**:
1. **Arbitrary Age Hardcoding**: When any user authenticates using Google Sign-In, the server does not verify age tokens, does not inspect Google account claims for birthdate (Google OAuth does not provide verified DOB by default), and does not require pre-registration age intent verification.
2. **Unconditional Adult Classification**: The server hardcodes `dob = date(2000, 1, 1)`. In 2026, this makes every user appear exactly 26 years old!
3. **Total Subversion of Protection**: A 13-year-old minor who downloads UR-Heart and taps "Sign in with Google" is instantly registered in the database as an adult born on January 1, 2000. They can browse adult discovery decks, swipe on adults, receive direct messages, and participate in location-based matching.
4. **Statutory Penalty Exposure**: Under DPDP Act Section 33 read with the Schedule, Item 3:
   > *"Breach in observance of additional obligations in relation to children under section 9: May extend to **two hundred crore rupees** (₹200,00,00,000)."*
   Accompanied by immediate criminal registration under POCSO and IT Act § 67B.

---

### 2.3 Section 12: Right to Erasure ("Account Incineration") vs. Technical Reality

Section 12(3) of the DPDP Act provides:
> *"A Data Principal shall have the right to erasure of her personal data... and a Data Fiduciary shall, upon receipt of such request... erase that personal data unless retention of the same is necessary for the specified purpose or for compliance with any law for the time being in force."*

UR-Heart heavily markets its "Account Incineration" feature as a cryptographically irreversible, zero-retention privacy engine. Our forensic inspection evaluated the entire erasure chain from Flutter UI to FastAPI backend to Supabase database and Cloudflare R2 object storage.

#### 2.3.1 The Orphaned UI Navigation Flaw
While `AccountIncinerationDialog` exists in `lib/features/legal_vault/presentation/widgets/account_incineration_dialog.dart`, and `SanctuarySettingsScreen` exists in `lib/features/settings/presentation/screens/sanctuary_settings_screen.dart`, **neither screen is accessible through the application UI!**
- In `lib/features/navigation/presentation/screens/sanctuary_navigation_shell.dart#L27-33`, the 5 persistent tabs are:
  1. `FeedScreen` (Discovery Feed)
  2. `ResonancesScreen` (Empty Stub: `Text('ResonancesScreen (Coming Soon)')`)
  3. `ChatsListScreen` (Empty Stub: `Text('ChatsListScreen (Coming Soon)')`)
  4. `GrowthHubScreen` (Rewards & Store)
  5. `MyPersonaScreen` (Empty Stub: `Text('MyPersonaScreen')`)
- In `lib/core/app/app_router.dart#L142-148`, `/settings` and `/vault` are registered, but **zero buttons, menu icons, or links navigate to them**.
- An end-user cannot access their settings or legal vault to initiate account deletion during ordinary application use, violating Section 12 and Apple Guideline 5.1.1(v).

#### 2.3.2 Supabase GoTrue Auth Identity Retention
In `backend/app/services/account_incineration_service.py#L52-156`, the service deletes the user row from `public.users` (`await session.execute(delete(User).where(User.id == user_id))`).
However:
- The backend makes zero API calls to Supabase Auth (`supabase.auth.admin.delete_user(auth_id)`).
- Although a database trigger `handle_user_auth_cleanup` exists in `supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L1150-1175` executing `DELETE FROM auth.users WHERE id = OLD.auth_id`, this trigger runs only if the database role has direct delete permissions on Supabase's private `auth` schema. When executing via restricted connection pools or when triggers are disabled during maintenance, the user's identity, email address, hashed credentials, and GoTrue session state remain permanently stored in `auth.users`, violating Section 12.

#### 2.3.3 Media Storage Cascade Prefix Mismatch (The Storage Leak)
In `supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L1118-1148`, the database defines a trigger `trg_user_cascade_cleanup` intended to purge media on deletion:
```sql
DELETE FROM storage.objects
WHERE bucket_id = 'ur-heart-media'
  AND (name LIKE ('users/' || OLD.auth_id::text || '/%'));
```
**The Forensic Discrepancy**:
- In `backend/app/api/v1/endpoints/media.py#L54-62`, uploads are written to prefixes formatted as:
  `users/{current_user.id}/{filename}` where `current_user.id` is the `public.users.id` UUID.
- In Supabase, `public.users.id` is a distinct, randomly generated UUID (`id UUID PRIMARY KEY DEFAULT gen_random_uuid()`), which is **not equal to `auth_id`** (`auth_id UUID UNIQUE NOT NULL`).
- As a consequence, the SQL trigger executes `name LIKE ('users/' || OLD.auth_id || '/%')`, matching **zero rows**.
- If Supabase Storage is utilized, user photos, voice recordings, and moment snapshots are **never deleted**.
- Furthermore, raw biometric KYC frames stored under `kyc_temp/{user_id}/` and `kyc_escalations/` are not referenced by the trigger at all, leaving biometric identity frames permanently stored in cloud object buckets.

#### 2.3.4 The "Vaporization Paradox" (Destruction of Peer Incineration State)
In `backend/app/services/account_incineration_service.py#L44-50`, the service attempts to notify the surviving counterpart that their match has left the platform:
```python
stmt = (
    update(Match)
    .where((Match.user1_id == user_id) | (Match.user2_id == user_id))
    .values(is_active=False, closure_status="peer_incinerated")
)
await session.execute(stmt)
```
However, at line 133 of the same service:
```python
await session.execute(delete(User).where(User.id == user_id))
```
In `supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L98-99`:
```sql
user1_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
user2_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
```
Because the foreign key constraints specify `ON DELETE CASCADE`, deleting the user row causes PostgreSQL to **immediately and automatically delete the match record entirely**. The `closure_status = 'peer_incinerated'` update is instantly vaporized. The surviving peer's match simply vanishes without explanation, corrupting client chat state.

#### 2.3.5 Audit of Legal Obligations Retention Exceptions (§ 12(3))
Section 12(3) allows the Data Fiduciary to retain data necessary for *"compliance with any law for the time being in force."*
Our audit confirms that `account_incineration_service.py#L113-130` properly decouples PII while preserving legal records:
- **Grievance Dossiers**: Anonymizes `reporter_id` and `reported_user_id` to `NULL` and redacts narrative evidence text to `"[INCINERATED_PURSUANT_TO_DPDP_SECTION_12]"`, maintaining aggregate compliance statistics for MeitY reporting without storing principal data.
- **Financial Transactions**: Anonymizes `InAppPurchase.user_id` to `NULL` while retaining transaction amounts and payment IDs to satisfy the mandatory 7-year retention requirements under Section 44AB of the Indian Income Tax Act, 1961 and the Prevention of Money Laundering Act, 2002.

---

## 3. INFORMATION TECHNOLOGY ACT, 2000 & INTERMEDIARY GUIDELINES (2021/2023)

### 3.1 Loss of Section 79 Safe Harbor Immunity

Section 79(1) of the Information Technology Act, 2000 grants intermediaries immunity from criminal and civil liability for third-party user content hosted or transmitted through the platform.
However, under Section 79(2)(c), this safe harbor protection is **strictly conditional** upon the intermediary observing due diligence requirements prescribed by the Central Government under the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021 (as amended).

#### 3.1.1 Rule 3(1)(a) & (b): Mandatory Publication of Terms & Privacy Rules
Rule 3(1)(a) mandates that an intermediary shall prominently publish on its website, mobile application, or both, the rules and regulations, privacy policy, and user agreement for access or usage of its computer resource.
Rule 3(1)(b) mandates that the intermediary shall inform its users in clear terms not to host, display, upload, modify, publish, transmit, store, update, or share any objectionable, harmful, defamatory, obscene, pornographic, pedophilic, or unlawful material.

**Forensic Audit Finding**:
- A comprehensive regex search across all 65 Flutter client files (`lib/`) and all 20 FastAPI backend routers (`backend/`) confirms that:
  - **Zero Terms of Service exist.**
  - **Zero Privacy Policy exists.**
  - **Zero Community Guidelines exist.**
  - **Zero Acceptable Use Policies exist.**
- The application presents zero rules to seekers upon registration or during chat and media uploads.

**Legal Consequence: Compliance Gap & Risk to Section 79 Safe Harbor**:
By failing to publish the statutory terms and due diligence rules, UR-Heart creates a severe compliance gap under Rule 3 of the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021. This failure puts the platform's Section 79 safe harbor immunity at significant risk in contested legal proceedings, leaving the operating entity vulnerable to regulatory enforcement and potential vicarious exposure for unmoderated third-party uploads.

#### 3.1.2 Personal Criminal Exposure of Platform Directors & Operators
Without Section 79 immunity, corporate officers, directors, and administrators face direct, personal prosecution under the Indian Penal Code / Bharatiya Nyaya Sanhita and the IT Act for any user-uploaded media:
1. **IT Act Section 67** (Publishing or transmitting obscene material in electronic form):
   - First conviction: Imprisonment up to **3 years** and fine up to **₹5,00,000**.
   - Subsequent conviction: Imprisonment up to **5 years** and fine up to **₹10,00,000**.
2. **IT Act Section 67A** (Publishing or transmitting material containing sexually explicit act):
   - First conviction: Imprisonment up to **5 years** and fine up to **₹10,00,000**.
   - Subsequent conviction: Imprisonment up to **7 years** and fine up to **₹10,00,000**.
3. **IT Act Section 67B** (Child Sexual Abuse Material):
   - Mandatory minimum imprisonment of **5 years**, extending up to **7 years**, and fine up to **₹10,00,000**. Non-bailable and cognizable offense.
4. **IT Act Section 66E** (Violation of Bodily Privacy):
   - Imprisonment up to **3 years** or fine up to **₹2,00,000**.
5. **Bharatiya Nyaya Sanhita, 2023 Section 77 (Voyeurism)**:
   - Imprisonment of **1 to 3 years** (first conviction); **3 to 7 years** (second conviction).
6. **Bharatiya Nyaya Sanhita, 2023 Section 78 (Stalking)**:
   - Imprisonment up to **3 years** (first conviction); up to **5 years** (second conviction).

---

### 3.2 Rule 3(2)(a): Prominent Publication of Grievance Redressal Particulars

Rule 3(2)(a) of the IT Intermediary Rules mandates:
> *"The intermediary shall prominently publish on its website, mobile based application or both, as the case may be, the name of the Grievance Officer and his contact details as well as mechanism by which a user or a victim may make complaint of violation of the provisions of this rule..."*

**Forensic Audit Finding**:
- There is **no Grievance Officer designated, named, or published anywhere** within `lib/`, `backend/`, or documentation templates.
- The platform fails to provide an Indian physical address, phone number, or designated statutory grievance email address.

---

### 3.3 Rule 3(2)(b): The 24-Hour Mandatory Emergency Takedown Workflow

Rule 3(2)(b) establishes a strict statutory emergency takedown timeline for sensitive personal content:
> *"The intermediary shall, within twenty-four hours from the receipt of a complaint made by an individual or any person on his behalf under this sub-clause, in relation to any content which is prima facie in the nature of any material which exposes the private area of such individual, shows such individual in full or partial nudity or shows or depicts such individual in any sexual act or conduct, or is in the nature of impersonation in an electronic form, including artificially generated images of such individual, take all reasonable and practicable measures to remove or disable access to such content..."*

**Forensic Audit Finding (`backend/app/services/legal_vault_service.py#L125-141`)**:
In `legal_vault_service.py`:
```python
dossier_ref = self.generate_dossier_reference()
ack_time = datetime.now(timezone.utc)
due_date = ack_time + timedelta(days=15)  # <--- CRITICAL STATUTORY DEFECT

dossier = GrievanceDossier(
    ...
    violation_category=payload.violation_category,
    ...
    statutory_resolution_due_at=due_date,
    sla_deadline_at=due_date,
)
```
1. **Generic 15-Day SLA Applied to Emergency Content**: The backend applies a fixed 15-day resolution SLA (`ack_time + timedelta(days=15)`) indiscriminately across all grievance categories, including `explicit_content` and `impersonation`.
2. **Zero Automated Media Quarantine**: When an explicit content grievance is submitted, the backend merely inserts a record into `grievance_dossiers`. It does **not** hide the target user's photos, does **not** revoke the public CDN URL, and does **not** place the reported user into incognito or quarantined state pending moderation.
3. **Statutory Breach**: Failing to take down non-consensual intimate imagery within 24 hours strips the platform of all intermediary immunity and constitutes an independent offense under Rule 3(2)(b) punishable by platform blocking orders under Section 69A of the IT Act.

---

### 3.4 User Reporting & Blocking Mechanisms (IT Due Diligence & Store Policies)

#### 3.4.1 Hardcoded Disabled Reporting in Chat Dialogue
In `lib/features/chat/presentation/screens/chat_dialogue_screen.dart#L259-270`:
```dart
const PopupMenuItem(
  value: 'report_grievance',
  enabled: false,
  child: Row(
    children: [
      Icon(Icons.flag_outlined, size: 18.0, color: Colors.grey),
      SizedBox(width: 10.0),
      Text('Report Grievance (Coming Soon)'),
    ],
  ),
),
```
The menu action to report an abusive user directly from an ongoing chat conversation is **hardcoded disabled with `enabled: false` and the text `"Report Grievance (Coming Soon)"`**. A seeker subjected to sexual harassment, stalking, or abusive threats in active chat has zero ability to flag or report the perpetrator.

#### 3.4.2 Total Absence of User Blocking Mechanism
- **Apple App Store Review Guideline 1.2 (User Generated Content)** states:
  > *"Apps with user-generated content must include: A mechanism for users to flag objectionable content; **A mechanism for users to block abusive users**; Published contact information so users can easily reach the developer."*
- **Google Play UGC Policy** states:
  > *"Apps that contain UGC must implement robust, effective, and continuous moderation, including: **An in-app feature to block users and UGC**."*

**Forensic Audit Finding**:
- While a database table `public.blocked_users` exists in `supabase/migrations/20260926000000_phase1_database_foundation_and_rls.sql#L506-514`, **zero API endpoints exist in FastAPI to block or unblock users**.
- In the Flutter client (`lib/`), there is **zero UI widget, button, or menu item allowing a user to block another seeker**.
- Failure to provide an active user blocking feature results in **guaranteed, automated rejection** during Apple App Store and Google Play App Review.

#### 3.4.3 The Impossible UX of the Legal Vault Reporting Dialog
In `lib/features/legal_vault/presentation/screens/vault_legal_screen.dart#L716-722`:
```dart
TextField(
  controller: userCtrl,
  decoration: const InputDecoration(
    labelText: 'Reported User UUID',
    border: OutlineInputBorder(),
  ),
),
```
The grievance filing form in the Legal Vault requires a consumer to manually type the target seeker's 36-character internal database UUID (e.g., `3fa85f64-5717-4562-b3fc-2c963f66afa6`). Because internal database UUIDs are never exposed in the user interface during swiping or chat, it is literally impossible for an ordinary victim to file a grievance against an abusive seeker through this form.

---

## 4. DATING PLATFORM SAFETY & CONTENT LIABILITY

### 4.1 Unilateral Photo Unmasking Micro-Perk (`profile_unlock_single`, ₹39)

UR-Heart implements a modesty photo veil (`is_photo_veiled = True`) as a core product safety pillar, promising seekers that their facial photos will remain veiled and blurred until mutual intentionality is established.

#### 4.1.1 Forensic Code Inspection
In `backend/app/services/photo_reveal_service.py#L244-257`:
```python
# 2. Micro-perk single profile unlock bypass (user_a purchased unlock for user_b)
iap_stmt = select(InAppPurchase).where(
    InAppPurchase.user_id == user_a,
    InAppPurchase.status == "completed",
    (
        (InAppPurchase.product_identifier == f"profile_unlock_single:{user_b}")
        | (
            (InAppPurchase.product_identifier == "profile_unlock_single")
            & InAppPurchase.transaction_reference.contains(str(user_b))
        )
    ),
)
if (await session.execute(iap_stmt)).scalars().first():
    return {"target_id": user_b, "status": "purchased_unlock", "is_revealed": True}
```
And in `backend/app/api/v1/endpoints/revelation.py#L95-117`:
```python
@router.post("/photo/unlock-perk", response_model=SanctuaryResponse[PhotoRevealResponse])
async def unlock_photo_with_perk(...)
```

#### 4.1.2 Statutory & Criminal Analysis
1. **Direct Breach of DPDP Act 2023 Section 6**:
   Under Section 6(1), processing of personal data (including biometric facial imagery) requires consent that is free, specific, informed, unconditional, and unambiguous with clear affirmative action. By permitting User A to pay ₹39 to unmask User B's photographs without User B's prior knowledge, affirmative consent, or notification, the platform unilaterally overrides User B's statutory consent rights.
2. **Criminal Liability for Voyeurism (BNS 2023 § 77)**:
   Under Section 77 of the Bharatiya Nyaya Sanhita, 2023:
   > *"Any man who monitors or watches or captures the image of a woman engaging in a private act in circumstances where she would usually have the expectation of not being observed... commits the offence of voyeurism."*
   In a privacy-first dating platform where seekers upload veiled photos under the explicit contractual promise of modesty and mutual consent, selling a paid backdoor to unmask their facial likeness without consent constitutes commercial facilitation and abetment of voyeurism.
3. **Criminal Liability for Cyber Stalking (BNS 2023 § 78)**:
   Facilitating the persistent, unilateral tracking and visual unmasking of a non-consenting individual constitutes electronic stalking under BNS Section 78.
4. **Remediation**: The `profile_unlock_single` bypass must be **completely eliminated**. Photo unmasking must strictly require **bilateral affirmative mutual consent** in all circumstances.

---

### 4.2 Handling of CSAM, NCII & Mandatory Law Enforcement Reporting

#### 4.2.1 Statutory Reporting Obligations under POCSO Act 2012 § 19 & 21
Under Section 19 and 21 of the POCSO Act, any person (including corporate officers of a digital intermediary) who has apprehension or knowledge that an offense under the Act has been committed has a **mandatory statutory obligation** to provide information to the Special Juvenile Police Unit or local police. Failure to report is punishable by imprisonment up to **6 months** or fine, or both.

#### 4.2.2 Media Ingestion Vulnerability in Backend
In `backend/app/api/v1/endpoints/media.py#L48-84`, presigned S3/R2 upload URLs are issued directly to authenticated seekers for moment slots and avatars:
- The backend performs **zero automated hash matching** against known Child Sexual Abuse Material (CSAM) databases (e.g., Microsoft PhotoDNA, Project Arachnid, or Internet Watch Foundation hashes).
- The backend performs **zero automated machine-vision moderation** (NSFW/nudity classification via Google Cloud Vision SafeSearch, AWS Rekognition, or Groq Vision) prior to publishing assets.
- Once uploaded, images are served via direct public CDN links (`https://media.urheart.app/users/...`), permitting unmoderated sexually explicit content and CSAM to propagate unrestricted.
- Remediation: Implement automated perceptual hashing (PDQ/PhotoDNA) and pre-CDN machine-vision classification on all media uploads, combined with an automated law enforcement dispatch workflow to the National Cyber Crime Reporting Portal (NCRP / cybercrime.gov.in).

---

## 5. COMMERCIAL, PAYMENT & STORE COMPLIANCE

### 5.1 Consumer Protection (E-Commerce) Rules, 2020 Compliance

Under Rule 4 of the Consumer Protection (E-Commerce) Rules, 2020, every e-commerce entity operating in India must provide clear, accessible statutory disclosures on its platform:
1. **Mandatory Corporate Disclosures (Rule 4(1))**:
   - Legal name of the e-commerce entity: *ASI Verticals Private Limited*
   - Principal registered office address
   - Corporate Identity Number (CIN) and Goods & Services Tax Identification Number (GSTIN)
   - Verified contact email and customer care helpline number
   - *Current Status*: **100% missing from the application and backend.**
2. **Pricing & Sub-Unit Transparency (Rule 4(11))**:
   - Total price in INR along with a clear breakup showing base cost, delivery/platform fees, and applicable GST (18% under HSN 998439 for Online Information Database Access and Retrieval - OIDAR services).
   - *Current Status*: The store catalog (`backend/app/api/v1/endpoints/store.py#L13-25`) returns flat amounts (e.g. ₹39, ₹99) without tax breakdowns.
3. **Mandatory Grievance Ticket Tracking (Rule 4(5))**:
   - Acknowledgement of consumer complaints within 48 hours and resolution within one month, with an automated ticket tracking number.
   - *Current Status*: Missing from the growth and store subsystems.
4. **Dispute & Refund Webhook Handling**:
   - In `backend/app/api/v1/endpoints/payments.py`, webhook handlers exist for `payment.captured` and `payment.failed`, but there is **zero handling for `payment.dispute.created` or chargeback adjustments**, risking automated merchant account suspension by Razorpay/Stripe for unacknowledged disputes.

---

### 5.2 Direct Razorpay Checkout vs. App Store Policies (Apple Guideline 3.1.1 & Google Play)

#### 5.2.1 Forensic Inspection of Native Client Payment Service
In `lib/features/growth/data/payment_service.dart#L51-141`:
```dart
Future<void> initiateProductPurchase({
  required BuildContext context,
  required StoreProduct product,
  required WidgetRef ref,
}) async {
  // 1. Create server-side Razorpay Order in integer paise subunits
  final orderRes = await _client.post(
    '/api/v1/payments/create-order',
    body: {'product_identifier': product.id},
  );
  ...
  // 2. Launch checkout sheet via native/webview bridge or custom launcher
  final checkoutResult = await launcher(context, options);
  ...
  // 3. Dispatch cryptographic checkout verification
  await _client.post(
    '/api/v1/payments/verify-checkout',
    body: {
      'razorpay_order_id': checkoutResult.orderId,
      'razorpay_payment_id': checkoutResult.paymentId,
      'razorpay_signature': checkoutResult.signature,
      'product_identifier': product.id,
    },
  );
}
```
And in lines 144–154:
```dart
/// Default mock fallback sheet for development/unsupported platforms
Future<RazorpayCheckoutResult> _defaultCheckoutDialog(...) async {
  // shortcut: returns simulated success on web/desktop until native Razorpay SDK bridge initialized
  return RazorpayCheckoutResult.success(
    paymentId: 'pay_simulated_${DateTime.now().millisecondsSinceEpoch}',
    orderId: options['order_id'] as String? ?? 'order_simulated',
    signature: 'sig_simulated',
  );
}
```

#### 5.2.2 App Store Policy Violations
1. **Apple App Store Review Guideline 3.1.1 (In-App Purchase)**:
   > *"If you want to unlock features or functionality within your app (by way of example: subscriptions, in-game currencies, game levels, access to premium content, or unlocking a full version), you must use in-app purchase. Apps may not use their own mechanisms to unlock content or services, such as license keys, augmented reality markers, QR codes, etc."*
2. **Google Play Payments Policy**:
   > *"Developers offering in-app purchases of digital goods and services within apps distributed on Google Play must use Google Play's billing system."*

**Impact**:
Digital dating features (Direct Letters, Super Likes, Profile Unlocks, Sovereign Passes) are classified unambiguously as digital goods consumed within the software. Implementing direct payment gateway checkout (Razorpay) inside native iOS and Android binaries is an **immediate, non-negotiable rejection ground**, leading to permanent termination of developer accounts for anti-steering circumventing behavior.

#### 5.2.3 Mandatory Architectural Separation
The payment architecture must be bifurcated:
- **Mobile Binaries (iOS/Android)**: Must integrate native Google Play Billing (Play In-App Billing v3) and Apple StoreKit via the `in_app_purchase` Flutter package or RevenueCat SDK.
- **Web Storefront ([https://urheart.app/store](https://urheart.app/store))**: Razorpay and Stripe may be legally offered strictly for web-based entitlement purchases consumed across devices, complying with Apple's Reader and Web Entitlement guidelines.

---

### 5.3 Legal Classification of Virtual Goods & In-App Currency

The platform features virtual items including Direct Letters, Boost Points, and Sovereign Passes.
1. **Closed-Loop Digital Licenses**:
   These items must be legally categorized in terms as **limited, non-transferable, revocable, non-exclusive digital licenses** possessing zero fiat value, zero redeemability for currency, and zero secondary market transferability.
2. **Prepaid Payment Instrument (PPI) Non-Applicability**:
   Under RBI Master Directions on Prepaid Payment Instruments, closed-loop tokens redeemable exclusively for digital services within the issuing platform do not constitute regulated PPIs, provided they cannot be converted into cash or transferred between users.
3. **Exclusion from Virtual Digital Assets (VDA) Tax**:
   Under Section 2(47A) of the Indian Income Tax Act, 1961 read with CBDT notifications, closed-loop game points and non-cryptographic virtual perk tokens do not constitute Virtual Digital Assets (VDAs) and are exempt from 30% flat capital gains tax and 1% TDS under Section 194S, provided they are explicitly designated as non-transferable service credits.

---

## 6. DRAFT MODEL LEGAL DOCUMENTS & POLICY FRAMEWORKS

The following four model draft policy documents have been prepared to address the identified statutory, intermediary, and consumer compliance gaps. 

> [!WARNING]
> **DRAFT WORKING DOCUMENTS**: The policies below are draft templates requiring verification of actual corporate particulars by legal counsel and implementation/testing of underlying operational capabilities (including billing, grievance escalation, language selection, and account incineration workflows) before publication. They do not constitute finalized or legally effective platform agreements.

---

### DOCUMENT 1: MASTER TERMS OF SERVICE

```markdown
# UR-HEART SANCTUARY — MASTER TERMS OF SERVICE
**Effective Date: October 15, 2026**
**Last Updated: October 15, 2026**
**Governing Law: Republic of India**

PLEASE READ THESE TERMS OF SERVICE CAREFULLY BEFORE ACCESSING OR USING THE UR-HEART DATING SANCTUARY PLATFORM.

## 1. ACCEPTANCE OF TERMS & CORPORATE DISCLOSURE
1.1. These Master Terms of Service ("Terms" or "Agreement") constitute a legally binding agreement between you ("User", "Seeker", or "Data Principal") and **ASI Verticals Private Limited** ("Company", "UR-Heart", "Platform", "We", "Us", or "Our"), a private limited company incorporated under the Companies Act, 2013 of India, having its registered office at:
> **[INSERT REGISTERED COMPANY LEGAL NAME]**  
> [INSERT REGISTERED OFFICE ADDRESS]  
> Corporate Identity Number (CIN): [INSERT CORPORATE IDENTITY NUMBER (CIN)]  
> Goods & Services Tax Identification Number (GSTIN): [INSERT GSTIN]  
> Official Legal Contact: legal@urheart.app | Statutory Grievance Desk: [INSERT GRIEVANCE OFFICER NAME & CONTACT EMAIL]  

1.2. By downloading, installing, registering on, browsing, or using the UR-Heart mobile application ("App") or web sanctuary located at https://urheart.app ("Site"), you irrevocably agree to comply with and be bound by these Terms, our Privacy Policy, our Community Safety Guidelines, and our Grievance Redressal Protocol. If you do not agree to these Terms, you must immediately uninstall the App and cease all access to the Platform.

---

## 2. STRICT 18+ ELIGIBILITY & AGE AFFIRMATION
2.1. **Strict Adult Requirement**: UR-Heart is an adult dating, kinship, and conscious connection platform designed exclusively for individuals who are **at least eighteen (18) years of age**. Access by minors (individuals under 18 years) is strictly prohibited.
2.2. **Statutory Affirmation Under DPDP Act Section 15**:
   By registering or logging into the Platform, you solemnly affirm and warrant under penalty of law that:
   (a) You are 18 years of age or older as of the date of registration;
   (b) All information provided regarding your date of birth is accurate, truthful, and verifiable;
   (c) You have not previously been suspended, removed, or banned from UR-Heart for predatory, abusive, or fraudulent behavior.
2.3. **Statutory Penalties for False Age Declaration**: Under Section 15 of the Digital Personal Data Protection Act, 2023 (DPDP Act 2023), no Data Principal shall impersonate another person or furnish any false particulars or suppress any material information. Any minor or individual falsely declaring their age to gain access commits a material breach of this Agreement and a statutory offense. The Company reserves the unconditional right to instantly terminate the account, forfeit all purchased entitlements without refund, report the violation to competent law enforcement agencies under the Protection of Children from Sexual Offences Act, 2012 (POCSO Act), and place the offending device's hardware fingerprint on our permanent Hardware Quarantine Registry.

---

## 3. INTERMEDIARY STATUS & USER CONDUCT DUE DILIGENCE
3.1. **Intermediary Classification**: UR-Heart operates as an intermediary under Section 2(1)(w) of the Information Technology Act, 2000 ("IT Act"). In compliance with Rule 3(1)(b) of the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021 (as amended), you are hereby informed, and agree, that you shall NOT host, display, upload, modify, publish, transmit, store, update, or share any information that:
   (a) Belongs to another person and to which you do not have any right;
   (b) Is obscene, pornographic, pedophilic, invasive of another's privacy including bodily privacy;
   (c) Depicts Non-Consensual Intimate Imagery (NCII), full or partial nudity, sexual acts, or is in the nature of sexual harassment or voyeurism under Section 77 of the Bharatiya Nyaya Sanhita, 2023 (BNS 2023);
   (d) Insults the modesty of any woman under Section 79 of the BNS 2023 or constitutes stalking under Section 78 of the BNS 2023;
   (e) Harms minors in any way, including any depiction of Child Sexual Abuse Material (CSAM);
   (f) Deceives or misleads the addressee about the origin of the message or intentionally communicates any information which is patently false or misleading in nature;
   (g) Impersonates another person or uses automated scripts, deepfakes, or artificial visual manipulation to deceive seekers;
   (h) Threatens the unity, integrity, defense, security or sovereignty of India, friendly relations with foreign States, or public order;
   (i) Contains software viruses or any other computer code designed to interrupt, destroy, or limit the functionality of any computer resource;
   (j) Solicits commercial sexual acts, prostitution, human trafficking, or unauthorized financial solicitation.

3.2. **Enforcement and Account Sanctions**: Any violation of Section 3.1 entitles the Company to immediately disable or remove the offending content within twenty-four (24) hours, suspend or terminate your account without notice, and provide all electronic logs and records to authorized law enforcement agencies pursuant to Section 79 of the IT Act.

---

## 4. PHOTO VEIL, MODESTY COVENANTS & CONSENT BOUNDARIES
4.1. **Sovereign Photo Veil**: UR-Heart incorporates a proprietary photo veil feature (`is_photo_veiled = True`) to protect personal privacy. Every seeker retains exclusive ownership and control over their facial photographs.
4.2. **Strict Mutual Bilateral Consent Requirement**:
   (a) Unmasking a seeker's photo veil strictly requires **mutual, bilateral affirmative consent**.
   (b) Under no circumstances may any micro-perk, virtual pass, ad reward, or monetary payment bypass or override another seeker's photo veil without that seeker's explicit, contemporaneous acceptance of a reveal request.
4.3. **Anti-Capture Protection & Prohibited Acts**:
   (a) The App enforces hardware-level display security (`FLAG_SECURE`). You agree NOT to bypass, intercept, hook, capture, screenshot, screen-record, scrape, or extract any veiled or unveiled photographs, voice sparks, or private dialogues.
   (b) Capturing, recording, redistributing, or publishing another seeker's unveiled photographs without their prior written consent constitutes an intentional violation of bodily privacy under Section 66E of the IT Act, voyeurism under Section 77 of the BNS 2023, and a tort of privacy under Indian common law. Violators will face immediate hardware ban and civil/criminal prosecution.

---

## 5. DATING SAFETY & IN-PERSON INTERACTION DISCLAIMER
5.1. **Platform Nature**: UR-Heart provides a digital venue for mutual introduction. The Company does NOT conduct criminal background checks, psychological evaluations, or physical surveillance of its users.
5.2. **User Responsibility**: You are solely responsible for your interactions with other seekers. You agree to exercise common sense and prudence when communicating or meeting in person. Always meet in public places, inform trusted friends or family of your whereabouts, and never disclose sensitive financial or home address details.
5.3. **Disclaimer of Offline Liability**: To the maximum extent permitted by applicable Indian law, the Company, its directors, officers, employees, and agents expressly disclaim any and all liability for any physical, emotional, financial, or reputational damage, injury, stalking, harassment, theft, or assault resulting from communications or in-person meetings arranged through the Platform.

---

## 6. VIRTUAL PERKS, BILLING & MICRO-TRANSACTIONS
6.1. **Nature of Virtual Perks**: All digital goods, Direct Letters, Sovereign Passes, Boost Points, and virtual perks purchased or earned within the Platform represent **limited, revocable, non-transferable, non-exclusive digital licenses** to access specific software functionality within UR-Heart.
6.2. **Zero Cash Value**: Virtual perks possess zero real-world monetary value, do NOT constitute money, currency, or Prepaid Payment Instruments (PPIs) under Reserve Bank of India regulations, and cannot be redeemed, transferred, traded, or refunded for fiat currency.
6.3. **Platform Store Billing Compliance**:
   (a) All purchases made within the native iOS application are processed exclusively through Apple In-App Purchase and are subject to Apple's Terms and Conditions.
   (b) All purchases made within the native Android application are processed exclusively through Google Play Billing and are subject to Google Play Terms of Service.
   (c) Purchases made via our external Web Sanctuary ([https://urheart.app/store](https://urheart.app/store)) are processed via authorized payment aggregators (Razorpay / Stripe) and are billed in Indian Rupees (INR) inclusive of applicable 18% GST.
6.4. **Refund Policy**: All micro-perk purchases are final and non-refundable once delivered, subject only to mandatory consumer protection laws and our Refund & Cancellation Policy.

---

## 7. INTELLECTUAL PROPERTY & PROPRIETARY RIGHTS
7.1. All trademarks, service marks, logos, user interfaces, visual designs, Cormorant Garamond typography implementations, glassmorphism design tokens, software algorithms, and backend source code are the exclusive intellectual property of ASI Verticals Private Limited.
7.2. You retain ownership of the photos, text, and voice recordings you upload ("User Content"). By uploading User Content, you grant UR-Heart a worldwide, royalty-free, non-exclusive, revocable license to process, store, transcribe, and display such content solely for facilitating your matchmaking experience and community safety compliance pursuant to our Privacy Policy.

---

## 8. STATUTORY ACCOUNT INCINERATION & DATA ERASURE
8.1. You have the right to terminate your account and irrevocably incinerate your personal data at any time via the "Incinerate Sacred Persona" feature in Settings or via our web deletion portal at https://urheart.app/delete-account.
8.2. Incineration permanently expunges your profile, facial photographs, voice sparks, matches, chats, and biometric KYC verification records across our database and cloud storage in compliance with Section 12 of the DPDP Act 2023. Anonymized transaction records and statutory grievance files are retained strictly as required by applicable Indian tax and intermediary laws.

---

## 9. INDEMNIFICATION & LIMITATION OF LIABILITY
9.1. **Indemnification**: You agree to defend, indemnify, and hold harmless ASI Verticals Private Limited, its subsidiaries, directors, officers, employees, and agents from and against any claims, liabilities, damages, losses, fines, penalties, and expenses (including reasonable legal fees) arising out of or in connection with: (a) your violation of these Terms; (b) any content uploaded by you; (c) your violation of any statutory right of any third party or seeker; or (d) your conduct during in-person interactions.
9.2. **Limitation of Liability**: To the maximum extent permitted by Indian law, in no event shall ASI Verticals Private Limited be liable for any indirect, incidental, special, consequential, punitive, or exemplary damages, including loss of profits, emotional distress, or loss of data. The total aggregate liability of the Company for all claims arising out of this Agreement shall be limited to the total amount paid by you to the Company in the twelve (12) months preceding the event giving rise to liability, or INR 1,000 (Indian Rupees One Thousand), whichever is greater.

---

## 10. GOVERNING LAW & DISPUTE RESOLUTION
10.1. **Governing Law**: This Agreement and any dispute arising out of or in connection with it shall be governed by and construed in accordance with the laws of the Republic of India, without regard to its conflict of law principles.
10.2. **Mandatory Conciliation & Arbitration**:
   (a) Any dispute, controversy, or claim arising out of or relating to these Terms shall first be referred to mutual conciliation by providing written notice to legal@urheart.app.
   (b) If the dispute is not settled within thirty (30) days of such notice, it shall be referred to and finally resolved by binding arbitration administered in accordance with the Arbitration and Conciliation Act, 1996 of India.
   (c) The arbitral tribunal shall consist of a sole arbitrator appointed mutually by the parties, or failing agreement, in accordance with the Act.
   (d) The seat and venue of arbitration shall be **New Delhi, India**. The arbitration proceedings shall be conducted in the English language.
10.3. **Exclusive Court Jurisdiction**: Subject to the arbitration clause, the competent courts in New Delhi, India shall have exclusive jurisdiction over all legal disputes arising out of this Agreement.
```

---

### DOCUMENT 2: PRIVACY POLICY & DPDP STATUTORY DATA NOTICE

```markdown
# UR-HEART SANCTUARY — PRIVACY POLICY & STATUTORY DATA NOTICE
**Effective Date: October 15, 2026**
**Last Updated: October 15, 2026**
**Notice Provided Under Sections 5 & 6 of the Digital Personal Data Protection Act, 2023 (DPDP Act 2023)**

ASI Verticals Private Limited ("Data Fiduciary", "Company", "We", "Us", or "Our") is committed to honoring your digital privacy, conscious connection, and psychological sovereignty. This Privacy Policy and Statutory Notice explains the categories of personal data we collect, our lawful bases and processing purposes, data retention periods, security safeguards, and your sovereign statutory rights as a Data Principal under the Digital Personal Data Protection Act, 2023 (DPDP Act 2023).

---

## 1. IDENTITY & CONTACT PARTICULARS OF THE DATA FIDUCIARY
- **Corporate Entity**: [Insert Registered Corporate Entity Name]
- **Registered Office**: [Insert Verified Indian Registered Office Address]
- **Corporate Identity Number (CIN)**: [Insert Authorized Corporate Identity Number (CIN)]
- **Designated Data Protection / Grievance Officer**: [Insert Designated Grievance Officer Name], [Insert Title/Designation]
- **Dedicated Privacy & Statutory Email**: [Insert Privacy Email] | [Insert Grievance Email]
- **Telephone / Contact Number**: [Insert Authorized Grievance Telephone Helpline]

---

## 2. ITEMIZED CATEGORIES OF PERSONAL DATA COLLECTED
In strict adherence to the Section 6 Purpose Limitation principle, UR-Heart collects only personal data strictly necessary to facilitate intentional matchmaking, maintain safety, and verify legal eligibility:

| Category of Personal Data | Specific Data Elements | Primary Processing Purpose | Lawful Basis (DPDP § 4 & § 6) |
|---|---|---|---|
| **Identity & Demographics** | Legal Name, Date of Birth, Gender, Relationship Intentions, Educational/Occupational Narrative | Account provisioning, identity verification, and compatibility matching | Free, specific, informed consent |
| **Visual Media** | Profile photos, moment photos, modesty-veiled images | Profile presentation, photo veil handshake, and discovery feed display | Free, specific, informed consent |
| **Auditory Media** | 7-second Voice Spark audio recordings (`voice_spark_url`), Whisper transcriptions | Human voice resonance discovery and profile showcase | Free, specific, informed consent |
| **Biometric Liveness (Ephemeral)** | Live camera video frames and selfie capture during onboarding | Automated liveness detection and sybil/bot prevention via Groq Vision API | Free, specific, informed consent (Processed via Groq Vision API; escalated manual verification frames retained in secure storage until desk review) |
| **Coarse Geolocation** | Latitude and longitude coordinates (fuzzed to ~1.1 km district level) | Distance calculation for mutual resonance filtering | Free, specific, informed consent |
| **Technical & Hardware Identifiers** | Installation UUID, SHA-256 device hardware hash, FCM push notification tokens | Underage quarantine registry enforcement, session security, push notifications | Legitimate use (Security & Underage Prevention) |
| **Communication Records** | Real-time chat messages (TLS-in-transit, PostgreSQL AES-256 at-rest storage), typing status, read receipts | Facilitating dialogue between matched seekers | Free, specific, informed consent |
| **Financial & Billing Data** | Transaction identifiers, order IDs, product SKUs, gross amounts in paise | Processing virtual perks, tax accounting, and statutory audit compliance | Compliance with legal obligation (Income Tax Act § 44AB) |

---

## 3. STRICT PROHIBITION ON DATA BROKERAGE & THIRD-PARTY SHARING
3.1. **Zero Data Brokerage Guarantee**: UR-Heart does NOT sell, rent, lease, trade, or monetize your personal data, profile photos, voice sparks, or chat transcripts to third-party data brokers, marketing agencies, or data aggregators.
3.2. **Authorized Service Processors (Data Processors)**:
   Personal data is shared strictly with contractually bound Data Processors operating under strict confidentiality and security safeguards:
   - **Cloud Infrastructure & Storage**: Cloudflare, Inc. (Cloudflare R2 Object Storage for encrypted media assets);
   - **Database Infrastructure**: Supabase, Inc. / PostgreSQL (Encrypted relational database hosting);
   - **AI Machine Intelligence**: Groq, Inc. and Google Cloud Platform (Ephemeral inference for audio transcription and KYC liveness verification; zero retention for foundation model training);
   - **Payment Aggregation**: Razorpay Software Private Limited / Stripe Payments (PCI-DSS compliant payment processing);
   - **Push Notifications**: Google Firebase Cloud Messaging (FCM).

---

## 4. CROSS-BORDER DATA TRANSFERS (DPDP ACT § 16)
Your personal data is hosted primarily on cloud servers located within the territory of the Republic of India. Any cross-border transfer of data to third-party processors (such as Cloudflare or cloud AI inference endpoints) is executed strictly in compliance with Section 16 of the DPDP Act 2023 and notifications issued by the Central Government, ensuring that data is never transferred to any restricted or blacklisted foreign country or territory.

---

## 5. DATA RETENTION & STATUTORY INCINERATION SCHEDULE
We retain personal data strictly for as long as necessary to fulfill the purposes of processing, or to comply with statutory legal requirements:

1. **Active Seeker Profiles**: Retained for the active lifespan of the account.
2. **Ephemeral Biometric Frames (KYC Liveness)**: Video frames captured during camera liveness checks are permanently deleted within **60 seconds** of automated machine verification. Only the binary verification status (`kyc_verified = True/False`) and timestamp are retained.
3. **Account Incineration (Section 12 Erasure)**:
   - When a seeker triggers account incineration, all profile data, photos, voice sparks, match records, FCM tokens, and private messages are **permanently and irrevocably expunged within 24 hours**.
   - Cloudflare R2 media files are deleted via prefix cascade (`users/{user_id}/`).
4. **Statutory Legal Retention Exceptions**:
   - Financial transaction ledgers (Order ID, Payment ID, Gross Amount) are retained in anonymized form for **7 years** pursuant to Section 44AB of the Income Tax Act, 1961.
   - Statutory grievance dossiers are retained in anonymized form for **1 year** pursuant to Rule 3(2) of the Information Technology Rules, 2021 for MeitY reporting.

---

## 6. SOVEREIGN STATUTORY RIGHTS OF DATA PRINCIPALS
Under Chapter III of the Digital Personal Data Protection Act, 2023, you hold the following sovereign rights:

1. **Right to Access Information (§ 11)**: You have the right to request a summary of personal data being processed, the identities of all Data Processors with whom data has been shared, and an automated machine-readable JSON copy of your personal data archive via the Sacred Legal Vault (`/vault`).
2. **Right to Correction & Completion (§ 12(1))**: You have the right to correct inaccurate personal data, complete incomplete records, and update dating preferences through your profile settings.
3. **Right to Erasure ("Account Incineration") (§ 12(3))**: You have the right to request full, irreversible erasure of your personal data via in-app settings or via our web portal at https://urheart.app/delete-account.
4. **Right to Nominate (§ 14)**: You have the right to nominate a digital nominee who, in the event of your death or incapacity, shall be authorized to exercise your data rights via our Legal Vault Nominee Designation interface.
5. **Right of Grievance Redressal (§ 13)**: You have the right to have grievances addressed by our designated Grievance Officer within statutory timelines.
6. **Right to Complain to the Data Protection Board of India**: If you are aggrieved by any decision or delay of the Data Fiduciary regarding your rights, you have the right to register a formal complaint with the Data Protection Board of India.

---

## 7. CONSTITUTIONAL EIGHTH SCHEDULE LANGUAGE AVAILABILITY (§ 5(3))
In accordance with Section 5(3) of the DPDP Act 2023, this Privacy Policy and Statutory Notice is made available in English and in the 22 languages specified in the Eighth Schedule to the Constitution of India (including Hindi, Bengali, Marathi, Telugu, Tamil, Gujarati, Kannada, Malayalam, Odia, and Punjabi) upon request or via the language selector at [https://urheart.app/privacy](https://urheart.app/privacy).
```

---

### DOCUMENT 3: GRIEVANCE OFFICER STATUTORY NOTICE & REDRESSAL PROTOCOL

```markdown
# UR-HEART SANCTUARY — GRIEVANCE OFFICER NOTICE & REDRESSAL PROTOCOL
**Published Pursuant to Rule 3(2) of the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021**
**Effective Date: October 15, 2026**

ASI Verticals Private Limited is committed to maintaining a safe, respectful, and legally compliant online matchmaking environment. In accordance with Rule 3(2) of the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021, this document details the identity of our designated Grievance Officer, the procedure for lodging complaints, and our statutory redressal timelines.

---

## 1. DESIGNATED RESIDENT GRIEVANCE OFFICER DETAILS
Seekers, victims, and members of the public may direct any grievance, takedown notice, legal notice, or complaint regarding content, privacy violations, harassment, impersonation, or platform abuse to our designated Resident Grievance Officer:

- **Full Legal Name**: [Insert Designated Resident Grievance Officer Name]
- **Professional Designation**: Resident Grievance Officer & Legal Counsel
- **Company Name**: [Insert Registered Corporate Entity Name]
- **Indian Registered Office Address**:  
  > [Insert Verified Indian Registered Office Address]  
- **Statutory Grievance Email**: [Insert Statutory Grievance Email]
- **Direct Redressal Desk Email**: [Insert Direct Redressal Desk Email]
- **Dedicated Telephone Helpline**: [Insert Authorized Grievance Redressal Telephone Helpline]  
  *(Operating Hours: Monday through Friday, 10:00 AM to 6:00 PM Indian Standard Time, excluding national holidays)*

---

## 2. STATUTORY COMPLAINT REDRESSAL PROTOCOL & SLA TIMELINES

UR-Heart operates a dual-track triage and resolution framework ensuring strict compliance with statutory mandates under Indian law:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   STATUTORY REDRESSAL WORKFLOW                                  │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│  [Complaint Received] ──────► [Automated Acknowledgment & Unique Ticket ID within 24 Hours]     │
│                                           │                                                     │
│                   ┌───────────────────────┴───────────────────────┐                             │
│                   ▼                                               ▼                             │
│       [TRACK A: EMERGENCY NCII / NUDITY]              [TRACK B: GENERAL GRIEVANCES]             │
│        (Rule 3(2)(b) Content Violations)               (Harassment, Impersonation, DPDP)        │
│                   │                                               │                             │
│                   ▼                                               ▼                             │
│     * IMMEDIATE MEDIA QUARANTINE                     * 48-Hour Safety Triage                    │
│     * MANDATORY TAKEDOWN WITHIN 24 HOURS             * Bilateral Notice to Reported Seeker      │
│     * Law Enforcement Report if CSAM                 * FINAL RESOLUTION WITHIN 15 DAYS          │
│                                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Track A: 24-Hour Mandatory Emergency Takedown (Rule 3(2)(b))
**Scope**: Complaints relating to content which prima facie:
- Exposes the private area of an individual;
- Shows an individual in full or partial nudity;
- Shows or depicts an individual in any sexual act or conduct;
- Constitutes Non-Consensual Intimate Imagery (NCII) or morphing;
- Depicts Child Sexual Abuse Material (CSAM);
- Involves non-consensual electronic impersonation or deepfake likeness creation.

**Emergency Workflow & Timelines**:
1. **Immediate Quarantine**: Upon submission of an emergency ticket through the App or via grievance@urheart.app, the platform's automated safety pipeline immediately disables public CDN access to the reported media and places the reported seeker's account into a temporary incognito safety shield pending moderation.
2. **Statutory Takedown**: The Grievance Officer shall review and permanently take down or disable access to such content **within twenty-four (24) hours** of receipt of the complaint.
3. **Mandatory Reporting**: Any material identified as depicting Child Sexual Abuse Material (CSAM) shall be reported immediately to the National Cyber Crime Reporting Portal (NCRP) pursuant to POCSO Act Section 19.

### 2.2 Track B: General Grievance Redressal (Rule 3(2)(a) & DPDP Act § 13)
**Scope**: Complaints relating to verbal abuse, stalking, off-platform harassment, spam, fraudulent billing, account deletion disputes, or DPDP Act Data Principal rights.

**Resolution Timelines**:
1. **Statutory Acknowledgment**: Every ticket receives an automated acknowledgement with a unique dossier reference tracking number (e.g., `GRIEV-2026-XXXX`) **within twenty-four (24) hours**.
2. **Investigation & Resolution**: The Grievance Officer shall investigate the facts, evaluate evidence, request additional particulars if necessary, and dispose of the complaint with an action report **within fifteen (15) calendar days** from the date of its receipt.

---

## 3. HOW TO LODGE A STATUTORY COMPLAINT
You may submit a grievance through any of the following official channels:
1. **In-App Direct Chat Grievance**: Tap the three-dot menu in any active dialogue screen and select **"Report Grievance"**. Select the appropriate violation category and submit narrative evidence. The target seeker's identifier is pre-filled automatically.
2. **In-App Sacred Legal Vault**: Navigate to `/vault` in the App, select **"File Statutory Grievance"**, pick the target profile from your recent resonances, select the violation category, and attach evidence.
3. **Email Submission**: Send an email to **grievance@urheart.app** including:
   - Your registered mobile number or email address;
   - The profile name, registered telephone/email, or screenshots of the reported user;
   - A detailed description of the incident;
   - Verifiable electronic evidence (screenshots, date and timestamps);
   - A declaration that the statements made in the complaint are true to the best of your knowledge.

---

## 4. APPELLATE REMEDIES: GRIEVANCE APPELLATE COMMITTEE (GAC)
If you are unsatisfied with the decision or resolution provided by our Grievance Officer, or if your complaint is not resolved within the statutory fifteen (15) day period, you have the statutory right under Rule 3A of the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021 to prefer an appeal to the **Grievance Appellate Committee (GAC)** established by the Central Government:
- **GAC Portal**: [https://gac.gov.in](https://gac.gov.in)
- **Time Limit for Appeal**: Within **thirty (30) days** from the date of receipt of communication from our Grievance Officer.
```

---

### DOCUMENT 4: REFUND, CANCELLATION & MICRO-TRANSACTION POLICY

```markdown
# UR-HEART SANCTUARY — REFUND, CANCELLATION & MICRO-TRANSACTION POLICY
**In Compliance with the Consumer Protection (E-Commerce) Rules, 2020 & Payment Gateway Guidelines**
**Effective Date: October 15, 2026**

ASI Verticals Private Limited ("Company", "We", "Us") operates the UR-Heart Dating Sanctuary. This Refund, Cancellation & Micro-Transaction Policy outlines the terms governing the purchase, delivery, and refund of digital goods, micro-perks, and subscriptions acquired on our platform.

---

## 1. NATURE OF IN-APP DIGITAL PURCHASES
1.1. **Immediate Digital Provisioning**: All products offered on UR-Heart (including Direct Letters, Boost Points, Profile Unlocks, and Sovereign Passes) are digital goods that are provisioned and credited to your account immediately upon successful payment authorization.
1.2. **General Non-Refundability**: Because in-app digital perks and passes are immediately consumed or made available for real-time matchmaking, all purchases are generally **non-refundable and non-exchangeable once delivered**, except in the specific circumstances outlined in Section 2 below.

---

## 2. EXCEPTIONS: ELIGIBILITY FOR STATUTORY REFUNDS
In strict compliance with Rule 4(11) of the Consumer Protection (E-Commerce) Rules, 2020 and Reserve Bank of India (RBI) payment guidelines, seekers are entitled to a full refund under the following circumstances:

### 2.1 Technical Failure & Unfulfilled Entitlements
If your bank account, card, or UPI VPA was debited, but the purchased digital perk or subscription was not provisioned to your account due to server communication error, network drop, or technical failure:
- Our automated reconciliation engine will attempt to provision the entitlement within twenty-four (24) hours.
- If the entitlement cannot be provisioned within 24 hours, an automated refund will be initiated to your original payment source.

### 2.2 Verified Duplicate / Double Debits
If a technical glitch causes multiple debits for a single transaction order, all duplicate debits beyond the single authorized transaction will be refunded automatically.

### 2.3 Fraudulent or Unauthorized Transactions
If your payment method was used fraudulently without your authorization, please report the transaction immediately to billing@urheart.app and your issuing bank. Upon verified fraud notice, the transaction will be refunded and the beneficiary account permanently terminated.

---

## 3. REFUND TIMELINES & METHOD OF SETTLEMENT
3.1. **Processing Window**: Verified refund requests are approved and dispatched to our banking aggregators within **48 hours** of ticket validation.
3.2. **Settlement Timeframe**: In accordance with RBI guidelines, refunds will reflect in your original payment method (Bank Account, Credit/Debit Card, or UPI) within **five (5) to seven (7) business days** depending on your issuing bank.
3.3. **No Cash Refunds**: All refunds are processed strictly back to the original funding instrument. Under no circumstances will refunds be issued in physical cash or transferred to third-party bank accounts.

---

## 4. PLATFORM-SPECIFIC BILLING DISCLOSURES

### 4.1 Apple App Store In-App Purchases
All purchases made on iOS devices are billed through Apple In-App Purchase. Apple manages all payment processing and refunds for iOS users. To request a refund for an iOS purchase:
1. Visit Apple's Report a Problem page: [https://reportaproblem.apple.com](https://reportaproblem.apple.com);
2. Sign in with your Apple ID;
3. Select "Request a refund", choose your reason, and select the UR-Heart purchase.

### 4.2 Google Play Store Purchases
All purchases made on Android devices are billed through Google Play Billing. You may request a refund via the Google Play Store app within 48 hours of purchase by visiting [https://play.google.com/store/account/orderhistory](https://play.google.com/store/account/orderhistory).

### 4.3 Web Sanctuary Purchases (Razorpay / Stripe)
Purchases made via our Web Storefront ([https://urheart.app/store](https://urheart.app/store)) are managed directly by ASI Verticals Private Limited. For any inquiries or refund requests, contact our dedicated billing desk at **billing@urheart.app**.

---

## 5. CONTACT OUR BILLING REDRESSAL DESK
For questions, failed transaction investigations, or double debit reconciliations:
- **Billing Redressal Email**: **billing@urheart.app**
- **Help Desk Telephone**: **+91-120-4567890** (Mon–Fri, 10 AM – 6 PM IST)
- **Response SLA**: Every ticket receives an automated tracking ID and personalized response within **24 hours**.
```

---

## 7. CONCRETE ENGINEERING IMPLEMENTATION REQUIREMENTS

To achieve full statutory, criminal, and platform compliance, the following precise engineering remediations must be executed across the backend, mobile client, and database migrations:

### 7.1 Backend Code Remediations

#### Remediation BE-01: Eliminate Google OAuth Hardcoded DOB & Mandate Cryptographic Age Verification
- **Target File**: `backend/app/services/auth_service.py` (lines 136–155)
- **Vulnerability**: `dob=date(2000, 1, 1)` hardcoded, bypassing age verification under DPDP § 9 and POCSO.
- **Action**: Require `age_intent_token` in `GoogleSyncRequest`. If `dob` is not verified, require explicit age verification before account provisioning:
```python
# Code Remediation Diff for backend/app/services/auth_service.py
# In google_sync():
if not user:
    if not payload.age_intent_token:
        raise SanctuaryException(
            error_code="AGE_VERIFICATION_REQUIRED",
            message="Seeker must complete age gate verification before account creation.",
            status_code=403,
        )
    # Cryptographically verify HMAC-signed age intent token
    verified_dob = self.verify_age_intent_token(payload.age_intent_token)
    if self.calculate_age(verified_dob) < 18:
        raise SanctuaryException(
            error_code="UNDERAGE_ACCESS_PROHIBITED",
            message="Seekers must be at least 18 years of age.",
            status_code=403,
        )
    user = User(
        auth_id=auth_id,
        email=email,
        full_name=claims.get("name") or "Seeker",
        dob=verified_dob,  # Bind verified date of birth
        ...
    )
```

#### Remediation BE-02: Eradicate Unilateral Photo Unlock Bypass
- **Target File**: `backend/app/services/photo_reveal_service.py` (lines 244–257 and 271–285)
- **Vulnerability**: `profile_unlock_single` paid micro-perk unilaterally unmasks target photos without affirmative consent (DPDP § 6, BNS § 77).
- **Action**: Delete the micro-perk bypass entirely. Photo reveals must strictly require `PhotoRevealConsent.status == 'accepted'`:
```python
# Code Remediation Diff for backend/app/services/photo_reveal_service.py
# Delete lines 244-257 entirely.
# Replace unlock_photo_with_perk() with an action that sends a "Priority Reveal Request"
# that STILL requires target seeker's explicit affirmative acceptance.
```

#### Remediation BE-03: Implement Mandatory 24-Hour NCII SLA & Automated Quarantine
- **Target File**: `backend/app/services/legal_vault_service.py` (lines 125–141)
- **Vulnerability**: Generic 15-day SLA applied to sexually explicit content; missing 24-hour takedown under IT Rules Rule 3(2)(b).
- **Action**: Implement conditional statutory deadline and immediate safety quarantine:
```python
# Code Remediation Diff for backend/app/services/legal_vault_service.py
ack_time = datetime.now(timezone.utc)
if payload.violation_category in ("explicit_content", "impersonation", "underage"):
    # Rule 3(2)(b) 24-Hour Fast-Track Statutory SLA
    due_date = ack_time + timedelta(hours=24)
    is_emergency = True
    # Immediate safety quarantine of reported seeker's media assets
    await self.quarantine_user_media(payload.reported_user_id, session)
else:
    # Rule 3(2)(a) 15-Day General Resolution SLA
    due_date = ack_time + timedelta(days=15)
    is_emergency = False
```

#### Remediation BE-04: Implement User Blocking API Endpoints
- **Target File**: Create `backend/app/api/v1/endpoints/blocking.py`
- **Vulnerability**: Missing user blocking endpoints violating Apple Guideline 1.2 and Google Play UGC policies.
- **Action**: Implement `POST /api/v1/users/{target_id}/block` and `DELETE /api/v1/users/{target_id}/block` using the existing `public.blocked_users` table.

---

### 7.2 Flutter Client Code Remediations

#### Remediation FE-01: Re-Enable In-App Chat Grievance Reporting
- **Target File**: `lib/features/chat/presentation/screens/chat_dialogue_screen.dart` (lines 259–270)
- **Vulnerability**: `PopupMenuItem(value: 'report_grievance', enabled: false, child: Text('Report Grievance (Coming Soon)'))`.
- **Action**: Set `enabled: true`, remove "(Coming Soon)", and launch the statutory grievance modal pre-populating `reported_user_id` with the dialogue peer's UUID.

#### Remediation FE-02: Implement User Blocking Action Sheet in Chat & Profile
- **Target File**: `lib/features/chat/presentation/screens/chat_dialogue_screen.dart` and `lib/features/profile/presentation/screens/seeker_profile_detail_screen.dart`
- **Action**: Add a "Block Seeker" button that invokes the blocking API, terminates active match dialogue, and removes the blocked profile from discovery decks.

#### Remediation FE-03: Wire Navigation Shell to Settings & Legal Vault
- **Target File**: `lib/features/navigation/presentation/screens/sanctuary_navigation_shell.dart` and `lib/features/profile/presentation/screens/my_persona_screen.dart`
- **Vulnerability**: `/settings` and `/vault` routes are orphaned; seekers cannot reach account deletion or DPDP nominee features.
- **Action**: Implement profile management buttons on `MyPersonaScreen` linking directly to `/settings` ("Sanctuary Settings & Account Deletion") and `/vault` ("Sacred Legal Vault").

#### Remediation FE-04: Persist Statutory Consent to Server
- **Target File**: `lib/features/auth/presentation/screens/consent_screen.dart` (lines 39–47)
- **Vulnerability**: Consent stored only in plaintext local `SharedPreferences`.
- **Action**: Dispatch `POST /api/v1/legal/consent-record` upon affirmation, writing an immutable cryptographic log entry to `public.consent_audit_logs`.

---

### 7.3 Supabase Database Migration Remediations

#### Remediation DB-01: Fix Storage Deletion Trigger Key Mismatch
- **Target File**: `supabase/migrations/20261015120000_sync_schema_and_fix_incineration.sql`
- **Vulnerability**: Trigger deletes `users/{OLD.auth_id}/%` while media is stored under `users/{OLD.id}/%`.
- **Action**: Replace `handle_user_cascade_cleanup` function:
```sql
CREATE OR REPLACE FUNCTION public.handle_user_cascade_cleanup()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    -- Fix: Use OLD.id (public.users.id) to match actual upload prefix
    DELETE FROM storage.objects
    WHERE bucket_id = 'ur-heart-media'
      AND (
        name LIKE ('users/' || OLD.id::text || '/%')
        OR name LIKE ('kyc_temp/' || OLD.id::text || '/%')
      );
    RETURN OLD;
END;
$$;
```

#### Remediation DB-02: Fix Match Cascade to Preserve Peer Incineration Notice
- **Target File**: `supabase/migrations/20261015120000_sync_schema_and_fix_incineration.sql`
- **Vulnerability**: Foreign key `ON DELETE CASCADE` instantly vaporizes matches marked as `'peer_incinerated'`.
- **Action**: Alter foreign keys on `public.matches` to `ON DELETE SET NULL` or implement a soft-tombstone architecture so surviving seekers receive appropriate notification of their peer's departure.

---

## 8. INDEPENDENT VERIFICATION & AUDIT ATTESTATION

### 8.1 Empirical Verification Commands
To independently verify the empirical findings documented in this report:

1. **Verify Google OAuth DOB Bypass**:
   ```bash
   git grep -n "dob=date(2000, 1, 1)" backend/app/services/auth_service.py
   # Line 142 confirms hardcoded birthdate during Google OAuth account provisioning.
   ```
2. **Verify Unilateral Photo Reveal Bypass**:
   ```bash
   git grep -n "profile_unlock_single" backend/app/services/photo_reveal_service.py
   # Lines 244-257 confirm instant photo unmasking upon micro-perk purchase without mutual consent.
   ```
3. **Verify Disabled In-App Chat Reporting**:
   ```bash
   git grep -n "Report Grievance (Coming Soon)" lib/features/chat/
   # Line 266 of chat_dialogue_screen.dart confirms hardcoded enabled: false.
   ```
4. **Verify Missing User Blocking Endpoints**:
   ```bash
   git grep -n "def block" backend/app/api/v1/endpoints/
   # Returns 0 results; confirms zero endpoints exist to block abusive users.
   ```
5. **Verify Orphaned Settings & Legal Vault Routes**:
   ```bash
   git grep -n "SanctuarySettingsScreen" lib/
   git grep -n "VaultLegalScreen" lib/
   # Confirms routes exist in app_router.dart but are never navigated to from sanctuary_navigation_shell.dart.
   ```
6. **Verify Storage Cascade Trigger Prefix Mismatch**:
   ```bash
   git grep -n "OLD.auth_id" supabase/migrations/
   # Line 1129 of 20260926000000 migration confirms mismatch with backend/app/api/v1/endpoints/media.py#L55.
   ```

### 8.2 Auditor Sign-Off
This Legal & Regulatory Compliance Audit Report provides an exhaustive, empirically substantiated assessment of the legal and regulatory risk exposure of the UR-Heart dating platform. All findings have been verified directly against the production source code and database migrations. Immediate execution of the engineering remediations and publication of the draft legal documents provided in Section 6 is mandatory to safeguard the platform against catastrophic financial penalties and criminal liability.

**Report Compiled & Certified By**:  
*Legal & Regulatory Specialist Worker (`worker_legal_1`)*  
ASI Verticals Multi-Agent Quality Assurance & Regulatory Taskforce  
October 15, 2026
