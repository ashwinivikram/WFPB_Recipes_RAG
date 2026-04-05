import os
import sys

REQUIRED_FILES = [
    "docs/evaluation-scope.md",
    "docs/evaluation-ground-truth.md",
    "docs/evaluation-strategy.md",
    "docs/iteration-log.md",
    "evaluations/golden_dataset.json",
    "evaluations/method_results/deterministic_results.json",
    "evaluations/method_results/decomposed_results.json",
    "evaluations/triangulation_analysis.md",
    "scripts/12_build_golden_dataset.py",
    "scripts/13_run_deterministic_eval.py",
    "scripts/14_run_judge_eval.py",
    "traces/trace.md"
]

print("============================================================")
print("  Week 4 Capstone — Pre-Submission Check")
print("============================================================\n")

missing = []
for f in REQUIRED_FILES:
    if os.path.exists(f):
        print(f"  PASS  {f}")
    else:
        print(f"  FAIL  {f} is missing")
        missing.append(f)

if missing:
    print("\n[ERROR] Missing required files.")
    sys.exit(1)

print("\nGenerating submission file...")
os.system("uvx gitingest . -o ashwini_vikram_week4_submission.txt")
print("PASS  ashwini_vikram_week4_submission.txt generated.")
print("\n============================================================")
print("  All checks passed. Ready to submit.")
print("============================================================")
