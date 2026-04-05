"""
Week 3 Capstone Pre-Submission Check
=====================================

Run this before submitting to catch structural issues, bloat, and secrets.

Usage (from your capstone repo root):
    uv run python week-3/prequalify.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Resolve week-3/ directory (script lives inside it)
WEEK_DIR = Path(__file__).resolve().parent
REPO_ROOT = WEEK_DIR.parent

# Expected filename: firstname_lastname_week3_submission.txt
SUBMISSION_FILENAME_PATTERN = r"^[a-z]+(_[a-z]+)+_week3_submission\.txt$"

REQUIRED_FILES = {
    "submission.md": "Your main submission document",
    "docs/retrieval-analysis.md": "Constraint and corpus assessment",
    "docs/retrieval-strategy.md": "Hybrid config, reranking config, narrowing decision",
    "docs/iteration-log.md": "Iteration log — what you tried, changed, and learned",
    "evaluations/week3_comparison.md": "Week 2 vs Week 3 comparison with analysis",
    "evaluations/week3_deep_analysis.md": "Judge reliability deep-dive with spot-checked questions",
    ".gitingestignore": "Gitingest ignore rules",
}

SUBMISSION_REQUIRED_SECTIONS = [
    "Student Name",
    "Project Title",
    "Progress Recap",
    "Retrieval Assessment Summary",
    "Retrieval Configuration",
    "Evaluation Approach",
    "Evaluation Summary",
    "Judge Reliability",
    "Key Observations",
    "Iteration Summary",
    "Self-Assessment",
]

RETRIEVAL_ANALYSIS_REQUIRED_SECTIONS = [
    "Constraint",
    "Corpus",
    "Narrowing",
]

RETRIEVAL_STRATEGY_REQUIRED_SECTIONS = [
    "Hybrid Configuration",
    "Reranking",
    "Narrowing Decision",
    "Pipeline",
]

MAX_SUBMISSION_BYTES = 1_000_000  # 1MB
MIN_SUBMISSION_BYTES = 5_000      # 5KB — below this, files are probably empty
MAX_FILE_COUNT = 50
MAX_SINGLE_FILE_LINES = 2000

# Patterns that indicate leaked secrets
SECRET_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub PAT"),
    (r"ghu_[a-zA-Z0-9]{36}", "GitHub user token"),
    (r"QDRANT_API_KEY\s*=\s*(?!os\.|Secret|None|getenv|environ|\"|\')[A-Za-z0-9_\-]{8,}", "Qdrant API key"),
    (r"GOOGLE_API_KEY\s*=\s*(?!os\.|Secret|None|getenv|environ|\"|\')[A-Za-z0-9_\-]{8,}", "Google API key"),
    (r"ANTHROPIC_API_KEY\s*=\s*(?!os\.|Secret|None|getenv|environ|\"|\')[A-Za-z0-9_\-]{8,}", "Anthropic API key"),
    (r"VOYAGE_API_KEY\s*=\s*(?!os\.|Secret|None|getenv|environ|\"|\')[A-Za-z0-9_\-]{8,}", "Voyage API key"),
    (r"Bearer\s+[a-zA-Z0-9\-_.]{20,}", "Bearer token"),
    (r"password\s*=\s*['\"][^'\"]{8,}['\"]", "Hardcoded password"),
]

# Patterns indicating raw data or large artifacts leaked into submission
DATA_BLOAT_PATTERNS = [
    (r"^FILE:\s+.*data/raw/", "data/raw/ files included — check .gitingestignore"),
    (r"^FILE:\s+.*data/processed/", "data/processed/ files included — check .gitingestignore"),
    (r"^FILE:\s+.*\.env$", ".env file included — secrets may be exposed"),
    (r"^FILE:\s+.*\.csv$", "CSV file included — should be in .gitingestignore"),
    (r"^FILE:\s+.*\.parquet$", "Parquet file included — should be in .gitingestignore"),
    (r"^FILE:\s+.*\.npy$", "NumPy file included — should be in .gitingestignore"),
    (r"^FILE:\s+.*rag_results/.*\.json$", "RAG results JSON included — should be in .gitingestignore (too large)"),
    (r"^FILE:\s+.*archive/", "Archive files included — should be in .gitingestignore"),
    (r"^FILE:\s+.*prequalify\.py$", "Prequalify script included — add to .gitingestignore"),
    (r"^FILE:\s+.*submission_guidelines\.md$", "Submission guidelines included — add to .gitingestignore"),
    (r"^FILE:\s+.*data_preparation/outputs/", "data_preparation/outputs/ files included (file metadata JSON, 620KB) — check .gitingestignore"),
]

# Items that MUST be in .gitingestignore
REQUIRED_IGNORE_ENTRIES = [
    "archive/",
    "rag_results/",
    "data_preparation/outputs/",
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


def check_retrieval_analysis_sections() -> tuple[bool, list[str]]:
    """Check retrieval-analysis.md for required sections, accepting 'Assessment' as alternate for 'Narrowing'."""
    file_path = WEEK_DIR / "docs" / "retrieval-analysis.md"
    if not file_path.exists():
        return False, RETRIEVAL_ANALYSIS_REQUIRED_SECTIONS

    content = file_path.read_text()
    missing = []
    for section in RETRIEVAL_ANALYSIS_REQUIRED_SECTIONS:
        pattern = rf"(^#+\s*{re.escape(section)}|^\*\*{re.escape(section)}\*\*)"
        found = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
        if not found:
            if section.lower() not in content.lower():
                # For "Narrowing", also accept "Assessment" as an alternate
                if section == "Narrowing":
                    alt_pattern = rf"(^#+\s*Assessment|^\*\*Assessment\*\*)"
                    alt_found = re.search(alt_pattern, content, re.MULTILINE | re.IGNORECASE)
                    if alt_found or "assessment" in content.lower():
                        continue
                missing.append(section)

    label = "docs/retrieval-analysis.md"
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

    match = re.search(
        r"##\s*Student\s*Name(?:\(s\)|s)?\s*\n+(.*?)(?=\n##|\Z)",
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

    names = []
    for line in name_block.splitlines():
        line = line.strip().lstrip("- ").lstrip("* ").strip()
        if line and not line.startswith("["):
            for name in line.split(","):
                name = name.strip()
                if name:
                    names.append(name)

    if not names:
        print(f"  FAIL  No student names found in submission.md")
        return False, []

    incomplete = [n for n in names if len(n.split()) < 2]
    if incomplete:
        print(f"  FAIL  Each student must have full name (first + last): {', '.join(incomplete)}")
        return False, names

    print(f"  PASS  Student name(s): {', '.join(names)}")
    return True, names


def check_eval_results_exist() -> bool:
    """Check that eval_results/ has at least one JSON file (the final evaluation)."""
    eval_dir = WEEK_DIR / "evaluations" / "eval_results"
    if not eval_dir.exists():
        print(f"  FAIL  evaluations/eval_results/ — directory not found. Keep your final eval JSON here for grading.")
        return False

    json_files = list(eval_dir.glob("*.json"))
    if len(json_files) == 0:
        print(f"  FAIL  evaluations/eval_results/ — no JSON files found. Keep your final eval output here.")
        return False

    total_size = sum(f.stat().st_size for f in json_files)
    total_kb = total_size / 1024
    print(f"  PASS  evaluations/eval_results/ — {len(json_files)} eval file(s), {total_kb:.0f}KB total")
    return True


def check_deep_analysis() -> bool:
    """Check that week3_deep_analysis.md has substantive judge reliability content."""
    analysis_path = WEEK_DIR / "evaluations" / "week3_deep_analysis.md"
    if not analysis_path.exists():
        print(f"  FAIL  evaluations/week3_deep_analysis.md — file not found")
        return False

    content = analysis_path.read_text()
    if len(content.strip()) < 200:
        print(f"  WARN  evaluations/week3_deep_analysis.md — file seems too short ({len(content)} chars). Did you spot-check the judge?")
        return False

    # Check for evidence of actual spot-checking
    spot_check_keywords = ["agree", "disagree", "manual", "spot", "check", "judge said", "my read", "missed"]
    found = sum(1 for kw in spot_check_keywords if kw in content.lower())

    if found >= 2:
        print(f"  PASS  evaluations/week3_deep_analysis.md — substantive judge analysis found")
        return True
    else:
        print(f"  WARN  evaluations/week3_deep_analysis.md — doesn't appear to contain judge spot-check analysis")
        return False


def check_gitingestignore_entries() -> bool:
    """Check that .gitingestignore has critical exclusions."""
    ignore_path = WEEK_DIR / ".gitingestignore"
    if not ignore_path.exists():
        return False

    content = ignore_path.read_text()
    missing = []
    for entry in REQUIRED_IGNORE_ENTRIES:
        # Check for the entry (with or without leading slash/glob)
        if entry not in content:
            missing.append(entry)

    if missing:
        print(f"  WARN  .gitingestignore — missing recommended entries: {', '.join(missing)}")
        print(f"        These directories contain large files that will bloat your submission")
        return False
    else:
        print(f"  PASS  .gitingestignore — critical exclusions present")
        return True


def check_submission_not_template() -> bool:
    submission_path = WEEK_DIR / "submission.md"
    if not submission_path.exists():
        return False

    content = submission_path.read_text()
    template_markers = [
        "[Full name",
        "[Same project as Week 1-2]",
        "[brief summary",
        "[what changed with chunking",
        "[what retrieval problem remained]",
    ]

    unfilled = [m for m in template_markers if m in content]
    if unfilled:
        print(f"  WARN  submission.md — still has template placeholders: {unfilled[0]}...")
        return False
    else:
        print(f"  PASS  submission.md — no template placeholders found")
        return True


def find_submission_txt() -> Path | None:
    """Find the submission .txt file in repo root matching naming convention."""
    candidates = list(REPO_ROOT.glob("*_week3_submission.txt"))
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        print(f"  FAIL  Multiple submission files found: {[c.name for c in candidates]}")
        return None
    return None


def check_submission_filename(names: list[str]) -> tuple[bool, Path | None]:
    """Check submission .txt exists and follows naming convention."""
    txt_path = find_submission_txt()

    if txt_path is None:
        print(f"  FAIL  No submission .txt found in repo root")
        print(f"        Expected: firstname_lastname_week3_submission.txt")
        print(f"        Run: uv run gitingest week-3/ -o <name>_week3_submission.txt")
        return False, None

    filename = txt_path.name

    if re.match(SUBMISSION_FILENAME_PATTERN, filename):
        print(f"  PASS  {filename} — naming convention correct")
        return True, txt_path

    print(f"  WARN  {filename} — does not match expected pattern")
    print(f"        Expected: firstname_lastname_week3_submission.txt")
    return False, txt_path


def check_submission_size(txt_path: Path) -> bool:
    size_bytes = txt_path.stat().st_size
    size_kb = size_bytes / 1024
    size_mb = size_bytes / (1024 * 1024)

    if size_bytes > MAX_SUBMISSION_BYTES:
        print(f"  FAIL  {txt_path.name} — {size_mb:.1f}MB (must be under 1MB). Check .gitingestignore.")
        return False
    elif size_bytes < MIN_SUBMISSION_BYTES:
        print(f"  WARN  {txt_path.name} — {size_kb:.0f}KB (suspiciously small, are your files empty?)")
        return False
    else:
        print(f"  PASS  {txt_path.name} — {size_kb:.0f}KB")
        return True


def check_file_count(txt_path: Path) -> bool:
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


def check_required_files_in_txt(txt_path: Path) -> bool:
    """Check that key files appear in the gitingest output."""
    content = txt_path.read_text()

    required_in_txt = [
        "submission.md",
        "retrieval-analysis.md",
        "retrieval-strategy.md",
        "iteration-log.md",
        "week3_comparison.md",
        "week3_deep_analysis.md",
    ]

    missing = []
    for filename in required_in_txt:
        if filename not in content:
            missing.append(filename)

    if missing:
        print(f"  FAIL  Required files missing from submission .txt: {', '.join(missing)}")
        return False
    else:
        print(f"  PASS  All required files found in submission .txt")
        return True


def check_no_secrets(txt_path: Path) -> bool:
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
    content = txt_path.read_text()
    found = []

    for pattern, label in DATA_BLOAT_PATTERNS:
        if re.search(pattern, content, re.MULTILINE):
            found.append(label)

    if found:
        print(f"  FAIL  Bloat detected in submission:")
        for f in found:
            print(f"        - {f}")
        return False
    else:
        print(f"  PASS  No bloat detected")
        return True


def check_large_files(txt_path: Path) -> bool:
    content = txt_path.read_text()
    file_sections = re.split(r"^={48}\nFILE:\s+(.+)\n={48}$", content, flags=re.MULTILINE)

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
    content = txt_path.read_text(errors="replace")

    base64_blobs = re.findall(r"[A-Za-z0-9+/=]{200,}", content)
    suspicious = [b for b in base64_blobs if len(b) > 500]
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
    print("  Week 3 Capstone — Pre-Submission Check")
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

    # 2. Gitingestignore contents
    print("\nGitingestignore check:")
    if not check_gitingestignore_entries():
        warnings = True

    # 3. Submission sections
    print("\nSubmission document sections:")
    passed, _ = check_sections(
        WEEK_DIR / "submission.md",
        SUBMISSION_REQUIRED_SECTIONS,
        "submission.md",
    )
    if not passed:
        all_passed = False

    # 4. Retrieval analysis sections
    print("\nRetrieval analysis sections:")
    passed, _ = check_retrieval_analysis_sections()
    if not passed:
        all_passed = False

    # 5. Retrieval strategy sections
    print("\nRetrieval strategy sections:")
    passed, _ = check_sections(
        WEEK_DIR / "docs" / "retrieval-strategy.md",
        RETRIEVAL_STRATEGY_REQUIRED_SECTIONS,
        "docs/retrieval-strategy.md",
    )
    if not passed:
        all_passed = False

    # 6. Student names
    print("\nStudent names:")
    names_passed, names = check_student_names()
    if not names_passed:
        all_passed = False

    # 7. Template check
    print("\nTemplate check:")
    if not check_submission_not_template():
        warnings = True

    # 8. Eval results JSON
    print("\nEval results:")
    if not check_eval_results_exist():
        all_passed = False

    # 9. Deep analysis
    print("\nDeep analysis:")
    if not check_deep_analysis():
        warnings = True

    # 10. Submission .txt naming and size
    print("\nSubmission file:")
    name_ok, txt_path = check_submission_filename(names)
    if not name_ok:
        all_passed = False

    if txt_path and txt_path.exists():
        if not check_submission_size(txt_path):
            all_passed = False

        # 11. Content checks on the .txt
        print("\nSubmission content checks:")
        if not check_required_files_in_txt(txt_path):
            all_passed = False
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
