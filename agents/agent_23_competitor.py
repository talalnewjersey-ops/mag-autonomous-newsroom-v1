#!/usr/bin/env python3
"""
NEXUS-14 V4 - Agent 23: Competitor Engine  (M8 — SECONDARY / interface)

STATUS: Information-Gain analysis engine + report contract implemented. The live
SERP scrape of the top-10 Google competitors is a documented runtime integration
point (Option A scope): it requires authorized SERP API access (SerpAPI is already
an env var in this repo) and fetching competitor pages, which cannot be validated
in this environment.

The agent therefore:
  * If competitor corpus is supplied (--competitors competitors.json), it computes
    Information Gain, entity coverage, missing FAQs/tables/examples/references, and
    search-intent coverage, then decides PASS/FAIL.
  * If no competitor corpus is supplied, it emits status="PENDING" + passed=False
    so the Quality Gate BLOCKS (no silent pass).

The entity/coverage analysis below is REAL and runs offline against any supplied
competitor text; only the *acquisition* of competitor text is the integration point.

REPORT CONTRACT (consumed by scripts/quality_gate_v4.py::_consult_report)
  output/agent_23/competitor_report.json
  { "passed": bool, "status": "PASS|FAIL|PENDING", "information_gain": float,
    "missing": {...}, "coverage": {...} }

RUNTIME INTEGRATION POINT  fetch_competitors():
  Use SERPAPI_KEY to query the keyword, take the top 10 organic URLs, fetch and
  extract main text for each, and pass them as competitors.json:
    [{"url": "...", "title": "...", "text": "..."}]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from services.content_similarity import token_set, classify_intent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("agent_23")

# Minimum fraction of competitor entities our article must also cover.
ENTITY_COVERAGE_MIN = 0.70
# Article must add at least this fraction of NEW tokens vs competitors (info gain).
INFORMATION_GAIN_MIN = 0.20

_FAQ_RE = re.compile(r'##\s+(?:FAQ|Frequently Asked Questions)', re.IGNORECASE)
_TABLE_RE = re.compile(r'(?:\|.*\|.*\n)|(<table)', re.IGNORECASE)
_EXAMPLE_RE = re.compile(r'(?:case stud|for example|real-world|example:)', re.IGNORECASE)
_OFFICIAL_RE = re.compile(r'https?://[^\s)]*(?:irs\.gov|canada\.ca|fdic\.gov|consumerfinance\.gov|uscis\.gov)')


def _entities(text: str) -> set:
    """Coarse entity proxy: significant multi-char tokens (no stopwords)."""
    return {t for t in token_set(text) if len(t) > 4}


def information_gain(article_text: str, competitor_texts: List[str]) -> float:
    comp_entities = set()
    for t in competitor_texts:
        comp_entities |= _entities(t)
    art_entities = _entities(article_text)
    if not art_entities:
        return 0.0
    new_entities = art_entities - comp_entities
    return len(new_entities) / len(art_entities)


def entity_coverage(article_text: str, competitor_texts: List[str]) -> float:
    comp_entities = set()
    for t in competitor_texts:
        comp_entities |= _entities(t)
    if not comp_entities:
        return 1.0
    art_entities = _entities(article_text)
    return len(art_entities & comp_entities) / len(comp_entities)


def missing_components(article_text: str, competitors: List[Dict]) -> Dict:
    art = article_text
    comp_has_faq = any(_FAQ_RE.search(c.get("text", "")) for c in competitors)
    comp_has_table = any(_TABLE_RE.search(c.get("text", "")) for c in competitors)
    comp_has_example = any(_EXAMPLE_RE.search(c.get("text", "")) for c in competitors)
    comp_has_official = any(_OFFICIAL_RE.search(c.get("text", "")) for c in competitors)
    return {
        "faq": comp_has_faq and not _FAQ_RE.search(art),
        "table": comp_has_table and not _TABLE_RE.search(art),
        "examples": comp_has_example and not _EXAMPLE_RE.search(art),
        "official_references": comp_has_official and not _OFFICIAL_RE.search(art),
    }


def run_competitor_check(article_text: str,
                         competitors: Optional[List[Dict]],
                         keyword: str = "",
                         output_path: str = "output/agent_23/competitor_report.json") -> Dict:
    if not competitors:
        report = {
            "agent": "agent_23_competitor",
            "version": "4.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "PENDING",
            "passed": False,
            "detail": "No competitor corpus supplied; gate must not pass on PENDING.",
        }
        _write(report, output_path)
        return report

    comp_texts = [c.get("text", "") for c in competitors]
    ig = information_gain(article_text, comp_texts)
    cov = entity_coverage(article_text, comp_texts)
    missing = missing_components(article_text, competitors)
    intent_match = classify_intent(keyword or article_text[:200])

    regenerate = [k for k, v in missing.items() if v]
    passed = (
        ig >= INFORMATION_GAIN_MIN
        and cov >= ENTITY_COVERAGE_MIN
        and not regenerate
    )
    report = {
        "agent": "agent_23_competitor",
        "version": "4.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "information_gain": round(ig, 4),
        "entity_coverage": round(cov, 4),
        "thresholds": {"information_gain_min": INFORMATION_GAIN_MIN,
                       "entity_coverage_min": ENTITY_COVERAGE_MIN},
        "search_intent": intent_match,
        "missing": missing,
        "regenerate_sections": regenerate,
        "competitors_analyzed": len(competitors),
    }
    _write(report, output_path)
    logger.info("Agent 23 status=%s ig=%.3f cov=%.3f missing=%s",
                report["status"], ig, cov, regenerate)
    return report


def _write(report: Dict, output_path: str) -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def fetch_competitors(keyword: str) -> Optional[List[Dict]]:
    """RUNTIME INTEGRATION POINT: SERP scrape of top-10 competitors.

    Implement in CI using SERPAPI_KEY. Returning None here means "no data" so the
    gate blocks rather than passing on missing competitor analysis.
    """
    logger.info("fetch_competitors() is a CI integration point (SERPAPI). keyword=%s", keyword)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent 23 - Competitor Engine (V4)")
    parser.add_argument("--input", required=True, help="article markdown/text file")
    parser.add_argument("--competitors", help="JSON list of {url,title,text}")
    parser.add_argument("--keyword", default="")
    parser.add_argument("--output", default="output/agent_23/competitor_report.json")
    args = parser.parse_args()

    article_text = Path(args.input).read_text(encoding="utf-8")
    competitors = None
    if args.competitors and Path(args.competitors).exists():
        competitors = json.loads(Path(args.competitors).read_text(encoding="utf-8"))
    elif args.keyword:
        competitors = fetch_competitors(args.keyword)

    report = run_competitor_check(article_text, competitors, args.keyword, args.output)
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
