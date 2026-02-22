"""
Week 1 Capstone Pre-Submission Check
=====================================

Run this before submitting to catch structural issues, bloat, and secrets.

Usage (from your capstone repo root):
    uv run python week-1/prequalify.py
"""

import re
import sys
from pathlib import Path

# Resolve week-1/ directory (script lives inside it)
WEEK_DIR = Path(__file__).resolve().parent
REPO_ROOT = WEEK_DIR

# Expected filename: firstname_lastname_week1_submission.txt
# Group: firstname1_firstname2_week1_submission.txt
SUBMISSION_FILENAME_PATTERN = r"^[a-z]+(_[a-z]+)+_week1_submission\.txt$"

REQUIRED_FILES = {
    "submission.md": "Your main submission document",
    "docs/scoping.md": "Problem scoping (IDENTIFY/QUALIFY/DEFINE/SCOPE)",
    "data/README.md": "Data sourcing documentation",
    "analysis/data_quality_notes.md": "Corpus analysis findings",
    "traces/trace.md": "Traced queries with assessments",
    ".gitingestignore": "Gitingest ignore rules for data exclusions",
}

SUBMISSION_REQUIRED_SECTIONS = [
    "Student Name",
    "Project Title",
    "Problem Statement",
    "Data Overview",
    "Data Curation Summary",
    "Pipeline Configuration",
    "Trace Summary",
    "Observations",
    "Self-Assessment",
]

SCOPING_REQUIRED_SECTIONS = [
    "IDENTIFY",
    "QUALIFY",
    "DEFINE",
    "SCOPE",
]

MIN_TRACES = 5
MAX_SUBMISSION_BYTES = 1_000_000  # 1MB
MIN_SUBMISSION_BYTES = 5_000      # 5KB — below this, files are probably empty
MAX_FILE_COUNT = 50               # Week 1 should not have 50+ files
MAX_SINGLE_FILE_LINES = 2000      # Flag individual files over this in the .txt

# Patterns that indicate leaked secrets
SECRET_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub PAT"),
    (r"ghu_[a-zA-Z0-9]{36}", "GitHub user token"),
    # Match KEY=value but NOT KEY = os.getenv(...) or KEY = Secret(...) etc.
    (r"QDRANT_API_KEY\s*=\s*(?!os\.|Secret|None|getenv|environ|\"|\')[A-Za-z0-9_\-]{8,}", "Qdrant API key"),
    (r"GOOGLE_API_KEY\s*=\s*(?!os\.|Secret|None|getenv|environ|\"|\')[A-Za-z0-9_\-]{8,}", "Google API key"),
    (r"ANTHROPIC_API_KEY\s*=\s*(?!os\.|Secret|None|getenv|environ|\"|\')[A-Za-z0-9_\-]{8,}", "Anthropic API key"),
    (r"VOYAGE_API_KEY\s*=\s*(?!os\.|Secret|None|getenv|environ|\"|\')[A-Za-z0-9_\-]{8,}", "Voyage API key"),
    (r"Bearer\s+[a-zA-Z0-9\-_.]{20,}", "Bearer token"),
    (r"password\s*=\s*['\"][^'\"]{8,}['\"]", "Hardcoded password"),
]

# Patterns indicating raw data leaked into the submission
DATA_BLOAT_PATTERNS = [
    (r"^FILE:\s+.*data/raw/", "data/raw/ files included — check .gitingestignore"),
    (r"^FILE:\s+.*data/processed/", "data/processed/ files included — check .gitingestignore"),
    (r"^FILE:\s+.*\.env$", ".env file included — secrets may be exposed"),
    (r"^FILE:\s+.*\.csv$", "CSV file included — should be in .gitingestignore"),
    (r"^FILE:\s+.*\.parquet$", "Parquet file included — should be in .gitingestignore"),
]


def check_file_exists(rel_path: str, description: str) -> bool:
    path = WEEK_DIR / rel_path
    if path.exists():
        print(f"  PASS  {rel_path}")
        return True
    else:
        print(f"  FAIL  {rel_path} — {description}")
        return False


