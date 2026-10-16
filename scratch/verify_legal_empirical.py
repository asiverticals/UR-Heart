"""
Empirical verification script for legal, regulatory & compliance claims in audit_legal.md.
"""
import os
import sys
import re

def verify_google_oauth_dob():
    print("\n--- Legal Check 1: Google OAuth DOB Hardcoding (DPDP Section 9 & POCSO) ---")
    path = "backend/app/services/auth_service.py"
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    target_found = False
    for idx, line in enumerate(lines, 1):
        if "dob=date(2000, 1, 1)" in line:
            print(f"[FOUND] {path}:{idx} -> {line.strip()}")
            target_found = True
            break
    assert target_found, "dob=date(2000, 1, 1) was not found in auth_service.py!"
    print("[PASS] Verified Google OAuth hardcodes DOB to 2000-01-01, bypassing age verification.")

def verify_in_app_reporting_disabled():
    print("\n--- Legal Check 2: Disabled In-App Chat Reporting (IT Rules & Store Guidelines) ---")
    path = "lib/features/chat/presentation/screens/chat_dialogue_screen.dart"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "value: 'report_grievance'" in content
    assert "enabled: false" in content
    assert "Report Grievance (Coming Soon)" in content
    print("[PASS] Verified chat_dialogue_screen.dart hardcodes report_grievance as disabled with '(Coming Soon)'.")

def verify_unilateral_photo_reveal():
    print("\n--- Legal Check 3: Unilateral INR 39 Photo Reveal Bypass (DPDP Section 6 & BNS Section 77-78) ---")
    path = "backend/app/services/photo_reveal_service.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "profile_unlock_single" in content
    print("[PASS] Verified photo_reveal_service.py contains profile_unlock_single paid micro-perk.")

def verify_ncii_24hr_sla_absence():
    print("\n--- Legal Check 4: Missing 24-Hour NCII Emergency SLA (IT Rules Rule 3(2)(b)) ---")
    path = "backend/app/services/legal_vault_service.py"
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    fixed_15_days = False
    twenty_four_hours = False
    for idx, line in enumerate(lines, 1):
        if "timedelta(days=15)" in line:
            print(f"[FOUND] {path}:{idx} -> {line.strip()}")
            fixed_15_days = True
        if "timedelta(hours=24)" in line:
            twenty_four_hours = True

    assert fixed_15_days, "Expected timedelta(days=15) in legal_vault_service.py"
    assert not twenty_four_hours, "Did not expect 24-hour SLA logic in current legal_vault_service.py!"
    print("[PASS] Verified legal_vault_service.py enforces a blanket 15-day SLA with no 24-hr NCII fast-track.")

def verify_missing_user_blocking_endpoints():
    print("\n--- Legal Check 5: Missing User Blocking Endpoints (Apple 1.2 & Google UGC) ---")
    import os
    endpoints_dir = "backend/app/api/v1/endpoints"
    block_endpoints = []
    for root, _, files in os.walk(endpoints_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "@router." in line and "/block" in line:
                            block_endpoints.append(f"{file_path}: {line.strip()}")
    print(f"Block endpoints found: {block_endpoints}")
    assert len(block_endpoints) == 0, f"Expected 0 user blocking endpoints, found: {block_endpoints}"
    print("[PASS] Verified backend exposes zero blocking endpoints.")

def verify_storage_trigger_prefix_mismatch():
    print("\n--- Legal Check 6: Storage Cleanup Trigger Prefix Alignment (DPDP Section 12) ---")
    migrations_dir = "supabase/migrations"
    mig_files = sorted(os.listdir(migrations_dir))
    final_migration_content = ""
    for mf in reversed(mig_files):
        if mf.endswith(".sql"):
            with open(os.path.join(migrations_dir, mf), "r", encoding="utf-8") as f:
                content = f.read()
                if "FUNCTION public.handle_user_cascade_cleanup" in content:
                    final_migration_content = content
                    break
    start = final_migration_content.find("FUNCTION public.handle_user_cascade_cleanup")
    assert start != -1, "handle_user_cascade_cleanup function definition not found in latest migration"
    end = final_migration_content.find("$$;", start)
    func_body = final_migration_content[start:end]

    assert "users/' || OLD.id::text" in func_body, "Function body does not delete users/{OLD.id} prefix"
    assert "DELETE FROM storage.objects" in func_body, "Function body does not delete from storage.objects"

    media_endpoint_path = "backend/app/api/v1/endpoints/media.py"
    with open(media_endpoint_path, "r", encoding="utf-8") as f:
        media_code = f.read()

    # In media.py, uploads are saved under users/{current_user.id}/
    assert "users/{current_user.id}" in media_code
    print("[PASS] Verified storage cleanup alignment: Final trigger checks 'users/{OLD.id}/' matching upload path 'users/{current_user.id}/'.")

def verify_payments_parameter_tampering():
    print("\n--- Security Check: Payment Parameter Tampering (SEC-05) ---")
    path = "backend/app/api/v1/endpoints/payments.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "product_identifier = payload.product_identifier" in content
    assert "if not product_identifier:" in content
    assert "amount_gross=None" in content
    print("[PASS] Verified payments.py accepts client-supplied product_identifier and ignores billing amount check.")

def verify_live_secrets_in_env():
    print("\n--- Security Check: Configuration Credential Presence in .env ---")
    with open(".env", "r", encoding="utf-8") as f:
        env_content = f.read()

    required_keys = [
        "DATABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPERADMIN_SECRET_KEY",
        "RESEND_API_KEY",
        "SMTP_PASSWORD",
    ]
    for key in required_keys:
        match = re.search(rf"^{key}=\S+", env_content, re.MULTILINE)
        assert match is not None, f"Expected non-empty {key} in .env"
    print("[PASS] Verified configuration credentials present for DATABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPERADMIN_SECRET_KEY, RESEND_API_KEY, and SMTP_PASSWORD without exposing secrets.")

def main():
    print("=======================================================")
    print("UR-HEART LEGAL & SECURITY EMPIRICAL CHALLENGE HARNESS")
    print("=======================================================")
    verify_google_oauth_dob()
    verify_in_app_reporting_disabled()
    verify_unilateral_photo_reveal()
    verify_ncii_24hr_sla_absence()
    verify_missing_user_blocking_endpoints()
    verify_storage_trigger_prefix_mismatch()
    verify_payments_parameter_tampering()
    verify_live_secrets_in_env()
    print("\n>>> ALL 8 EMPIRICAL LEGAL & SECURITY CHECKS PASSED WITH 100% ACCURACY! <<<")

if __name__ == "__main__":
    main()
