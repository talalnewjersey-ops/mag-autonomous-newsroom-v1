#!/usr/bin/env python3
"""
NEXUS-14 V3 - Gate 19: Country / Category Validation Gate
MoneyAbroadGuide.com | Priority 2 implementation (Issue #4, PR #7).

Purpose
-------
Block publication when an article's detected country does not match the
country implied by its assigned WordPress category (e.g. a USA article placed
in the "Newcomers to Canada" category, or vice-versa).

Authority model
---------------
Deterministic. The country is derived from content signals (shared with
Agent 17). Category->country mapping is loaded from config and MUST reflect
real production WordPress category IDs/slugs. On UNKNOWN/AMBIGUOUS country,
the gate does NOT silently pass: it returns a MANUAL_REVIEW result.

Rollout
-------
Defaults to mode="warning" (records mismatch, does not block) so results can be
collected over real runs. Switch to mode="blocking" only AFTER the mapping is
confirmed and warning-mode logs are clean.

VERIFIED MAPPING (read-only GET /wp-json/wp/v2/categories on 2026-06-22):
    id  7  Banking               banking               (country-neutral)
    id 12  Taxes                 taxes                 (country-neutral)
    id 17  Newcomers to the USA  newcomers-to-the-usa  -> USA
    id 18  Newcomers to Canada   newcomers-to-canada   -> CANADA
Only IDs 17 and 18 are country-bound. Neutral categories never trigger a
country conflict. Any category ID/slug NOT present in the map is treated as
UNKNOWN -> MANUAL_REVIEW (never assume).
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [GATE-19] %(levelname)s %(message)s")
logger = logging.getLogger("gate_19_country_category")

# Shared country detection signals (kept in sync with Agent 17).
COUNTRY_SIGNALS = {
    "USA": ["usa", "u.s.", "u.s.a", "united states", "america", "american",
            "irs", "ssn", "itin", "social security", "green card", "i-94",
            "dmv", "401k", "fafsa", "medicaid", "medicare", "fdic",
            "chase", "wells fargo", "bank of america", "zelle"],
    "CANADA": ["canada", "canadian", "cra", "sin number", "social insurance",
               "rrsp", "tfsa", "gic", "interac", "newcomer to canada",
               "permanent resident", "pr card", "service canada", "cdic",
               "td canada", "rbc", "scotiabank", "cibc"],
}

# Default mapping — VERIFIED against production on 2026-06-22.
# Override via --category-map <json> to avoid hardcoding in other environments.
DEFAULT_CATEGORY_COUNTRY_MAP = {
    "by_id": {"17": "USA", "18": "CANADA", "7": "NEUTRAL", "12": "NEUTRAL"},
    "by_slug": {
        "newcomers-to-the-usa": "USA",
        "newcomers-to-canada": "CANADA",
        "banking": "NEUTRAL",
        "taxes": "NEUTRAL",
    },
}


def detect_country(*texts):
    blob = " ".join(t for t in texts if t).lower()
    scores = {c: sum(1 for s in sig if s in blob) for c, sig in COUNTRY_SIGNALS.items()}
    usa, can = scores["USA"], scores["CANADA"]
    if usa == 0 and can == 0:
        return "UNKNOWN"
    if usa > 0 and can > 0 and abs(usa - can) <= 1:
        return "AMBIGUOUS"
    return "USA" if usa > can else "CANADA"


def category_country(cat_id, cat_slug, cmap):
    if cat_id is not None and str(cat_id) in cmap.get("by_id", {}):
        return cmap["by_id"][str(cat_id)]
    if cat_slug and cat_slug in cmap.get("by_slug", {}):
        return cmap["by_slug"][cat_slug]
    return "UNKNOWN"  # never assume an unmapped category


def validate(content_text, title, slug, categories, cmap, mode="warning"):
    """categories: list of {id, slug} dicts assigned to the article."""
    detected = detect_country(title or "", slug or "", content_text or "")
    cat_results = []
    conflict = False
    unmapped = False

    for cat in categories or []:
        cc = category_country(cat.get("id"), cat.get("slug"), cmap)
        is_conflict = (
            detected in ("USA", "CANADA")
            and cc in ("USA", "CANADA")
            and detected != cc
        )
        if cc == "UNKNOWN":
            unmapped = True
        if is_conflict:
            conflict = True
        cat_results.append({"id": cat.get("id"), "slug": cat.get("slug"),
                            "category_country": cc, "conflict": is_conflict})

    if detected in ("UNKNOWN", "AMBIGUOUS"):
        verdict, blocking = "MANUAL_REVIEW", (mode == "blocking")
        reason = f"Country detection inconclusive ({detected}); manual review required."
    elif conflict:
        verdict, blocking = "FAIL", (mode == "blocking")
        reason = "Country/category mismatch: article country differs from assigned category country."
    elif unmapped:
        verdict, blocking = "MANUAL_REVIEW", (mode == "blocking")
        reason = "Article assigned to a category not present in the verified mapping; manual review required."
    else:
        verdict, blocking = "PASS", False
        reason = "Country matches all country-bound categories."

    return {
        "gate": "19 - Country / Category Validation",
        "mode": mode,
        "detected_country": detected,
        "categories": cat_results,
        "verdict": verdict,
        "blocking": blocking,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Gate 19 - Country/Category Validation")
    parser.add_argument("--content", default="", help="path to article text/html (optional)")
    parser.add_argument("--title", default="")
    parser.add_argument("--slug", default="")
    parser.add_argument("--categories", default="[]",
                        help='JSON list, e.g. [{"id":17,"slug":"newcomers-to-the-usa"}]')
    parser.add_argument("--category-map", default="", help="path to JSON override of the category->country map")
    parser.add_argument("--mode", default="warning", choices=["warning", "blocking"])
    parser.add_argument("--output", default="output/gate_19/country_category_result.json")
    args = parser.parse_args()

    cmap = DEFAULT_CATEGORY_COUNTRY_MAP
    if args.category_map:
        cmap = json.loads(Path(args.category_map).read_text())

    content_text = ""
    if args.content and Path(args.content).exists():
        content_text = re.sub(r"<[^>]+>", " ", Path(args.content).read_text())

    categories = json.loads(args.categories)
    result = validate(content_text, args.title, args.slug, categories, cmap, mode=args.mode)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    logger.info(f"VERDICT: {result['verdict']} | blocking={result['blocking']} | {result['reason']}")

    sys.exit(1 if result["blocking"] else 0)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
NEXUS-14 V3 - Gate 19: Country / Category Validation Gate
MoneyAbroadGuide.com | Priority 2 implementation (Issue #4, PR #7).

Purpose
-------
Block publication when an article's detected country does not match the
country implied by its assigned WordPress category (e.g. a USA article placed
in the "Newcomers to Canada" category, or vice-versa).

Authority model
---------------
Deterministic. The country is derived from content signals (shared with
Agent 17). Category->country mapping is loaded from config and MUST reflect
real production WordPress category IDs/slugs. On UNKNOWN/AMBIGUOUS country,
the gate does NOT silently pass: it returns a MANUAL_REVIEW result.

Rollout
-------
Defaults to mode="warning" (records mismatch, does not block) so results can be
collected over real runs. Switch to mode="blocking" only AFTER the mapping is
confirmed and warning-mode logs are clean.

VERIFIED MAPPING (read-only GET /wp-json/wp/v2/categories on 2026-06-22):
    id  7  Banking               banking               (country-neutral)
    id 12  Taxes                 taxes                 (country-neutral)
    id 17  Newcomers to the USA  newcomers-to-the-usa  -> USA
    id 18  Newcomers to Canada   newcomers-to-canada   -> CANADA
Only IDs 17 and 18 are country-bound. Neutral categories never trigger a
country conflict. Any category ID/slug NOT present in the map is treated as
UNKNOWN -> MANUAL_REVIEW (never assume).
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [GATE-19] %(levelname)s %(message)s")
logger = logging.getLogger("gate_19_country_category")

# Shared country detection signals (kept in sync with Agent 17).
COUNTRY_SIGNALS = {
    "USA": ["usa", "u.s.", "u.s.a", "united states", "america", "american",
            "irs", "ssn", "itin", "social security", "green card", "i-94",
            "dmv", "401k", "fafsa", "medicaid", "medicare", "fdic",
            "chase", "wells fargo", "bank of america", "zelle"],
    "CANADA": ["canada", "canadian", "cra", "sin number", "social insurance",
               "rrsp", "tfsa", "gic", "interac", "newcomer to canada",
               "permanent resident", "pr card", "service canada", "cdic",
               "td canada", "rbc", "scotiabank", "cibc"],
}

# Default mapping — VERIFIED against production on 2026-06-22.
# Override via --category-map <json> to avoid hardcoding in other environments.
DEFAULT_CATEGORY_COUNTRY_MAP = {
    "by_id": {"17": "USA", "18": "CANADA", "7": "NEUTRAL", "12": "NEUTRAL"},
    "by_slug": {
        "newcomers-to-the-usa": "USA",
        "newcomers-to-canada": "CANADA",
        "banking": "NEUTRAL",
        "taxes": "NEUTRAL",
    },
}


def detect_country(*texts):
    blob = " ".join(t for t in texts if t).lower()
    scores = {c: sum(1 for s in sig if s in blob) for c, sig in COUNTRY_SIGNALS.items()}
    usa, can = scores["USA"], scores["CANADA"]
    if usa == 0 and can == 0:
        return "UNKNOWN"
    if usa > 0 and can > 0 and abs(usa - can) <= 1:
        return "AMBIGUOUS"
    return "USA" if usa > can else "CANADA"


def category_country(cat_id, cat_slug, cmap):
    if cat_id is not None and str(cat_id) in cmap.get("by_id", {}):
        return cmap["by_id"][str(cat_id)]
    if cat_slug and cat_slug in cmap.get("by_slug", {}):
        return cmap["by_slug"][cat_slug]
    return "UNKNOWN"  # never assume an unmapped category


def validate(content_text, title, slug, categories, cmap, mode="warning"):
    """categories: list of {id, slug} dicts assigned to the article."""
    detected = detect_country(title or "", slug or "", content_text or "")
    cat_results = []
    conflict = False
    unmapped = False

    for cat in categories or []:
        cc = category_country(cat.get("id"), cat.get("slug"), cmap)
        is_conflict = (
            detected in ("USA", "CANADA")
            and cc in ("USA", "CANADA")
            and detected != cc
        )
        if cc == "UNKNOWN":
            unmapped = True
        if is_conflict:
            conflict = True
        cat_results.append({"id": cat.get("id"), "slug": cat.get("slug"),
                            "category_country": cc, "conflict": is_conflict})

    if detected in ("UNKNOWN", "AMBIGUOUS"):
        verdict, blocking = "MANUAL_REVIEW", (mode == "blocking")
        reason = f"Country detection inconclusive ({detected}); manual review required."
    elif conflict:
        verdict, blocking = "FAIL", (mode == "blocking")
        reason = "Country/category mismatch: article country differs from assigned category country."
    elif unmapped:
        verdict, blocking = "MANUAL_REVIEW", (mode == "blocking")
        reason = "Article assigned to a category not present in the verified mapping; manual review required."
    else:
        verdict, blocking = "PASS", False
        reason = "Country matches all country-bound categories."

    return {
        "gate": "19 - Country / Category Validation",
        "mode": mode,
        "detected_country": detected,
        "categories": cat_results,
        "verdict": verdict,
        "blocking": blocking,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Gate 19 - Country/Category Validation")
    parser.add_argument("--content", default="", help="path to article text/html (optional)")
    parser.add_argument("--title", default="")
    parser.add_argument("--slug", default="")
    parser.add_argument("--categories", default="[]",
                        help='JSON list, e.g. [{"id":17,"slug":"newcomers-to-the-usa"}]')
    parser.add_argument("--category-map", default="", help="path to JSON override of the category->country map")
    parser.add_argument("--mode", default="warning", choices=["warning", "blocking"])
    parser.add_argument("--output", default="output/gate_19/country_category_result.json")
    args = parser.parse_args()

    cmap = DEFAULT_CATEGORY_COUNTRY_MAP
    if args.category_map:
        cmap = json.loads(Path(args.category_map).read_text())

    content_text = ""
    if args.content and Path(args.content).exists():
        content_text = re.sub(r"<[^>]+>", " ", Path(args.content).read_text())

    categories = json.loads(args.categories)
    result = validate(content_text, args.title, args.slug, categories, cmap, mode=args.mode)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    logger.info(f"VERDICT: {result['verdict']} | blocking={result['blocking']} | {result['reason']}")

    sys.exit(1 if result["blocking"] else 0)


if __name__ == "__main__":
    main()
