# PR B — Priority 2: Country / Category Validation Gate (DRAFT PROPOSAL)

> **Draft proposal. Do NOT merge. Do NOT deploy. Do NOT push to main.** Human review required.
> Implements Priority 2 from the NEXUS-14 audit (Issue #4). Companion to PR #5 and PR-A.

## Problem identified

Canada content can be assigned to USA categories (and vice versa). There is currently **no validation anywhere** that an article's country matches its assigned WordPress category, and no gate that blocks publication on a mismatch.

## Root cause (from reading the real code)

- `agents/agent_03_content_planner.py` contains **no category logic at all** (grep for "categor" returns nothing) — category assignment is effectively unguarded.
- `scripts/v2_quality_gate.py` defines **18 gates**, none of which check country↔category consistency. Publication can proceed with a mismatched category.
- `config/article_strategy.json` (after PR #5) declares the *intent* (`category_safeguards`) but no executable gate enforces it.

## Proposed fix

Add a **new blocking Gate 19: Country/Category Consistency**, fed by a small validator that runs **before publication**. A mismatch is a **hard failure** (not a warning).

### New validator: `agents/agent_19_country_category_validator.py` (proposed)

```python
#!/usr/bin/env python3
"""Agent 19 - Country/Category Validator. Runs before publish. Blocking."""
import json, re, sys
from pathlib import Path

# WordPress category IDs/slugs grouped by country (load from config in real impl)
COUNTRY_CATEGORIES = {
    "US": {"banking-usa","credit-usa","insurance-usa","taxes-usa","money-transfer-usa","first-90-days-usa","driver-license-usa"},
    "CA": {"banking-canada","credit-canada","insurance-canada","taxes-canada","money-transfer-canada","first-90-days-canada","driver-license-canada"},
}
USA_TOKENS = {"usa","u.s.","america","irs","ssn","itin","fdic","uscis","401k","ira"}
CA_TOKENS  = {"canada","canadian","cra","rrsp","tfsa","sin","gc.ca","ontario","quebec"}

def detect_country(text):
    t = text.lower()
    ca = any(x in t for x in CA_TOKENS); us = any(x in t for x in USA_TOKENS)
    if ca and not us: return "CA"
    if us and not ca: return "US"
    if ca and us:     return "BOTH"
    return "UNKNOWN"

def validate(title, slug, assigned_categories):
    country = detect_country(title + " " + slug)
    issues = []
    for cat in assigned_categories:
        c = cat.lower()
        if country == "US" and c in COUNTRY_CATEGORIES["CA"]:
            issues.append(f"US article assigned CA category '{cat}'")
        if country == "CA" and c in COUNTRY_CATEGORIES["US"]:
            issues.append(f"CA article assigned US category '{cat}'")
    passed = len(issues) == 0 and country != "UNKNOWN"
    if country == "UNKNOWN":
        issues.append("Country could not be determined - manual review required")
    return {"country": country, "passed": passed, "issues": issues,
            "blocking": not passed}

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--title", required=True)
    p.add_argument("--slug", default="")
    p.add_argument("--categories", default="")  # comma separated
    p.add_argument("--output", default="output/agent_19/country_category_report.json")
    a = p.parse_args()
    cats = [c.strip() for c in a.categories.split(",") if c.strip()]
    res = validate(a.title, a.slug, cats)
    out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    sys.exit(1 if res["blocking"] else 0)

if __name__ == "__main__":
    main()
```

### Quality-gate patch: add Gate 19 to `scripts/v2_quality_gate.py`

```python
# GATE 19: Country/Category Consistency (Agent 19) - BLOCKING
cc = load_json_report(getattr(args, 'country_category_report', ''), "Country/Category")      if getattr(args, 'country_category_report', '') else {"_missing": True}
if cc.get("_missing"):
    cc_pass = False
    all_failures.append("GATE 19 FAIL: Country/Category report missing (Agent 19 not run)")
else:
    cc_pass = cc.get("passed", False)
gate_results["gate_19_country_category"] = {
    "gate": "19 - Country/Category Consistency (Agent 19)",
    "passed": cc_pass,
    "country": cc.get("country", "UNKNOWN"),
    "issues": cc.get("issues", []),
}
if not cc_pass and not cc.get("_missing"):
    all_failures.append(f"GATE 19 FAIL: {cc.get('issues')}")
```

Also add the CLI arg `--country-category-report` to `main()`, and wire Agent 19 into `production_v2.yml` before the publish step.

### Config: extend `config/article_strategy.json category_safeguards`

```json
"category_safeguards": {
  "enforced_as_gate": true,
  "gate": "Gate 19 - Country/Category Consistency",
  "country_category_map": {
    "US": ["banking-usa","credit-usa","insurance-usa","taxes-usa","money-transfer-usa","first-90-days-usa","driver-license-usa"],
    "CA": ["banking-canada","credit-canada","insurance-canada","taxes-canada","money-transfer-canada","first-90-days-canada","driver-license-canada"]
  },
  "on_mismatch": "BLOCK_PUBLICATION",
  "on_unknown_country": "BLOCK_REQUIRE_MANUAL_REVIEW"
}
```

## Files affected

- `docs/proposals/PR-B_country_category_gate.md` — **this PR**
- Follow-up application targets: new `agents/agent_19_country_category_validator.py`, `scripts/v2_quality_gate.py` (Gate 19 + CLI arg), `config/article_strategy.json`, `.github/workflows/production_v2.yml` (wire-in).

## Risk assessment

Low. Pure additive gate. Worst case is a false "UNKNOWN" stop requiring manual review — fail-safe. The real category IDs/slugs must be confirmed against the live WordPress taxonomy before applying.

## Expected SEO impact

Positive — correct country categorization improves topical clustering, breadcrumbs, and internal-link relevance; avoids confusing Google's understanding of the US vs CA sections.

## Expected content quality impact

Positive — readers land in the correct country section; no Canadian advice surfacing under US categories.

## Expected monetization impact

Positive — country-correct categories mean country-correct affiliate offers (e.g., RBC/Scotiabank for CA, Chase/Chime for US), improving conversion and avoiding irrelevant/ineligible offers.
