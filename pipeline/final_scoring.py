import json
from datetime import datetime

# Load all results
with open("call_1_defect_classification_results.json") as f:
    call_1_results = json.load(f)

with open("call_2_probability_results.json") as f:
    call_2_results = json.load(f)

with open("call_3_severity_results.json") as f:
    call_3_results = json.load(f)

with open("config/defect_criteria.json") as f:
    defect_context = json.load(f)

# Create lookups
probability_lookup = {r["bug_id"]: r for r in call_2_results}
severity_lookup = {r["bug_id"]: r for r in call_3_results}

# Risk level thresholds from defect criteria
risk_levels = defect_context["risk_matrix"]["risk_levels"]


def calculate_risk(probability_score, severity_score):
    """Deterministic risk calculation.  No LLM needed."""
    risk_score = probability_score * severity_score

    if risk_score >= 15:
        risk_level = "HIGH"
        disposition = "CAPA Required"
    elif risk_score >= 7:
        risk_level = "MEDIUM"
        disposition = "Complaint - evaluate for CAPA escalation"
    else:
        risk_level = "LOW"
        disposition = "Complaint - moderate timeline"

    return risk_score, risk_level, disposition


def build_final_report():
    """Combine all pipeline results into a final report."""

    report = {
        "report_title": "Complaint Review Board - Automated Triage Report",
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_bugs_reviewed": len(call_1_results),
            "non_defects": 0,
            "defects": 0,
            "capas_recommended": 0,
            "complaints_medium": 0,
            "complaints_low": 0
        },
        "non_defect_items": [],
        "defect_items": []
    }

    # Process non-defects
    for item in call_1_results:
        if not item["is_defect"]:
            report["summary"]["non_defects"] += 1
            report["non_defect_items"].append({
                "bug_id": item["bug_id"],
                "classification": "NON-DEFECT",
                "rationale": item["summary"],
                "action": "No further action required.  Fix at team discretion."
            })

    # Process defects
    for item in call_1_results:
        if not item["is_defect"]:
            continue

        report["summary"]["defects"] += 1
        bug_id = item["bug_id"]

        probability = probability_lookup.get(bug_id, {})
        severity = severity_lookup.get(bug_id, {})

        prob_score = probability.get("probability_score", 0)
        sev_score = severity.get("severity_score", 0)

        risk_score, risk_level, disposition = calculate_risk(prob_score, sev_score)

        if "CAPA" in disposition:
            report["summary"]["capas_recommended"] += 1
        elif risk_level == "MEDIUM":
            report["summary"]["complaints_medium"] += 1
        else:
            report["summary"]["complaints_low"] += 1

        defect_entry = {
            "bug_id": bug_id,
            "classification": "DEFECT",
            "failed_requirements": item["criterion_2_failed_requirements"],
            "failed_user_needs": item["criterion_2_failed_user_needs"],
            "defect_summary": item["summary"],
            "risk_assessment": {
                "probability_score": prob_score,
                "probability_label": probability.get("probability_label", "not assessed"),
                "probability_rationale": probability.get("rationale", "not assessed"),
                "severity_score": sev_score,
                "severity_label": severity.get("severity_label", "not assessed"),
                "severity_rationale": severity.get("rationale", "not assessed"),
                "risk_score": risk_score,
                "risk_level": risk_level
            },
            "disposition": disposition
        }

        report["defect_items"].append(defect_entry)

    # Sort defects by risk score descending so highest risk is at the top
    report["defect_items"].sort(key=lambda x: x["risk_assessment"]["risk_score"], reverse=True)

    return report


def print_report(report):
    """Print a readable version of the report to the terminal."""

    print("=" * 70)
    print(f"  {report['report_title']}")
    print(f"  Generated: {report['generated_at']}")
    print("=" * 70)
    print()

    s = report["summary"]
    print(f"  SUMMARY")
    print(f"  Total bugs reviewed:      {s['total_bugs_reviewed']}")
    print(f"  Non-defects:              {s['non_defects']}")
    print(f"  Defects:                  {s['defects']}")
    print(f"  CAPAs recommended:        {s['capas_recommended']}")
    print(f"  Complaints (medium risk): {s['complaints_medium']}")
    print(f"  Complaints (low risk):    {s['complaints_low']}")
    print()

    # Print CAPAs first
    print("-" * 70)
    print("  RECOMMENDED CAPAs (highest risk defects)")
    print("-" * 70)
    for item in report["defect_items"]:
        if "CAPA" in item["disposition"]:
            ra = item["risk_assessment"]
            print()
            print(f"  {item['bug_id']}")
            print(f"  Risk Score: {ra['risk_score']} ({ra['risk_level']})")
            print(f"  Probability: {ra['probability_score']} ({ra['probability_label']})  |  Severity: {ra['severity_score']} ({ra['severity_label']})")
            print(f"  Failed Requirements: {item['failed_requirements']}")
            print(f"  Disposition: {item['disposition']}")
            print(f"  Summary: {item['defect_summary']}")

    # Print medium risk complaints
    print()
    print("-" * 70)
    print("  COMPLAINTS - MEDIUM RISK")
    print("-" * 70)
    medium_items = [i for i in report["defect_items"] if i["risk_assessment"]["risk_level"] == "MEDIUM"]
    if not medium_items:
        print("  None")
    for item in medium_items:
        ra = item["risk_assessment"]
        print()
        print(f"  {item['bug_id']}")
        print(f"  Risk Score: {ra['risk_score']} ({ra['risk_level']})")
        print(f"  Probability: {ra['probability_score']} ({ra['probability_label']})  |  Severity: {ra['severity_score']} ({ra['severity_label']})")
        print(f"  Disposition: {item['disposition']}")
        print(f"  Summary: {item['defect_summary']}")

    # Print low risk complaints
    print()
    print("-" * 70)
    print("  COMPLAINTS - LOW RISK")
    print("-" * 70)
    low_items = [i for i in report["defect_items"] if i["risk_assessment"]["risk_level"] == "LOW"]
    if not low_items:
        print("  None")
    for item in low_items:
        ra = item["risk_assessment"]
        print()
        print(f"  {item['bug_id']}")
        print(f"  Risk Score: {ra['risk_score']} ({ra['risk_level']})")
        print(f"  Probability: {ra['probability_score']} ({ra['probability_label']})  |  Severity: {ra['severity_score']} ({ra['severity_label']})")
        print(f"  Disposition: {item['disposition']}")
        print(f"  Summary: {item['defect_summary']}")

    # Print non-defects
    print()
    print("-" * 70)
    print("  NON-DEFECTS (no further action required)")
    print("-" * 70)
    for item in report["non_defect_items"]:
        print()
        print(f"  {item['bug_id']}")
        print(f"  Rationale: {item['rationale']}")

    print()
    print("=" * 70)
    print("  END OF REPORT")
    print("=" * 70)


def main():
    report = build_final_report()

    # Save full report as JSON
    with open("final_triage_report.json", "w") as f:
        json.dump(report, f, indent=2)

    # Print readable report
    print_report(report)

    print()
    print(f"Full report saved to final_triage_report.json")


if __name__ == "__main__":
    main()