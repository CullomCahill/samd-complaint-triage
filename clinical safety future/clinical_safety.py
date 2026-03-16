import json
import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

# Load data files
with open("call_1_defect_classification_results.json") as f:
    call_1_results = json.load(f)

with open("product_context.json") as f:
    product_context = json.load(f)

# Filter to only defects
defects = [r for r in call_1_results if r["is_defect"]]
non_defects = [r for r in call_1_results if not r["is_defect"]]

print(f"Loaded {len(call_1_results)} results from Call 1.")
print(f"Defects to process: {len(defects)}")
print(f"Non-defects skipped: {len(non_defects)}")
print()


def assess_clinical_safety(defect, bug_description):
    """LLM Call 2: Assess whether a defect has clinical safety implications."""

    safety_criteria = product_context["clinical_safety_criteria"]

    prompt = f"""You are a Clinical Safety Reviewer for a regulated mental health Software as Medical Device (SaMD) product called MindBridge, a CBT-based therapeutic chatbot.

Your task is to determine whether the following defect has potential clinical safety implications.

CLINICAL SAFETY CRITERIA:
{safety_criteria["description"]}

{json.dumps(safety_criteria["criteria"], indent=2)}

Note: {safety_criteria["note"]}

DEFECT TO ASSESS:
Bug ID: {defect["bug_id"]}
Defect Classification Summary: {defect["summary"]}
Failed Requirements: {defect["criterion_2_failed_requirements"]}
Failed User Needs: {defect["criterion_2_failed_user_needs"]}

ADDITIONAL BUG CONTEXT:
{bug_description}

INSTRUCTIONS:
1. Review each clinical safety criterion and determine if this defect could trigger it.
2. Err on the side of caution.  Flag as a potential safety concern if there is any reasonable possibility of clinical harm.
3. Provide a clear, one to two sentence rationale.

Respond in the following JSON format only, no other text:
{{
    "bug_id": "{defect["bug_id"]}",
    "has_clinical_safety_implications": true or false,
    "triggered_safety_criteria": ["CS-XXX", "CS-YYY"] or [],
    "rationale": "one to two sentence explanation of why this does or does not have clinical safety implications",
    "safety_severity": "critical" or "moderate" or "low" or "none"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = response.content[0].text

    cleaned = response_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    result = json.loads(cleaned)
    return result


def main():
    # Load original bug data to get descriptions
    with open("bug_data.json") as f:
        bug_data = json.load(f)

    # Handle both list format and wrapped format
    if isinstance(bug_data, dict) and "bugs" in bug_data:
        bug_list = bug_data["bugs"]
    else:
        bug_list = bug_data

    # Create lookup by bug ID
    bug_lookup = {b["id"]: b["description"] for b in bug_list}

    results = []

    for defect in defects:
        bug_id = defect["bug_id"]
        bug_description = bug_lookup.get(bug_id, "No additional description available.")

        print(f"Processing {bug_id}...")
        try:
            result = assess_clinical_safety(defect, bug_description)
            results.append(result)

            safety_flag = "SAFETY CONCERN" if result["has_clinical_safety_implications"] else "NO SAFETY CONCERN"
            print(f"  Result: {safety_flag} (severity: {result['safety_severity']})")
            if result["triggered_safety_criteria"]:
                print(f"  Triggered Criteria: {result['triggered_safety_criteria']}")
            print(f"  Rationale: {result['rationale']}")
            print()

        except Exception as e:
            print(f"  ERROR processing {bug_id}: {e}")
            print()

    # Save results
    with open("call_2_clinical_safety_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    safety_concerns = [r for r in results if r["has_clinical_safety_implications"]]
    no_concerns = [r for r in results if not r["has_clinical_safety_implications"]]
    print("=" * 60)
    print("CLINICAL SAFETY SCREEN COMPLETE")
    print(f"Defects assessed: {len(results)}")
    print(f"Safety concerns flagged: {len(safety_concerns)}")
    print(f"No safety concerns: {len(no_concerns)}")
    print()
    if safety_concerns:
        print("FLAGGED DEFECTS:")
        for r in safety_concerns:
            print(f"  {r['bug_id']} - {r['safety_severity'].upper()} - {r['triggered_safety_criteria']}")
    print(f"\nResults saved to call_2_clinical_safety_results.json")


if __name__ == "__main__":
    main()