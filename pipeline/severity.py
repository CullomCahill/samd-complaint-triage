import json
import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

# Load data files
with open("call_1_defect_classification_results.json") as f:
    call_1_results = json.load(f)

with open("defect_criteria.json") as f:
    defect_context = json.load(f)

# Filter to only defects
defects = [r for r in call_1_results if r["is_defect"]]

print(f"Loaded {len(defects)} defects for severity assessment.")
print()

severity_scale = defect_context["risk_matrix"]["severity"]


def assess_severity(defect, bug_data):
    """LLM Call 3: Assess the severity score for a defect."""

    prompt = f"""You are a Quality Engineer performing a risk severity assessment for a regulated mental health Software as Medical Device (SaMD) product called MindBridge, a CBT-based therapeutic chatbot.

Your task is to assess the SEVERITY of harm that could result if this defect occurs.

SEVERITY SCALE:
1 - Negligible: no impact on therapeutic experience
2 - Minor: slight inconvenience, user can continue
3 - Moderate: disrupts session but user can recover
4 - Major: prevents therapeutic function or causes distress
5 - Critical: potential for clinical harm or safety event

FACTORS TO CONSIDER:
- What is the worst realistic outcome if a user encounters this defect?
- Does it prevent the user from completing a therapeutic task?
- Could it cause psychological distress to a vulnerable user?
- Does it involve patient safety or crisis intervention?
- Does it involve protected health information (PHI)?
- Does it undermine the clinical efficacy of the therapeutic intervention?

DEFECT TO ASSESS:
Bug ID: {defect["bug_id"]}
Classification Summary: {defect["summary"]}
Failed Requirements: {defect["criterion_2_failed_requirements"]}
Failed User Needs: {defect["criterion_2_failed_user_needs"]}

ORIGINAL BUG DETAILS:
Title: {bug_data["title"]}
Description: {bug_data["description"]}
Component: {bug_data["component"]}
Reported By: {bug_data["reported_by"]}

INSTRUCTIONS:
Assess the severity of harm that could result from this defect.  Ground your rationale in the specific impact on users of a mental health therapeutic product.  Be realistic and do not inflate severity beyond what is supported by the evidence.

Respond in the following JSON format only, no other text:
{{
    "bug_id": "{defect["bug_id"]}",
    "severity_score": 1 to 5,
    "severity_label": "Negligible" or "Minor" or "Moderate" or "Major" or "Critical",
    "rationale": "two to three sentence explanation focused on the realistic impact to the user"
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
    # Load original bug data
    with open("bug_data.json") as f:
        bug_data = json.load(f)

    if isinstance(bug_data, dict) and "bugs" in bug_data:
        bug_list = bug_data["bugs"]
    else:
        bug_list = bug_data

    bug_lookup = {b["id"]: b for b in bug_list}

    results = []

    for defect in defects:
        bug_id = defect["bug_id"]
        bug = bug_lookup.get(bug_id)

        if not bug:
            print(f"  WARNING: No bug data found for {bug_id}, skipping.")
            continue

        # Strip answer key fields
        clean_bug = {
            "id": bug["id"],
            "title": bug["title"],
            "description": bug["description"],
            "component": bug["component"],
            "reported_by": bug["reported_by"],
            "date_reported": bug["date_reported"],
            "related_feature": bug["related_feature"]
        }

        print(f"Processing {bug_id}: {bug['title']}...")
        try:
            result = assess_severity(defect, clean_bug)
            results.append(result)

            print(f"  Severity: {result['severity_score']} - {result['severity_label']}")
            print(f"  Rationale: {result['rationale']}")
            print()

        except Exception as e:
            print(f"  ERROR processing {bug_id}: {e}")
            print()

    # Save results
    with open("call_3_severity_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("=" * 60)
    print("SEVERITY ASSESSMENT COMPLETE")
    print(f"Defects assessed: {len(results)}")
    print()
    print("DISTRIBUTION:")
    for score in range(1, 6):
        count = len([r for r in results if r["severity_score"] == score])
        label = severity_scale[str(score)]
        print(f"  {score} ({label}): {count}")
    print(f"\nResults saved to call_3_severity_results.json")


if __name__ == "__main__":
    main()