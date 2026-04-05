"""
Week 4 Capstone Pre-Submission Check
=====================================

Run this before submitting to catch structural issues, bloat, and secrets.

Usage (from your capstone repo root):
    uv run python week-4/prequalify.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Resolve week-4/ directory (script lives inside it)
WEEK_DIR = Path(__file__).resolve().parent
REPO_ROOT = WEEK_DIR

# Expected filename: firstname_lastname_week4_submission.txt
SUBMISSION_FILENAME_PATTERN = r"^[a-z]+(_[a-z]+)+_week4_submission\.txt$"

REQUIRED_FILES = {
    "submission.md": "Your main submission document",
    "docs/evaluation-strategy.md": "Evaluation methods, golden dataset methodology, metrics justification",
    "docs/judge-design.md": "Judge rubric, criteria, prompt evolution with deltas",
    "docs/iteration-log.md": "Iteration log -- what you tried, changed, and learned",
    "evaluations/week4_comparison.md": "Cross-method comparison and triangulation analysis",
    "evaluations/week4_deep_analysis.md": "Judge design critique, spot-checked disagreements, structural biases",
    ".gitingestignore": "Gitingest ignore rules",
}

SUBMISSION_REQUIRED_SECTIONS = [
    "Student Name",
    "Project Title",
    "Progress Recap",
    "Golden Dataset Summary",
    "Evaluation Methods",
    "Judge Design Summary",
    "Evaluation Results Summary",
    "Triangulation Findings",
    "Judge Design Evolution",
    "Key Observations",
    "Iteration Summary",
    "Self-Assessment",
]

EVAL_STRATEGY_REQUIRED_SECTIONS = [
    "Evaluation Methods",
    "Golden Dataset",
    "Metrics",
]

JUDGE_DESIGN_REQUIRED_SECTIONS = [
    "Metrics",
    "Rubric",
    "Evolution",
]

MAX_SUBMISSION_BYTES = 1_000_000  # 1MB
MIN_SUBMISSION_BYTES = 5_000      # 5KB -- below this, files are probably empty
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
    (r"^FILE:\s+.*data/raw/", "data/raw/ files included -- check .gitingestignore"),
    (r"^FILE:\s+.*data/processed/", "data/processed/ files included -- check .gitingestignore"),
    (r"^FILE:\s+.*\.env$", ".env file included -- secrets may be exposed"),
    (r"^FILE:\s+.*\.csv$", "CSV file included -- should be in .gitingestignore"),
    (r"^FILE:\s+.*\.parquet$", "Parquet file included -- should be in .gitingestignore"),
    (r"^FILE:\s+.*\.npy$", "NumPy file included -- should be in .gitingestignore"),
    (r"^FILE:\s+.*\.pkl$", "Pickle file included -- should be in .gitingestignore"),
    (r"^FILE:\s+.*rag_results/.*\.json$", "RAG results JSON included -- should be in .gitingestignore (too large)"),
    (r"^FILE:\s+.*archive/", "Archive files included -- should be in .gitingestignore"),
    (r"^FILE:\s+.*prequalify\.py$", "Prequalify script included -- add to .gitingestignore"),
    (r"^FILE:\s+.*submission_guidelines\.md$", "Submission guidelines included -- add to .gitingestignore"),
]

# Items that MUST be in .gitingestignore
REQUIRED_IGNORE_ENTRIES = [
    "archive/",
    "rag_results/",
]


def check_file_exists(rel_path: str, description: str) -> bool:
    path = WEEK_DIR / rel_path
    if path.exists():
        print(f"  PASS  {rel_path}")
        return True
    else:
        print(f"  FAIL  {rel_path} -- {description}")
        return False


def check_has_scripts() -> bool:
    scripts_dir = WEEK_DIR / "scripts"
    if not scripts_dir.exists():
        print(f"  FAIL  scripts/ -- directory not found")
        return False
    py_files = list(scripts_dir.glob("*.py"))
    if len(py_files) == 0:
        print(f"  FAIL  scripts/ -- no Python files found")
        return False
    print(f"  PASS  scripts/ -- {len(py_files)} Python file(s)")
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
        print(f"  FAIL  {label} -- missing sections: {', '.join(missing)}")
        return False, missing
    else:
        print(f"  PASS  {label} -- all required sections present")
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


def check_golden_dataset() -> bool:
    """Check that golden_dataset.json exists and has meaningful entries."""
    gd_path = WEEK_DIR / "evaluations" / "golden_dataset.json"
    if not gd_path.exists():
        print(f"  FAIL  evaluations/golden_dataset.json -- file not found")
        return False

    try:
        data = json.loads(gd_path.read_text())
    except json.JSONDecodeError:
        print(f"  FAIL  evaluations/golden_dataset.json -- invalid JSON")
        return False

    # Handle both list format and dict-with-list format
    entries = data if isinstance(data, list) else data.get("questions", data.get("entries", []))

    if len(entries) < 5:
        print(f"  FAIL  evaluations/golden_dataset.json -- only {len(entries)} entries (minimum 5)")
        return False

    print(f"  PASS  evaluations/golden_dataset.json -- {len(entries)} entries")
    return True


def check_eval_results_exist() -> bool:
    """Check that eval_results/ has evaluation output from at least 2 methods."""
    eval_dir = WEEK_DIR / "evaluations" / "eval_results"
    if not eval_dir.exists():
        print(f"  FAIL  evaluations/eval_results/ -- directory not found. Keep your final eval outputs here for grading.")
        return False

    json_files = list(eval_dir.glob("*.json"))
    if len(json_files) == 0:
        print(f"  FAIL  evaluations/eval_results/ -- no JSON files found. Keep your evaluation outputs here.")
        return False

    if len(json_files) < 2:
        print(f"  WARN  evaluations/eval_results/ -- only {len(json_files)} eval file. Week 4 expects results from at least 2 methods.")

    total_size = sum(f.stat().st_size for f in json_files)
    total_kb = total_size / 1024
    print(f"  PASS  evaluations/eval_results/ -- {len(json_files)} eval file(s), {total_kb:.0f}KB total")
    return True


def check_deep_analysis() -> bool:
    """Check that week4_deep_analysis.md has substantive judge design critique."""
    analysis_path = WEEK_DIR / "evaluations" / "week4_deep_analysis.md"
    if not analysis_path.exists():
        print(f"  FAIL  evaluations/week4_deep_analysis.md -- file not found")
        return False

    content = analysis_path.read_text()
    if len(content.strip()) < 300:
        print(f"  WARN  evaluations/week4_deep_analysis.md -- file seems too short ({len(content)} chars)")
        return False

    # Check for evidence of judge iteration and spot-checking
    judge_design_keywords = ["v1", "v2", "delta", "changed", "improved", "iteration", "version"]
    spot_check_keywords = ["agree", "disagree", "manual", "spot", "check", "judge said", "my read", "bias"]

    judge_found = sum(1 for kw in judge_design_keywords if kw in content.lower())
    spot_found = sum(1 for kw in spot_check_keywords if kw in content.lower())

    if judge_found >= 2 and spot_found >= 2:
        print(f"  PASS  evaluations/week4_deep_analysis.md -- judge evolution and spot-check analysis found")
        return True
    elif judge_found >= 1 or spot_found >= 1:
        print(f"  WARN  evaluations/week4_deep_analysis.md -- may be thin on judge evolution ({judge_found} signals) or spot-checking ({spot_found} signals)")
        return True
    else:
        print(f"  WARN  evaluations/week4_deep_analysis.md -- doesn't appear to contain judge design critique or spot-checks")
        return False


def check_judge_design() -> bool:
    """Check that judge-design.md has substantive judge iteration content."""
    judge_path = WEEK_DIR / "docs" / "judge-design.md"
    if not judge_path.exists():
        print(f"  FAIL  docs/judge-design.md -- file not found")
        return False

    content = judge_path.read_text()
    if len(content.strip()) < 200:
        print(f"  WARN  docs/judge-design.md -- file seems too short ({len(content)} chars)")
        return False

    # Check for evidence of iteration (v1/v2/delta language)
    iteration_keywords = ["v1", "v2", "version", "iteration", "delta", "changed", "evolved", "initial", "final"]
    found = sum(1 for kw in iteration_keywords if kw in content.lower())

    if found >= 3:
        print(f"  PASS  docs/judge-design.md -- judge iteration documented")
        return True
    elif found >= 1:
        print(f"  WARN  docs/judge-design.md -- limited evidence of judge iteration ({found} signals). Document how your judge changed across versions.")
        return True
    else:
        print(f"  WARN  docs/judge-design.md -- no evidence of judge iteration. Week 4 expects documented evolution of your judge design.")
        return False


def check_comparison() -> bool:
    """Check that week4_comparison.md has cross-method triangulation."""
    comp_path = WEEK_DIR / "evaluations" / "week4_comparison.md"
    if not comp_path.exists():
        print(f"  FAIL  evaluations/week4_comparison.md -- file not found")
        return False

    content = comp_path.read_text()
    if len(content.strip()) < 200:
        print(f"  WARN  evaluations/week4_comparison.md -- file seems too short ({len(content)} chars)")
        return False

    # Check for triangulation language
    triangulation_keywords = ["agree", "disagree", "method", "compare", "triangul", "cross", "reliable", "bias"]
    found = sum(1 for kw in triangulation_keywords if kw in content.lower())

    if found >= 3:
        print(f"  PASS  evaluations/week4_comparison.md -- cross-method analysis found")
        return True
    else:
        print(f"  WARN  evaluations/week4_comparison.md -- limited triangulation analysis ({found} signals)")
        return True


def check_gitingestignore_entries() -> bool:
    """Check that .gitingestignore has critical exclusions."""
    ignore_path = WEEK_DIR / ".gitingestignore"
    if not ignore_path.exists():
        return False

    content = ignore_path.read_text()
    missing = []
    for entry in REQUIRED_IGNORE_ENTRIES:
        if entry not in content:
            missing.append(entry)

    if missing:
        print(f"  WARN  .gitingestignore -- missing recommended entries: {', '.join(missing)}")
        print(f"        These directories contain large files that will bloat your submission")
        return False
    else:
        print(f"  PASS  .gitingestignore -- critical exclusions present")
        return True


def check_submission_not_template() -> bool:
    submission_path = WEEK_DIR / "submission.md"
    if not submission_path.exists():
        return False

    content = submission_path.read_text()
    template_markers = [
        "[Full name",
        "[Same project as Weeks 1-3]",
        "[data scoping baseline]",
        "[which Week 3 system",
        "[name] -- [what it measures",
    ]

    unfilled = [m for m in template_markers if m in content]
    if unfilled:
        print(f"  WARN  submission.md -- still has template placeholders: {unfilled[0]}...")
        return False
    else:
        print(f"  PASS  submission.md -- no template placeholders found")
        return True


def find_submission_txt() -> Path | None:
    """Find the submission .txt file in repo root matching naming convention."""
    candidates = list(REPO_ROOT.glob("*_week4_submission.txt"))
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
        print(f"        Expected: firstname_lastname_week4_submission.txt")
        print(f"        Run: uv run gitingest week-4/ -o <name>_week4_submission.txt")
        return False, None

    filename = txt_path.name

    if re.match(SUBMISSION_FILENAME_PATTERN, filename):
        print(f"  PASS  {filename} -- naming convention correct")
        return True, txt_path

    print(f"  WARN  {filename} -- does not match expected pattern")
    print(f"        Expected: firstname_lastname_week4_submission.txt")
    return False, txt_path


def check_submission_size(txt_path: Path) -> bool:
    size_bytes = txt_path.stat().st_size
    size_kb = size_bytes / 1024
    size_mb = size_bytes / (1024 * 1024)

    if size_bytes > MAX_SUBMISSION_BYTES:
        print(f"  FAIL  {txt_path.name} -- {size_mb:.1f}MB (must be under 1MB). Check .gitingestignore.")
        return False
    elif size_bytes < MIN_SUBMISSION_BYTES:
        print(f"  WARN  {txt_path.name} -- {size_kb:.0f}KB (suspiciously small, are your files empty?)")
        return False
    else:
        print(f"  PASS  {txt_path.name} -- {size_kb:.0f}KB")
        return True


def check_file_count(txt_path: Path) -> bool:
    content = txt_path.read_text()
    file_headers = re.findall(r"^FILE:\s+", content, re.MULTILINE)
    count = len(file_headers)

    if count > MAX_FILE_COUNT:
        print(f"  FAIL  {count} files in submission (max {MAX_FILE_COUNT}) -- likely includes data files. Check .gitingestignore.")
        return False
    elif count == 0:
        print(f"  FAIL  No files found in submission .txt -- gitingest may have failed")
        return False
    else:
        print(f"  PASS  {count} files in submission")
        return True


def check_required_files_in_txt(txt_path: Path) -> bool:
    """Check that key files appear in the gitingest output."""
    content = txt_path.read_text()

    required_in_txt = [
        "submission.md",
        "evaluation-strategy.md",
        "judge-design.md",
        "iteration-log.md",
        "golden_dataset.json",
        "week4_comparison.md",
        "week4_deep_analysis.md",
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
        issues.append("Binary file markers found -- binary files should not be in submission")

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
    print("  Week 4 Capstone -- Pre-Submission Check")
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

    # 4. Evaluation strategy sections
    print("\nEvaluation strategy sections:")
    passed, _ = check_sections(
        WEEK_DIR / "docs" / "evaluation-strategy.md",
        EVAL_STRATEGY_REQUIRED_SECTIONS,
        "docs/evaluation-strategy.md",
    )
    if not passed:
        all_passed = False

    # 5. Judge design sections
    print("\nJudge design document:")
    if not check_judge_design():
        warnings = True

    # 6. Student names
    print("\nStudent names:")
    names_passed, names = check_student_names()
    if not names_passed:
        all_passed = False

    # 7. Template check
    print("\nTemplate check:")
    if not check_submission_not_template():
        warnings = True

    # 8. Golden dataset
    print("\nGolden dataset:")
    if not check_golden_dataset():
        all_passed = False

    # 9. Eval results
    print("\nEval results:")
    if not check_eval_results_exist():
        all_passed = False

    # 10. Deep analysis
    print("\nDeep analysis:")
    if not check_deep_analysis():
        warnings = True

    # 11. Comparison / triangulation
    print("\nComparison / triangulation:")
    if not check_comparison():
        warnings = True

    # 12. Submission .txt naming and size
    print("\nSubmission file:")
    name_ok, txt_path = check_submission_filename(names)
    if not name_ok:
        all_passed = False

    if txt_path and txt_path.exists():
        if not check_submission_size(txt_path):
            all_passed = False

        # 13. Content checks on the .txt
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
