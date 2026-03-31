import json
import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

# Load data files
with open("call_1_defect_classification_results.json") as f:
    call_1_results = json.load(f)

with open("config/defect_criteria.json") as f:
    defect_context = json.load(f)

# Filter to only defects
defects = [r for r in call_1_results if r["is_defect"]]

print(f"Loaded {len(defects)} defects for probability assessment.")
print()

# Get probability scale from risk matrix
probability_scale = defect_context["risk_matrix"]["probability"]


from pipeline.costs import INPUT_COST_PER_TOKEN, OUTPUT_COST_PER_TOKEN


def assess_probability(defect, bug_data):
    """LLM Call 3: Assess the probability score for a defect."""

    prompt = f"""You are a Quality Engineer performing a risk probability assessment for a regulated mental health Software as Medical Device (SaMD) product called MindBridge, a CBT-based therapeutic chatbot.

Your task is to assess the PROBABILITY that this defect will occur for users of the product.

PROBABILITY SCALE:
1 - Remote: unlikely to occur
2 - Low: could occur but rare
3 - Moderate: may occur occasionally
4 - High: likely to occur
5 - Very High: almost certain to occur

FACTORS TO CONSIDER:
- How many users are likely to encounter the conditions that trigger this bug?
- Is it tied to a common user action or an edge case?
- How frequently would the triggering conditions occur in normal use?
- How many reports have been received (if mentioned)?
- Does it affect all users or a specific subset (certain OS, certain usage pattern, etc.)?

DEFECT TO ASSESS:
Bug ID: {defect["bug_id"]}
Classification Summary: {defect["summary"]}
Failed Requirements: {defect["criterion_2_failed_requirements"]}

ORIGINAL BUG DETAILS:
Title: {bug_data["title"]}
Description: {bug_data["description"]}
Component: {bug_data["component"]}
Reported By: {bug_data["reported_by"]}

INSTRUCTIONS:
Assess the probability that a user of the MindBridge product will encounter this defect during normal use.  Base your assessment on the evidence available in the bug report, considering the factors listed above.  Do not speculate beyond what is stated.

Respond in the following JSON format only, no other text:
{{
    "bug_id": "{defect["bug_id"]}",
    "probability_score": 1 to 5,
    "probability_label": "Remote" or "Low" or "Moderate" or "High" or "Very High",
    "rationale": "two to three sentence explanation grounded in specific evidence from the bug report"
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
    return result, response.usage


def main():
    # Load original bug data for descriptions
    with open("examples/bug_data.json") as f:
        bug_data = json.load(f)

    if isinstance(bug_data, dict) and "bugs" in bug_data:
        bug_list = bug_data["bugs"]
    else:
        bug_list = bug_data

    bug_lookup = {b["id"]: b for b in bug_list}

    results = []
    total_input_tokens = 0
    total_output_tokens = 0

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
            result, usage = assess_probability(defect, clean_bug)
            results.append(result)
            total_input_tokens += usage.input_tokens
            total_output_tokens += usage.output_tokens

            print(f"  Probability: {result['probability_score']} - {result['probability_label']}")
            print(f"  Rationale: {result['rationale']}")
            print()

        except Exception as e:
            print(f"  ERROR processing {bug_id}: {e}")
            print()

    # Save results
    with open("call_2_probability_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("=" * 60)
    print("PROBABILITY ASSESSMENT COMPLETE")
    print(f"Defects assessed: {len(results)}")
    print()
    print("DISTRIBUTION:")
    for score in range(1, 6):
        count = len([r for r in results if r["probability_score"] == score])
        label = probability_scale[str(score)]
        print(f"  {score} ({label}): {count}")
    print(f"\nResults saved to call_2_probability_results.json")
    input_cost = total_input_tokens * INPUT_COST_PER_TOKEN
    output_cost = total_output_tokens * OUTPUT_COST_PER_TOKEN
    print(f"\nToken Usage (Step 2):")
    print(f"  Input tokens:  {total_input_tokens:,}  (${input_cost:.4f})")
    print(f"  Output tokens: {total_output_tokens:,}  (${output_cost:.4f})")
    print(f"  Step total:    ${input_cost + output_cost:.4f}")

    with open("usage_step2.json", "w") as f:
        json.dump({
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_cost": input_cost + output_cost
        }, f)


if __name__ == "__main__":
    main()