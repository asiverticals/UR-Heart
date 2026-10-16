"""
Deep forensic verification script v2.
Properly handles ambiguous filenames by trying specific directories.
"""
import os
import re
import sys

BASE_DIR = os.path.abspath(".")

def resolve_exact_path(fn_str):
    clean = fn_str.replace("\\", "/").strip("`'\" ")
    # 1. Try directly
    candidate = os.path.join(BASE_DIR, clean)
    if os.path.exists(candidate) and os.path.isfile(candidate):
        return os.path.relpath(candidate, BASE_DIR)
        
    # 2. Try prefix variations
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
        "lib/features/growth/presentation/screens",
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
    matches = []
    for p in prefixes:
        candidate = os.path.join(BASE_DIR, p, clean)
        if os.path.exists(candidate) and os.path.isfile(candidate):
            matches.append(os.path.relpath(candidate, BASE_DIR))
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        print(f"  [AMBIGUITY ERROR] Unqualified citation '{clean}' matches multiple candidates: {matches}")
        return None
    return None

REPORTS = [
    "reports/audit_architecture.md",
    "reports/audit_security.md",
    "reports/audit_legal.md",
]

overall_has_errors = False

for rep in REPORTS:
    print(f"\n========================================================")
    print(f"ACCURATE CITATION AUDIT: {rep}")
    print(f"========================================================")
    
    with open(os.path.join(BASE_DIR, rep), "r", encoding="utf-8") as f:
        text = f.read()

    pattern = re.compile(
        r'(`)?(?P<path>\.env|Dockerfile|[a-zA-Z0-9_\-\.\/]+\.(?:dart|py|sql|yaml|yml|json|env|md))'
        r'(?:#L(?P<start>\d+)(?:-L?(?P<end>\d+))?)?(`)?'
    )
    matches = list(pattern.finditer(text))
    
    unique_refs = set()
    for m in matches:
        fn = m.group("path")
        s = m.group("start")
        e = m.group("end")
        unique_refs.add((fn, s, e))

    found_count = 0
    missing_list = []
    line_mismatch_list = []
    
    for fn, s, e in sorted(unique_refs, key=lambda x: x[0]):
        # Skip external URLs, sample payloads, or shims
        if fn.startswith(("..", "http://", "https://", "wss://", "ws://")) or any(ign in fn for ign in [
            "github", "example.com", "exploit.json", "resp.json",
            "ORIGINAL_REQUEST.md", "blocking.py"
        ]):
            continue
            
        resolved = resolve_exact_path(fn)
        if not resolved:
            missing_list.append((fn, s, e))
        else:
            found_count += 1
            if s:
                abs_resolved = os.path.join(BASE_DIR, resolved)
                with open(abs_resolved, "r", encoding="utf-8", errors="replace") as rf:
                    lines = rf.readlines()
                total = len(lines)
                start_l = int(s)
                end_l = int(e) if e else start_l
                if start_l < 1 or start_l > total or end_l < start_l or end_l > total:
                    line_mismatch_list.append((fn, resolved, s, e, total))

    print(f"Resolved repo files: {found_count}")
    print(f"Missing/unresolved file paths: {len(missing_list)}")
    for mf in missing_list:
        print(f"  [UNRESOLVED] {mf}")
    print(f"Out of bounds line citations: {len(line_mismatch_list)}")
    for om in line_mismatch_list:
        print(f"  [OUT OF BOUNDS] {om}")

    if missing_list or line_mismatch_list:
        overall_has_errors = True

if overall_has_errors:
    sys.exit(1)
