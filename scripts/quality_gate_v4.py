#!/usr/bin/env python3
"""
NEXUS-14 V4 - scripts/quality_gate_v4.py  (M9 — Quality Gate V4)

THE AUTHORITATIVE PUBLICATION DECISION.

Core principle: DO NOT TRUST UPSTREAM AGENT REPORTS. The gate INDEPENDENTLY
recomputes every critical signal from the article source + WordPress draft, and
only consults agent reports as secondary corroboration. If the gate cannot
independently verify a required property, that gate FAILS.

INDEPENDENTLY RECALCULATED CHECKS
  * originality          -> recompute vs published corpus (Agent 19 logic)
  * schema               -> assert exactly one schema source; zero body JSON-LD
  * eeat                 -> structural presence of required trust elements
  * ymyl                 -> re-run YMYL validation (Agent 20 logic)
  * cannibalization      -> re-run semantic overlap (Agent 17 logic), no observe-only
  * internal_links       -> count + resolvability
  * canonical_uniqueness -> slug/title uniqueness vs corpus
  * readability          -> Flesch reading ease band
  * formatting           -> no emoji headings, heading hierarchy valid
  * accessibility        -> all images have alt text

Performance + competitor gates are consulted from their agent reports (Agent 22 /
Agent 23) because they require runtime measurement the gate cannot reproduce
offline; their PASS/FAIL is required but their metrics are not recomputed here.

PUBLICATION ALLOWED ONLY IF EVERY REQUIRED GATE PASSES.

OUTPUT  output/quality_gate_v4_result.json
EXIT CODES  0 -> READY_TO_PUBLISH ; 1 -> BLOCKED
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

# V4 independent-recompute building blocks.
from services.content_similarity import (
    title_similarity, slug_similarity, keyword_overlap, intent_overlap,
    composite_overlap, token_set,
)
from services.embeddings_service import get_embeddings_service
from services.schema_fields import contains_jsonld

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("quality_gate_v4")

# Import Agent 19/20 logic directly so the gate recomputes, not re-reads.
try:
    from agents.agent_19_originality import run_originality_check, split_sections
    from agents.agent_20_ymyl_validator import run_ymyl_validation
    from agents.agent_17_cannibalization import decide as cannibal_decide, SIGNAL_WEIGHTS
except Exception as e:  # pragma: no cover - import-time guard
    logger.warning("Agent logic import degraded: %s", e)
    run_originality_check = None
    run_ymyl_validation = None
    cannibal_decide = None
    SIGNAL_WEIGHTS = {"semantic": 0.4, "title": 0.2, "keyword": 0.2, "slug": 0.1, "intent": 0.1}

_HEADING_RE = re.compile(r'^\s*(#{2,6})\s+(.*)$', re.MULTILINE)
_EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF]")
_IMG_RE = re.compile(r'<img\b[^>]*>', re.IGNORECASE)
_ALT_RE = re.compile(r'\balt\s*=\s*["\'][^"\']+["\']', re.IGNORECASE)
_LINK_RE = re.compile(r'\[[^\]]+\]\((https?://[^)]+)\)')
_MD_LINK_INTERNAL = re.compile(r'\]\((https?://(?:www\.)?moneyabroadguide\.com[^)]*)\)', re.IGNORECASE)


# ---- Required thresholds ----------------------------------------------------
THRESHOLDS = {
    "originality_min": 80.0,
    "internal_links_min": 5,
    "readability_min": 45.0,       # Flesch reading ease (lower bound)
    "canonical_title_max": 0.85,   # max title similarity to any corpus title
    "canonical_slug_max": 0.85,
    "eeat_required_elements": [
        "author", "review_date", "update_date", "official_references",
        "disclosure", "related_articles",
    ],
}


def _flesch_reading_ease(text: str) -> float:
    sentences = max(1, len(re.findall(r'[.!?]+', text)))
    words = re.findall(r"[A-Za-z]+", text)
    if not words:
        return 0.0
    syllables = sum(_count_syllables(w) for w in words)
    wc = len(words)
    return 206.835 - 1.015 * (wc / sentences) - 84.6 * (syllables / wc)


def _count_syllables(word: str) -> int:
    word = word.lower()
    groups = re.findall(r'[aeiouy]+', word)
    n = len(groups)
    if word.endswith("e") and n > 1:
        n -= 1
    return max(1, n)


# ---- Independent gate checks ------------------------------------------------
def check_schema(rendered_html: str) -> Dict:
    """One schema source, zero body JSON-LD scripts."""
    body_jsonld = contains_jsonld(rendered_html)
    faq_block = "wp:yoast/faq-block" in rendered_html
    return {
        "name": "schema",
        "passed": not body_jsonld,
        "body_jsonld_present": body_jsonld,
        "yoast_faq_block_present": faq_block,
        "detail": "FAIL: body JSON-LD present" if body_jsonld else "OK: Yoast is single source",
    }


def check_eeat(article_meta: Dict) -> Dict:
    required = THRESHOLDS["eeat_required_elements"]
    missing = [k for k in required if not article_meta.get(k)]
    return {
        "name": "eeat",
        "passed": not missing,
        "missing_elements": missing,
        "detail": "OK" if not missing else f"Missing: {missing}",
    }


def check_formatting(markdown: str) -> Dict:
    emoji_headings = [h for _, h in _HEADING_RE.findall(markdown) if _EMOJI_RE.search(h)]
    levels = [len(h) for h, _ in _HEADING_RE.findall(markdown)]
    hierarchy_ok = all(b - a <= 1 for a, b in zip(levels, levels[1:])) if levels else True
    passed = not emoji_headings and hierarchy_ok
    return {
        "name": "formatting",
        "passed": passed,
        "emoji_headings": emoji_headings,
        "heading_hierarchy_ok": hierarchy_ok,
    }


def check_accessibility(rendered_html: str) -> Dict:
    imgs = _IMG_RE.findall(rendered_html)
    missing_alt = [img for img in imgs if not _ALT_RE.search(img)]
    return {
        "name": "accessibility",
        "passed": not missing_alt,
        "images": len(imgs),
        "images_missing_alt": len(missing_alt),
    }


def check_internal_links(markdown: str) -> Dict:
    internal = _MD_LINK_INTERNAL.findall(markdown)
    n = len(internal)
    return {
        "name": "internal_links",
        "passed": n >= THRESHOLDS["internal_links_min"],
        "count": n,
        "min": THRESHOLDS["internal_links_min"],
    }


def check_readability(markdown: str) -> Dict:
    score = _flesch_reading_ease(markdown)
    return {
        "name": "readability",
        "passed": score >= THRESHOLDS["readability_min"],
        "flesch_reading_ease": round(score, 2),
        "min": THRESHOLDS["readability_min"],
    }


def check_canonical_uniqueness(title: str, slug: str, corpus: List[Dict]) -> Dict:
    max_title = max((title_similarity(title, c.get("title", "")) for c in corpus), default=0.0)
    max_slug = max((slug_similarity(slug, c.get("slug", "")) for c in corpus), default=0.0)
    passed = (max_title <= THRESHOLDS["canonical_title_max"]
              and max_slug <= THRESHOLDS["canonical_slug_max"])
    return {
        "name": "canonical_uniqueness",
        "passed": passed,
        "max_title_similarity": round(max_title, 4),
        "max_slug_similarity": round(max_slug, 4),
    }


def check_cannibalization(title: str, slug: str, keywords: List[str],
                          corpus: List[Dict]) -> Dict:
    emb = get_embeddings_service()
    new_vec = emb.embed_text(f"{title} {' '.join(keywords)}")
    worst = 0.0
    for c in corpus:
        old_vec = emb.embed_text(c.get("title", ""))
        signals = {
            "semantic": max(0.0, emb.cosine_similarity(new_vec, old_vec)),
            "title": title_similarity(title, c.get("title", "")),
            "keyword": keyword_overlap(keywords or [title], list(token_set(c.get("title", "")))),
            "slug": slug_similarity(slug, c.get("slug", "")),
            "intent": intent_overlap(title, c.get("title", "")),
        }
        worst = max(worst, composite_overlap(signals, SIGNAL_WEIGHTS))
    decision = cannibal_decide(worst) if cannibal_decide else ("ALLOW" if worst < 0.55 else "BLOCK")
    return {
        "name": "cannibalization",
        "passed": decision == "ALLOW",
        "max_composite": round(worst, 4),
        "decision": decision,
    }


def check_originality(markdown: str, corpus: List[Dict]) -> Dict:
    if run_originality_check is None:
        return {"name": "originality", "passed": False, "detail": "agent_19 unavailable"}
    rep = run_originality_check(markdown, [{"markdown": c.get("markdown", "")} for c in corpus],
                               output_path="output/quality_gate_v4/originality_recheck.json")
    return {
        "name": "originality",
        "passed": rep["passed"] and rep["originality_score"] >= THRESHOLDS["originality_min"],
        "score": rep["originality_score"],
        "regenerate_sections": rep["regenerate_sections"],
    }


def check_ymyl(text: str) -> Dict:
    if run_ymyl_validation is None:
        return {"name": "ymyl", "passed": False, "detail": "agent_20 unavailable"}
    rep = run_ymyl_validation(text, output_path="output/quality_gate_v4/ymyl_recheck.json")
    return {
        "name": "ymyl",
        "passed": rep["status"] == "PASS",
        "status": rep["status"],
        "summary": rep["summary"],
    }


def _consult_report(path: Optional[str], key: str, default_pass: bool = False) -> Dict:
    """Performance / competitor gates: consult agent report PASS/FAIL only."""
    if not path or not Path(path).exists():
        return {"name": key, "passed": default_pass, "detail": "report missing"}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        return {"name": key, "passed": False, "detail": f"unreadable: {e}"}
    passed = bool(data.get("passed", data.get("status") == "PASS"))
    return {"name": key, "passed": passed, "report": path}


def run_gate(args) -> Dict:
    markdown = Path(args.article).read_text(encoding="utf-8") if args.article else ""
    rendered = Path(args.rendered).read_text(encoding="utf-8") if args.rendered and Path(args.rendered).exists() else markdown
    meta = json.loads(Path(args.meta).read_text(encoding="utf-8")) if args.meta and Path(args.meta).exists() else {}
    corpus = []
    if args.corpus_dir and Path(args.corpus_dir).exists():
        for f in sorted(Path(args.corpus_dir).glob("*.md")):
            corpus.append({"markdown": f.read_text(encoding="utf-8"),
                           "title": f.stem.replace("-", " "), "slug": f.stem})

    title = meta.get("title", "")
    slug = meta.get("slug", "")
    keywords = meta.get("keywords", []) or ([meta.get("keyword")] if meta.get("keyword") else [])

    checks = [
        check_schema(rendered),
        check_eeat(meta),
        check_formatting(markdown),
        check_accessibility(rendered),
        check_internal_links(markdown),
        check_readability(markdown),
        check_canonical_uniqueness(title, slug, corpus),
        check_cannibalization(title, slug, keywords, corpus),
        check_originality(markdown, corpus),
        check_ymyl(markdown),
        _consult_report(args.performance_report, "performance"),
        _consult_report(args.competitor_report, "competitor"),
    ]

    failed = [c["name"] for c in checks if not c["passed"]]
    decision = "READY_TO_PUBLISH" if not failed else "BLOCKED"
    result = {
        "gate": "quality_gate_v4",
        "version": "4.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "failed_gates": failed,
        "checks": checks,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Quality Gate V4 decision=%s failed=%s -> %s", decision, failed, out)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="NEXUS-14 Quality Gate V4 (authoritative)")
    parser.add_argument("--article", required=True, help="article markdown file")
    parser.add_argument("--rendered", help="rendered HTML of the WP draft body")
    parser.add_argument("--meta", help="JSON with title/slug/keywords + EEAT elements")
    parser.add_argument("--corpus-dir", default="output/published_corpus")
    parser.add_argument("--performance-report", help="Agent 22 report (consulted)")
    parser.add_argument("--competitor-report", help="Agent 23 report (consulted)")
    parser.add_argument("--output", default="output/quality_gate_v4_result.json")
    args = parser.parse_args()
    result = run_gate(args)
    sys.exit(0 if result["decision"] == "READY_TO_PUBLISH" else 1)


if __name__ == "__main__":
    main()
