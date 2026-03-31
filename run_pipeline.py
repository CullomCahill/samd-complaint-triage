import json
import subprocess
import sys
import time
import os

steps = [
    {
        "script": "pipeline/complaint_triage.py",
        "name": "Step 1: Defect Classification",
        "output_file": "call_1_defect_classification_results.json"
    },
    {
        "script": "pipeline/probability.py",
        "name": "Step 2: Probability Assessment",
        "output_file": "call_2_probability_results.json"
    },
    {
        "script": "pipeline/severity.py",
        "name": "Step 3: Severity Assessment",
        "output_file": "call_3_severity_results.json"
    },
    {
        "script": "pipeline/final_scoring.py",
        "name": "Step 4: Risk Scoring and Report Generation",
        "output_file": "final_triage_report.json"
    }
]

# Files that must exist before the pipeline starts
required_input_files = [
    "examples/bug_data.json",
    "config/product_context.json",
    "config/defect_criteria.json",
    ".env"
]

# Script files that must exist
required_scripts = [s["script"] for s in steps]


def preflight_check():
    """Verify all required files exist before spending money on API calls."""
    print("=" * 70)
    print("  PREFLIGHT CHECK")
    print("=" * 70)
    print()

    all_good = True

    # Check input data files
    print("  Input data files:")
    for f in required_input_files:
        if os.path.exists(f):
            size = os.path.getsize(f)
            if size == 0:
                print(f"    EMPTY  {f} (file exists but is 0 bytes)")
                all_good = False
            else:
                print(f"    OK     {f} ({size} bytes)")
        else:
            print(f"    MISSING  {f}")
            all_good = False

    print()

    # Check script files
    print("  Pipeline scripts:")
    for f in required_scripts:
        if os.path.exists(f):
            print(f"    OK     {f}")
        else:
            print(f"    MISSING  {f}")
            all_good = False

    print()

    # Check API key is set
    print("  Environment:")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        # Check .env file directly in case dotenv hasn't loaded yet
        if os.path.exists(".env"):
            with open(".env") as ef:
                content = ef.read()
                if "ANTHROPIC_API_KEY" in content and "=" in content:
                    key_value = content.split("ANTHROPIC_API_KEY=")[1].strip().split("\n")[0]
                    if len(key_value) > 0:
                        print(f"    OK     ANTHROPIC_API_KEY found in .env")
                    else:
                        print(f"    MISSING  ANTHROPIC_API_KEY is empty in .env")
                        all_good = False
                else:
                    print(f"    MISSING  ANTHROPIC_API_KEY not found in .env")
                    all_good = False
        else:
            print(f"    MISSING  ANTHROPIC_API_KEY not set and no .env file found")
            all_good = False
    else:
        print(f"    OK     ANTHROPIC_API_KEY is set")

    print()

    if not all_good:
        print("  PREFLIGHT FAILED.  Fix the issues above before running.")
        print("=" * 70)
        sys.exit(1)
    else:
        print("  All checks passed.  Starting pipeline.")
        print("=" * 70)
        print()


def run_pipeline():
    preflight_check()

    print("=" * 70)
    print("  COMPLAINT TRIAGE PIPELINE")
    print("  Starting full run...")
    print("=" * 70)
    print()

    start_time = time.time()

    for i, step in enumerate(steps):
        step_start = time.time()
        print(f"{'=' * 70}")
        print(f"  {step['name']}")
        print(f"  Running: {step['script']}")
        print(f"{'=' * 70}")
        print()

        result = subprocess.run(
            [sys.executable, step["script"]],
            capture_output=False
        )

        step_elapsed = time.time() - step_start

        if result.returncode != 0:
            print(f"\n  PIPELINE FAILED at {step['name']}")
            print(f"  Exit code: {result.returncode}")
            sys.exit(1)

        print(f"\n  Completed in {step_elapsed:.1f} seconds.")
        print(f"  Output: {step['output_file']}")
        print()

    total_elapsed = time.time() - start_time

    usage_files = ["usage_step1.json", "usage_step2.json", "usage_step3.json"]
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    for path in usage_files:
        if os.path.exists(path):
            with open(path) as f:
                u = json.load(f)
                total_input_tokens += u["input_tokens"]
                total_output_tokens += u["output_tokens"]
                total_cost += u["total_cost"]

    print("=" * 70)
    print(f"  PIPELINE COMPLETE")
    print(f"  Total time: {total_elapsed:.1f} seconds")
    print(f"  Final report: final_triage_report.json")
    print()
    print(f"  Token Usage (all steps):")
    print(f"    Input tokens:  {total_input_tokens:,}")
    print(f"    Output tokens: {total_output_tokens:,}")
    print(f"    Total cost:    ${total_cost:.4f}")
    print("=" * 70)


def main():
    run_pipeline()


if __name__ == "__main__":
    main()