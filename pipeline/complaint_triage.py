import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv
load_dotenv()

client = Anthropic()

# Load data files
with open("examples/bug_data.json") as f:
    bugs = json.load(f)["bugs"]

with open("config/product_context.json") as f:
    product_context = json.load(f)

with open("config/defect_criteria.json") as f:
    defect_criteria = json.load(f)["defect_criteria"] # nested in json object


from pipeline.costs import INPUT_COST_PER_TOKEN, OUTPUT_COST_PER_TOKEN


def classify_defect(bug):
    """LLM Call 1: Determine if a bug is a defect or non-defect."""

    # Strip 'expected_' answer key fields before sending to LLM
    clean_bug = {
        "id": bug["id"],
        "title": bug["title"],
        "description": bug["description"],
        "component": bug["component"],
        "reported_by": bug["reported_by"],
        "date_reported": bug["date_reported"],
        "in_released_product": bug["in_released_product"],
        "related_feature": bug["related_feature"]
    }

    prompt = f"""You are a Quality Engineer performing defect classification for a regulated mental health Software as Medical 
    Device (SaMD) product called MindBridge.

Your task is to determine whether the following bug qualifies as a DEFECT based on the defect criteria provided.

DEFECT CRITERIA (both must be true for a bug to be a defect):
1. {defect_criteria["must_meet_both"][0]}
2. {defect_criteria["must_meet_both"][1]}

USER NEEDS:
{json.dumps(product_context["user_needs"], indent=2)}

PRODUCT REQUIREMENTS:
{json.dumps(product_context["product_requirements"], indent=2)}

BUG TO CLASSIFY:
{json.dumps(clean_bug, indent=2)}

INSTRUCTIONS:
1. First assess whether this bug is present in the released product.
2. Then assess whether this bug represents a deviation from the intended function by checking it against the user needs and product requirements.
3. Both criteria must be met for it to be a defect.

Respond in the following JSON format only, no other text:
{{
    "bug_id": "{bug["id"]}",
    "is_defect": true or false,
    "criterion_1_in_released_product": true or false,
    "criterion_1_rationale": "one sentence explaining why this is or is not in the released product",
    "criterion_2_deviates_from_intended_function": true or false,
    "criterion_2_failed_requirements": ["PR-XXX", "PR-YYY"] or [],
    "criterion_2_failed_user_needs": ["UN-XXX"] or [],
    "criterion_2_rationale": "one to two sentences explaining which requirements or user needs are failed and why, or why none are failed",
    "summary": "two to three sentence summary of the overall finding suitable for presentation at a Complaint Review Board meeting"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = response.content[0].text

    # Clean up response in case of markdown fencing
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
    results = []
    total_input_tokens = 0
    total_output_tokens = 0

    for bug in bugs:
        print(f"Processing {bug['id']}: {bug['title']}...")
        try:
            result, usage = classify_defect(bug)
            results.append(result)
            total_input_tokens += usage.input_tokens
            total_output_tokens += usage.output_tokens

            status = "DEFECT" if result["is_defect"] else "NON-DEFECT"
            print(f"  Result: {status}")
            if result["is_defect"]:
                print(f"  Failed Requirements: {result['criterion_2_failed_requirements']}")
            print(f"  Summary: {result['summary']}")
            print()

        except Exception as e:
            print(f"  ERROR processing {bug['id']}: {e}")
            print()

    # Save results
    with open("call_1_defect_classification_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    defects = [r for r in results if r["is_defect"]]
    non_defects = [r for r in results if not r["is_defect"]]
    print("=" * 60)
    print(f"CLASSIFICATION COMPLETE")
    print(f"Total bugs processed: {len(results)}")
    print(f"Defects: {len(defects)}")
    print(f"Non-defects: {len(non_defects)}")
    print(f"Results saved to call_1_defect_classification_results.json")
    input_cost = total_input_tokens * INPUT_COST_PER_TOKEN
    output_cost = total_output_tokens * OUTPUT_COST_PER_TOKEN
    print(f"\nToken Usage (Step 1):")
    print(f"  Input tokens:  {total_input_tokens:,}  (${input_cost:.4f})")
    print(f"  Output tokens: {total_output_tokens:,}  (${output_cost:.4f})")
    print(f"  Step total:    ${input_cost + output_cost:.4f}")

    with open("usage_step1.json", "w") as f:
        json.dump({
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_cost": input_cost + output_cost
        }, f)


if __name__ == "__main__":
    main()