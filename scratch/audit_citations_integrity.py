"""
Forensic citation verification for UR-Heart audit reports.
Extracts file references, line ranges, and verifies existence and content against the active codebase.
"""
import re
import os
import sys

BASE_DIR = os.path.abspath(".")

REPORTS = [
    "reports/audit_architecture.md",
    "reports/audit_security.md",
    "reports/audit_legal.md",
]

def resolve_exact_path(fn_str):
    clean = fn_str.replace("\\", "/").strip("`'\" ")
    candidate = os.path.join(BASE_DIR, clean)
    if os.path.exists(candidate) and os.path.isfile(candidate):
        return os.path.relpath(candidate, BASE_DIR)
        
    prefixes = [
        "lib",
        "backend",
        "backend/app",
        "backend/app/api/v1/endpoints",
        "backend/app/models/domain",
        "backend/app/schemas",
        "backend/app/services",
        "backend/app/core",
        "supabase",
        "supabase/migrations",
        "lib/core/app",
        "lib/core/network",
        "lib/core/theme/widgets",
        "lib/features/auth/presentation/controllers",
        "lib/features/profile_setup/presentation/controllers",
        "lib/features/profile/presentation/screens",
        "lib/features/chat/presentation/screens",
        "lib/features/chat/presentation/controllers",
        "lib/features/feed/presentation/screens",
        "lib/features/resonances/presentation/screens",
        "lib/features/resonances/presentation/controllers",
        "lib/features/blind_date/presentation/screens",
        "lib/features/blind_date/presentation/controllers",
        "lib/features/settings/presentation/screens",
        "lib/features/rewards/presentation/screens",
        "lib/features/admin/presentation/screens",
        "backend/app/api/v1",
        "backend/app/models",
        "lib/core/services",
        "lib/core/billing",
        "lib/core/storage",
        "lib/features/profile_setup/presentation/widgets",
        "lib/features/navigation/presentation/screens",
        "reports",
    ]
    for p in prefixes:
        candidate = os.path.join(BASE_DIR, p, clean)
        if os.path.exists(candidate) and os.path.isfile(candidate):
            return os.path.relpath(candidate, BASE_DIR)
            
    return None

def check_citations(report_path):
    print(f"\n==========================================")
    print(f"AUDITING CITATIONS IN: {report_path}")
    print(f"==========================================")
    
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r'(`)?([a-zA-Z0-9_\-\.\/]+\.(dart|py|sql|yaml|yml|json|env|md|Dockerfile))(#L(\d+)(?:-L?(\d+))?)?(`)?')
    
    matches = pattern.findall(content)
    print(f"Total potential file references matched: {len(matches)}")
    
    unique_refs = set()
    for m in matches:
        filepath = m[1]
        line_start = m[4] if m[4] else None
        line_end = m[5] if m[5] else None
        unique_refs.add((filepath, line_start, line_end))
        
    print(f"Unique file & line references: {len(unique_refs)}")
    
    missing_files = []
    invalid_line_numbers = []
    valid_citations = 0
    
    # Sort with safe key
    sorted_refs = sorted(list(unique_refs), key=lambda x: (x[0], int(x[1]) if x[1] else 0, int(x[2]) if x[2] else 0))
    
    for filepath, line_start, line_end in sorted_refs:
        # Skip external URLs, relative dart shims, or sample payloads
        if filepath.startswith(("..", "http://", "https://", "wss://", "ws://")) or any(ign in filepath for ign in [
            "github", "example.com", "exploit.json", "resp.json",
            "ORIGINAL_REQUEST.md", "blocking.py"
        ]):
            continue
        
        resolved = resolve_exact_path(filepath)
        if not resolved:
            missing_files.append((filepath, line_start, line_end))
            continue
            
        abs_path = os.path.join(BASE_DIR, resolved)
                
        # If file exists, check line numbers if specified
        if line_start:
            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as target_f:
                    total_lines = len(target_f.readlines())
                start_num = int(line_start)
                end_num = int(line_end) if line_end else start_num
                if start_num > total_lines or end_num > total_lines:
                    invalid_line_numbers.append((filepath, line_start, line_end, total_lines))
                else:
                    valid_citations += 1
            except Exception as e:
                invalid_line_numbers.append((filepath, line_start, line_end, str(e)))
        else:
            valid_citations += 1

    print(f"Valid citations verified: {valid_citations}")
    print(f"Missing files: {len(missing_files)}")
    if missing_files:
        for mf in missing_files:
            print(f"  [MISSING FILE] {mf}")
            
    print(f"Invalid line numbers: {len(invalid_line_numbers)}")
    if invalid_line_numbers:
        for il in invalid_line_numbers:
            print(f"  [INVALID LINE] {il}")
            
    return missing_files, invalid_line_numbers

def main():
    results = {}
    has_errors = False
    for r in REPORTS:
        abs_r = os.path.join(BASE_DIR, r)
        if os.path.exists(abs_r):
            missing, invalid = check_citations(abs_r)
            results[r] = {"missing": missing, "invalid": invalid}
            if missing or invalid:
                has_errors = True
        else:
            print(f"ERROR: Report {r} does not exist!")
            results[r] = {"missing": ["REPORT FILE ITSELF"], "invalid": []}
            has_errors = True

    if has_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