def check_has_scripts() -> bool:
    scripts_dir = WEEK_DIR / "scripts"
    if not scripts_dir.exists():
        print(f"  FAIL  scripts/ — directory not found")
        return False
    py_files = list(scripts_dir.glob("*.py"))
    if len(py_files) == 0:
        print(f"  FAIL  scripts/ — no Python files found")
        return False
    print(f"  PASS  scripts/ — {len(py_files)} Python file(s)")
    return True


def check_sections(file_path: Path, required_sections: list[str], label: str) -> tuple[bool, list[str]]:
    if not file_path.exists():
        return False, required_sections

    content = file_path.read_text()
    missing = []
    for section in required_sections:
        pattern = rf"(^#+\s*{re.escape(section)}|^\*\*{re.escape(section)}\*\*)"
        if not re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
            if section.lower() not in content.lower():
                missing.append(section)

    if missing:
        print(f"  FAIL  {label} — missing sections: {', '.join(missing)}")
        return False, missing
    else:
        print(f"  PASS  {label} — all required sections present")
        return True, []


def check_student_names() -> tuple[bool, list[str]]:
    """Check that submission.md has real names under Student Name section."""
    submission_path = WEEK_DIR / "submission.md"
    if not submission_path.exists():
        return False, []

    content = submission_path.read_text()

    # Find Student Name section and extract the content after it
    match = re.search(
        r"##\s*Student\s*Name[s]?\s*\n+(.*?)(?=\n##|\Z)",
        content,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        print(f"  FAIL  Student Name section not found in submission.md")
        return False, []

    name_block = match.group(1).strip()
    if not name_block or name_block.startswith("["):
        print(f"  FAIL  Student Name is empty or still a placeholder")
        return False, []

    # Extract names (one per line, or comma-separated, or bullet points)
    names = []
    for line in name_block.splitlines():
        line = line.strip().lstrip("- ").lstrip("* ").strip()
        if line and not line.startswith("["):
            # Handle comma-separated names
            for name in line.split(","):
                name = name.strip()
                if name:
                    names.append(name)

    if not names:
        print(f"  FAIL  No student names found in submission.md")
        return False, []

    # Each name should have at least first and last name (2+ words)
    incomplete = [n for n in names if len(n.split()) < 2]
    if incomplete:
        print(f"  FAIL  Each student must have full name (first + last): {', '.join(incomplete)}")
        return False, names

    print(f"  PASS  Student name(s): {', '.join(names)}")
    return True, names


def check_trace_count() -> tuple[bool, int]:
    trace_path = WEEK_DIR / "traces" / "trace.md"
    if not trace_path.exists():
        print(f"  FAIL  traces/trace.md — file not found")
        return False, 0

    content = trace_path.read_text()
    query_matches = re.findall(r"^#+\s*Query\s", content, re.MULTILINE | re.IGNORECASE)
    if not query_matches:
        query_matches = re.findall(r"^\*\*Question:?\*\*", content, re.MULTILINE)
    if not query_matches:
        query_matches = re.findall(r"^##\s+\d+", content, re.MULTILINE)

    count = len(query_matches)
    if count >= MIN_TRACES:
        print(f"  PASS  traces/trace.md — {count} queries found (minimum: {MIN_TRACES})")
        return True, count
    else:
        print(f"  FAIL  traces/trace.md — {count} queries found (minimum: {MIN_TRACES})")
        return False, count


def check_submission_not_template() -> bool:
    submission_path = WEEK_DIR / "submission.md"
    if not submission_path.exists():
        return False

    content = submission_path.read_text()
    template_markers = [
        "[Your name]",
        "[One-line project title]",
        "[Your one-sentence problem statement",
        "[X documents, Y total size]",
    ]

    unfilled = [m for m in template_markers if m in content]
    if unfilled:
        print(f"  WARN  submission.md — still has template placeholders: {', '.join(unfilled)}")
        return False
    else:
        print(f"  PASS  submission.md — no template placeholders found")
        return True


def find_submission_txt() -> Path | None:
    """Find the submission .txt file in repo root matching naming convention."""
    candidates = list(REPO_ROOT.glob("*_week1_submission.txt"))
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        print(f"  FAIL  Multiple submission files found: {[c.name for c in candidates]}")
        return None
    # Fallback: check for old naming
    fallback = REPO_ROOT / "week-1-submission.txt"
    if fallback.exists():
        return fallback
    return None


def check_submission_filename(names: list[str]) -> tuple[bool, Path | None]:
    """Check submission .txt exists and follows naming convention."""
    txt_path = find_submission_txt()

    if txt_path is None:
        print(f"  FAIL  No submission .txt found in repo root")
        print(f"        Expected: firstname_lastname_week1_submission.txt")
        print(f"        Run: uv run gitingest week-1/ -o <name>_week1_submission.txt")
        return False, None

    filename = txt_path.name

    # Check naming convention
    if re.match(SUBMISSION_FILENAME_PATTERN, filename):
        print(f"  PASS  {filename} — naming convention correct")
        return True, txt_path

    if filename == "week-1-submission.txt":
        # Build expected name from student names
        if names:
            first_names = "_".join(n.split()[0].lower() for n in names)
            expected = f"{first_names}_week1_submission.txt"
        else:
            expected = "firstname_lastname_week1_submission.txt"
        print(f"  FAIL  {filename} — wrong naming convention")
        print(f"        Expected: {expected}")
        print(f"        Run: uv run gitingest week-1/ -o {expected}")
        return False, txt_path

    print(f"  WARN  {filename} — does not match expected pattern")
    print(f"        Expected: firstname_lastname_week1_submission.txt")
    return False, txt_path


def check_submission_size(txt_path: Path) -> bool:
    size_bytes = txt_path.stat().st_size
    size_kb = size_bytes / 1024
    size_mb = size_bytes / (1024 * 1024)

    passed = True
    if size_bytes > MAX_SUBMISSION_BYTES:
        print(f"  FAIL  {txt_path.name} — {size_mb:.1f}MB (must be under 1MB). Check .gitingestignore.")
        passed = False
    elif size_bytes < MIN_SUBMISSION_BYTES:
        print(f"  WARN  {txt_path.name} — {size_kb:.0f}KB (suspiciously small, are your files empty?)")
        passed = False
    else:
        print(f"  PASS  {txt_path.name} — {size_kb:.0f}KB")

    return passed


def check_file_count(txt_path: Path) -> bool:
    """Check that the submission doesn't have too many files."""
    content = txt_path.read_text()
    file_headers = re.findall(r"^FILE:\s+", content, re.MULTILINE)
    count = len(file_headers)

    if count > MAX_FILE_COUNT:
        print(f"  FAIL  {count} files in submission (max {MAX_FILE_COUNT}) — likely includes data files. Check .gitingestignore.")
        return False
    elif count == 0:
        print(f"  FAIL  No files found in submission .txt — gitingest may have failed")
        return False
    else:
        print(f"  PASS  {count} files in submission")
        return True


def check_no_secrets(txt_path: Path) -> bool:
    """Scan submission .txt for leaked API keys, tokens, and passwords."""
    content = txt_path.read_text()
    found = []

    for pattern, label in SECRET_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            found.append(f"{label} ({len(matches)} match{'es' if len(matches) > 1 else ''})")

    if found:
        print(f"  FAIL  Possible secrets detected:")
        for f in found:
            print(f"        - {f}")
        print(f"        Remove secrets from your code and regenerate the submission .txt")
        return False
    else:
        print(f"  PASS  No secrets detected")
        return True


def check_no_data_bloat(txt_path: Path) -> bool:
    """Check that raw data files didn't leak into the submission."""
    content = txt_path.read_text()
    found = []

    for pattern, label in DATA_BLOAT_PATTERNS:
        if re.search(pattern, content, re.MULTILINE):
            found.append(label)

    if found:
        print(f"  FAIL  Data files leaked into submission:")
        for f in found:
            print(f"        - {f}")
        return False
    else:
        print(f"  PASS  No data file bloat detected")
        return True


def check_large_files(txt_path: Path) -> bool:
    """Flag individual files in the .txt that are disproportionately large."""
    content = txt_path.read_text()
    # Split by file headers
    file_sections = re.split(r"^={48}\nFILE:\s+(.+)\n={48}$", content, flags=re.MULTILINE)

    # file_sections: [preamble, filename1, content1, filename2, content2, ...]
    large_files = []
    for i in range(1, len(file_sections) - 1, 2):
        filename = file_sections[i]
        file_content = file_sections[i + 1]
        line_count = file_content.count("\n")
        if line_count > MAX_SINGLE_FILE_LINES:
            large_files.append((filename, line_count))

    if large_files:
        print(f"  WARN  Large files detected (over {MAX_SINGLE_FILE_LINES} lines):")
        for name, lines in large_files:
            print(f"        - {name} ({lines} lines)")
        print(f"        Consider whether these should be in .gitingestignore")
        return False
    else:
        print(f"  PASS  No oversized files")
        return True


def check_no_binary(txt_path: Path) -> bool:
    """Check for binary content or base64 blobs that slipped through."""
    content = txt_path.read_text(errors="replace")

    # Check for base64 blobs (long strings of base64 chars)
    base64_blobs = re.findall(r"[A-Za-z0-9+/=]{200,}", content)
    # Filter out legitimate long strings (like URLs or hashes)
    suspicious = [b for b in base64_blobs if len(b) > 500]

    # Check for null bytes or binary indicators
    has_binary_marker = "[Binary file]" in content

    issues = []
    if suspicious:
        issues.append(f"{len(suspicious)} base64/binary blob(s) detected")
    if has_binary_marker:
        issues.append("Binary file markers found — binary files should not be in submission")

    if issues:
        print(f"  WARN  Possible binary content:")
        for issue in issues:
            print(f"        - {issue}")
        return False
    else:
        print(f"  PASS  No binary content detected")
        return True


def main():
    print("=" * 60)
    print("  Week 1 Capstone — Pre-Submission Check")
    print("=" * 60)
    print(f"\nChecking: {WEEK_DIR}\n")

    all_passed = True
    warnings = False

    # 1. Required files
    print("Required files:")
    for rel_path, description in REQUIRED_FILES.items():
        if not check_file_exists(rel_path, description):
            all_passed = False

    if not check_has_scripts():
        all_passed = False

    # 2. Submission sections
    print("\nSubmission document sections:")
    passed, _ = check_sections(
        WEEK_DIR / "submission.md",
        SUBMISSION_REQUIRED_SECTIONS,
        "submission.md",
    )
    if not passed:
        all_passed = False

    # 3. Scoping sections
    print("\nScoping document sections:")
    passed, _ = check_sections(
        WEEK_DIR / "docs" / "scoping.md",
        SCOPING_REQUIRED_SECTIONS,
        "docs/scoping.md",
    )
    if not passed:
        all_passed = False

    # 4. Student names
    print("\nStudent names:")
    names_passed, names = check_student_names()
    if not names_passed:
        all_passed = False

    # 5. Template check
    print("\nTemplate check:")
    if not check_submission_not_template():
        warnings = True

    # 6. Trace count
    print("\nTraces:")
    passed, count = check_trace_count()
    if not passed:
        all_passed = False

    # 7. Submission .txt naming and size
    print("\nSubmission file:")
    name_ok, txt_path = check_submission_filename(names)
    if not name_ok:
        all_passed = False

    if txt_path and txt_path.exists():
        if not check_submission_size(txt_path):
            all_passed = False

        # 8. Content checks on the .txt
        print("\nSubmission content checks:")
        if not check_file_count(txt_path):
            all_passed = False
        if not check_no_data_bloat(txt_path):
            all_passed = False
        if not check_no_secrets(txt_path):
            all_passed = False
        if not check_no_binary(txt_path):
            warnings = True
        if not check_large_files(txt_path):
            warnings = True

    # Summary
    print("\n" + "=" * 60)
    if all_passed and not warnings:
        print("  All checks passed. Ready to submit.")
    elif all_passed and warnings:
        print("  Checks passed with warnings. Review warnings above.")
    else:
        print("  Some checks failed. Fix the issues above before submitting.")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
