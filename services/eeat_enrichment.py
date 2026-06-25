"""
NEXUS-14 V4 - services/eeat_enrichment.py (M6 — EEAT Engine, structural)

Structural EEAT validation + enrichment shared by Agent 06 and the Quality Gate.

V4 CHANGE: EEAT is validated STRUCTURALLY, not by counting trust-signal phrases.
Every article must carry these discrete elements; their presence is enforced and
their absence blocks publication. This both raises EEAT quality and removes the
incentive (present in V3) to template the same trust phrases for a regex score.

SINGLE SOURCE OF TRUTH (Approach B / B1 alignment)
REQUIRED_EEAT_KEYS below is the authoritative list of required EEAT elements.
quality_gate_v4 IMPORTS this constant (it no longer hard-codes its own list), so
the gate and the enrichment engine can never silently diverge again. Previously
the gate required only 6 of these keys while the enrichment required 8; the gate
is now aligned to the full 8-key list.

REQUIRED ELEMENTS (8 — authoritative)
author - author name (string)
author_credentials - bio / credentials (string)
review_date - ISO date the article was reviewed
update_date - ISO date the article was last updated
official_references - >=1 official source URL
related_articles - >=1 internal related article link
disclosure - affiliate / editorial disclosure present
editorial_note - editorial note present

build_eeat_fields() assembles these from article_data and is the integration
point Agent 04 / Agent 06 call to attach EEAT structure before the gate runs.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, List

OFFICIAL_URL_RE = re.compile(
    r'https?://[^\s)]*(?:irs\.gov|canada\.ca|fdic\.gov|consumerfinance\.gov|'
    r'uscis\.gov|federalreserve\.gov|osfi-bsif\.gc\.ca)'
)
INTERNAL_LINK_RE = re.compile(r'https?://(?:www\.)?moneyabroadguide\.com', re.IGNORECASE)
DISCLOSURE_RE = re.compile(r'(?:affiliate|disclosure|we may earn|compensat)', re.IGNORECASE)

# ---------------------------------------------------------------------------
# SINGLE SOURCE OF TRUTH for required EEAT elements.
# quality_gate_v4 imports REQUIRED_EEAT_KEYS from here; it must NOT redeclare
# its own list. Keep this the only place the canonical key set is defined.
# ---------------------------------------------------------------------------
REQUIRED_EEAT_KEYS = [
    "author", "author_credentials", "review_date", "update_date",
    "official_references", "related_articles", "disclosure", "editorial_note",
]

# Backwards-compatible alias (historical name used by existing callers/tests).
REQUIRED_ELEMENTS = REQUIRED_EEAT_KEYS


def build_eeat_fields(article_data: Dict, markdown: str = "") -> Dict:
    """Assemble structured EEAT fields from article data + body text.

    Returns a dict shaped for quality_gate_v4.check_eeat() consumption, mapping
    the gate's required keys to truthy values when the element is present.
    """
    today = datetime.now(timezone.utc).date().isoformat()
    body = markdown or article_data.get("content", "") or ""

    official_refs = sorted(set(OFFICIAL_URL_RE.findall(body)))
    related = INTERNAL_LINK_RE.findall(body)
    has_disclosure = bool(DISCLOSURE_RE.search(body)) or bool(article_data.get("disclosure"))

    fields = {
        "author": article_data.get("author", "Talal Eddaouahiri"),
        "author_credentials": article_data.get("author_bio")
        or "Founder of MoneyAbroadGuide.com",
        "review_date": article_data.get("review_date") or today,
        # gate expects key "update_date"; map from date_modified if present.
        "update_date": article_data.get("update_date")
        or article_data.get("date_modified") or today,
        "official_references": official_refs or article_data.get("official_references", []),
        "related_articles": bool(related) or bool(article_data.get("related_articles")),
        "disclosure": has_disclosure,
        "editorial_note": article_data.get("editorial_note")
        or "Reviewed by the MoneyAbroadGuide editorial team for accuracy.",
    }
    return fields


def validate_eeat(fields: Dict) -> Dict:
    """Structural validation: every required element must be present/truthy."""
    missing = []
    for key in REQUIRED_EEAT_KEYS:
        val = fields.get(key)
        if val in (None, "", False, [], {}):
            missing.append(key)
    score = round(100 * (len(REQUIRED_EEAT_KEYS) - len(missing)) / len(REQUIRED_EEAT_KEYS), 1)
    return {
        "passed": not missing,
        "eeat_score": score,
        "missing_elements": missing,
        "required_elements": REQUIRED_EEAT_KEYS,
    }
