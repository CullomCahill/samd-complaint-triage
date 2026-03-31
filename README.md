# AI Bug Triage Pipeline — MindBridge SaMD

An automated complaint triage pipeline for a regulated Software as a Medical Device (SaMD) environment. Built around a fictional mental health chatbot called **MindBridge** as a toy example of a real workflow used in production at a mental health SaMD company.

Each incoming bug is run through four sequential LLM calls — one per step, one per bug — and assembled into a final triage report suitable for a Complaint Review Board.

See `flow_diagram.html` (open in any browser) for a visual of the pipeline.

---

## Setup

**Requirements:** `uv`, an Anthropic API key

```bash
uv sync
```

To add new dependencies later, use:

```bash
uv add <package-name>
```

Add your API key to a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your_key_here
```

**Run the full pipeline:**

```bash
uv run run_pipeline
```

`run_pipeline.py` runs a preflight check before making any API calls — it verifies all required input files exist and are non-empty, and that the API key is set. If anything is missing, it exits with a clear error message.

---

## Developer Commands

Run an individual step:

```bash
uv run complaint_triage
uv run probability
uv run severity
uv run final_scoring
```

Environment and dependency maintenance:

```bash
uv sync
uv lock
uv add <package-name>
```

---

## Input Files

| File                     | Purpose                                                       |
| ------------------------ | ------------------------------------------------------------- |
| `bug_data.json`          | Bug tickets to be triaged (the input)                         |
| `product_context.json`   | User needs and product requirements (compliance artifacts)    |
| `defect_criteria.json`   | SOP defect criteria, risk matrix, severity/probability scales |
| `bug_data_training.json` | Reference dataset used when building the model                |

---

## Pipeline — Four Steps

Each step is its own script. Each script makes **one LLM call per bug** and outputs a structured JSON file that feeds into the next step. The `bug_id` field links records across all outputs.

### Step 1 — `complaint_triage.py`

**Defect Classification**

Determines whether a bug is a formal defect using a two-criterion gate directly from the SOP:

1. Is the bug present in the released product?
2. Does it deviate from intended function — i.e., does it violate a User Need or Product Requirement?

Both must be true to classify as a defect. Outputs which specific requirements failed.

→ Output: `call_1_defect_classification_results.json`

### Step 2 — `probability.py`

**Probability Assessment**

Scores the likelihood that a user will encounter the defect (1–5 scale). Uses the defect classification output plus the original bug data. The probability and severity assessments are intentionally kept in separate LLM calls so neither influences the other.

→ Output: `call_2_probability_results.json`

### Step 3 — `severity.py`

**Severity Assessment**

Scores the realistic impact if the defect occurs (1–5 scale). For a mental health SaMD, this includes factors like psychological distress to a vulnerable user, crisis intervention scenarios, and PHI exposure.

→ Output: `call_3_severity_results.json`

### Step 4 — `final_scoring.py`

**Risk Scoring and Report — No LLM involved**

Combines all prior outputs. Risk score = probability × severity on a 5×5 matrix. Assembles a final triage report grouped by risk level:

| Risk Score | Action                                   |
| ---------- | ---------------------------------------- |
| 1–6        | Complaint — standard resolution timeline |
| 7–14       | Complaint — consider CAPA                |
| 15–25      | Defect — CAPA required                   |

→ Output: `final_triage_report.json`

---

## Output

`final_triage_report.json` contains:

- Summary counts (total bugs, defects, non-defects, CAPAs recommended)
- Non-defect items with rationale
- Defect items with failed requirements, risk score, and recommended action

Each step's intermediate output file is retained so any assessment can be traced back through the pipeline using `bug_id`.

---

## Limitations

- **Toy scale:** 15 product requirements, not hundreds. A production version would route each bug to its relevant feature category first, then pull only those requirements into context.
- **Manual fields:** Some bug ticket fields (e.g., `in_released_product`) rely on manual data entry and are prone to human error.
- **Tool validation:** In a real SaMD product, this pipeline would require tool validation before use in a regulated process. Since it preprocesses information for human review rather than making final decisions, this should be a manageable lift — though RAQA teams may have opinions.

---

## Future Considerations

- **Clinical safety routing:** Flag bugs for clinical safety review before the standard triage flow — particularly relevant for crisis detection or PHI-adjacent issues.
- **Feature category routing:** Determine the feature area of a bug first, then pull only the relevant subset of requirements into the LLM context.
- **Historical dataset:** Probability and severity assessments would become significantly more accurate with a dataset of past bugs and their real-world user impact.
- **eQMS integration:** In production, `product_context.json` would likely be replaced by a live call to your eQMS API.
