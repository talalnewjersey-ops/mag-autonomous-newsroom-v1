#!/usr/bin/env python3
"""
NEXUS-14 V4 - scripts/validate_v4_pipeline.py

OFFLINE V4 RELEASE-CANDIDATE VALIDATION HARNESS.

Purpose: produce REAL execution evidence for the V4 decision core without
touching WordPress, OpenAI, or any network service. It runs the actual V4
agents against deterministic in-memory fixtures and prints + writes a JSON
report of each gate decision.

WHAT IT EXERCISES (real code paths, no fabrication):
  * Agent 19  (originality)        -> run_originality_check
  * Agent 17  (cannibalization)    -> score_conflict + decide (in-memory corpus,
                                      NO fetch_wordpress_articles, NO network)
  * Agent 20  (YMYL)               -> run_ymyl_validation
  * Quality Gate V4                -> run_gate (authoritative, recomputes signals)

DETERMINISTIC: forces EMBEDDINGS_PROVIDER=hashing (offline, no API keys).
WRITES NOTHING to WordPress. Emits output/validation_v4/validation_report.json.

NOTE ON THE QUALITY GATE + RUNTIME GATES:
  The authoritative gate ALWAYS consults the performance (Agent 22) and
  competitor (Agent 23) reports. Offline, those reports are absent, so the gate
  correctly marks them as failed/PENDING. This is the documented honest design:
  publication is blocked until real Lighthouse / SERP measurements are supplied.
  Therefore a fully content-clean article is expected to be BLOCKED offline with
  failed_gates EXACTLY {performance, competitor}; every CONTENT gate must pass.

EXIT CODES
  0 -> harness ran and every scenario behaved as expected
  1 -> a scenario did not behave as expected (investigate the report)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# Force the deterministic, offline embeddings backend BEFORE importing agents.
os.environ.setdefault("EMBEDDINGS_PROVIDER", "hashing")

from services.embeddings_service import get_embeddings_service
from agents.agent_19_originality import run_originality_check
from agents.agent_20_ymyl_validator import run_ymyl_validation
from agents import agent_17_cannibalization as a17
import scripts.quality_gate_v4 as qg


OUT_DIR = Path("output/validation_v4")

# Runtime gates that always fail offline (no Lighthouse / SERP data). This is
# the documented honest behavior, not a defect.
RUNTIME_GATES = {"performance", "competitor"}


def run_cannibalization_offline(topic, keywords, slug, corpus_posts):
    """Run Agent 17 decision logic against an IN-MEMORY corpus.

    Deliberately bypasses fetch_wordpress_articles() so the harness makes NO
    network call and NEVER reads/writes WordPress. Uses the real
    score_conflict() + decide() so the decision is genuine V4 logic.
    """
    a17._load_thresholds()
    emb = get_embeddings_service()
    conflicts = [a17.score_conflict(topic, keywords, slug, p, emb) for p in corpus_posts]
    conflicts.sort(key=lambda c: c["composite"], reverse=True)
    top = conflicts[0] if conflicts else None
    max_score = top["composite"] if top else 0.0
    decision = a17.decide(max_score)
    return {
        "decision": decision,
        "blocking": decision in a17.BLOCKING_DECISIONS,
        "max_composite": round(max_score, 4),
        "corpus_size": len(corpus_posts),
        "bands": {"allow": a17.BAND_ALLOW, "human_review": a17.BAND_HUMAN, "merge": a17.BAND_MERGE},
    }


def run_quality_gate_offline(markdown, rendered_html, meta, corpus_md):
    """Drive the authoritative Quality Gate via a temp workspace (offline)."""
    tmp = Path(tempfile.mkdtemp(prefix="qg_v4_"))
    art = tmp / "article.md"; art.write_text(markdown, encoding="utf-8")
    ren = tmp / "rendered.html"; ren.write_text(rendered_html, encoding="utf-8")
    met = tmp / "meta.json"; met.write_text(json.dumps(meta), encoding="utf-8")
    corpus_dir = tmp / "corpus"; corpus_dir.mkdir()
    for i, md in enumerate(corpus_md):
        (corpus_dir / ("post_%02d.md" % i)).write_text(md, encoding="utf-8")
    out = tmp / "gate_result.json"

    class _Args:
        pass
    args = _Args()
    args.article = str(art)
    args.rendered = str(ren)
    args.meta = str(met)
    args.corpus_dir = str(corpus_dir)
    args.performance_report = None
    args.competitor_report = None
    args.output = str(out)
    return qg.run_gate(args)


# --------------------------------------------------------------------------- #
# Deterministic fixtures.                                                      #
# --------------------------------------------------------------------------- #
# CLEAN article: no banned patterns, valid heading hierarchy, >=5 internal
# moneyabroadguide.com links, an official source, a disclosure.
CLEAN_ARTICLE = (
    "Start with the numbers: sending $1,000 abroad can cost between $4 and $45 "
    "depending on the provider you choose this year.\n\n"
    "## How Transfer Fees Work\n"
    "Providers blend an explicit fee with an exchange-rate margin. "
    "See our [fee guide](https://moneyabroadguide.com/fees) for the math, the "
    "[comparison](https://moneyabroadguide.com/compare) table, and the "
    "[corridors](https://moneyabroadguide.com/corridors) overview.\n\n"
    "## Choosing A Service\n"
    "Match the corridor to the provider. The [service list]"
    "(https://moneyabroadguide.com/services) ranks them and our "
    "[reviews](https://moneyabroadguide.com/reviews) go deeper. "
    "Affiliate disclosure: we may earn a commission. "
    "Official guidance: https://www.irs.gov/businesses plus more "
    "[tips](https://moneyabroadguide.com/tips) here.\n\n"
    "## Frequently Asked Questions\n"
    "### How long does a transfer take?\n"
    "Most arrive within one business day.\n\n"
    "## Conclusion\n"
    "Pick the cheapest reliable corridor and confirm the rate before you send.\n"
)

CLEAN_META = {
    "title": "How To Send Money Abroad Cheaply In 2026",
    "slug": "send-money-abroad-cheaply-2026",
    "keywords": ["send money abroad", "transfer fees", "exchange rate"],
    "author": "Talal Eddaouahiri",
    "review_date": "2026-06-25",
    "update_date": "2026-06-25",
    "official_references": ["https://www.irs.gov/businesses"],
    "disclosure": True,
    "related_articles": ["https://moneyabroadguide.com/compare"],
}

CLEAN_RENDERED = (
    "<p>Clean rendered body with a single Yoast schema source.</p>"
    "<img src=\"chart.png\" alt=\"fee comparison chart\">"
    "<!-- wp:yoast/faq-block -->"
)

DUP_CORPUS_POSTS = [
    {"id": 101, "slug": "send-money-abroad-cheaply-2026",
     "title": {"rendered": "How To Send Money Abroad Cheaply In 2026"},
     "excerpt": {"rendered": "Compare providers, fees and exchange rates."},
     "link": "https://moneyabroadguide.com/?p=101"},
]

BAD_ARTICLE = (
    "In today\u0027s world, sending money is hard.\n\n"
    "## \U0001F680 Getting Started\n"
    "Body text without enough internal links.\n\n"
    "## Conclusion\nDone.\n"
)
BAD_META = {"title": "Send Money", "slug": "send-money", "keywords": ["x"], "author": "x"}
BAD_RENDERED = (
    "<p>Body with forbidden schema "
    "<script type=\"application/ld+json\">{}</script> and "
    "<img src=\"x.png\"></p>"
)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scenarios = []
    ok = True

    # --- Scenario A: CLEAN article, empty corpus.
    a19_clean = run_originality_check(CLEAN_ARTICLE, [], str(OUT_DIR / "orig_clean.json"))
    a17_clean = run_cannibalization_offline(
        CLEAN_META["title"], CLEAN_META["keywords"], CLEAN_META["slug"], [])
    a20_clean = run_ymyl_validation(CLEAN_ARTICLE, output_path=str(OUT_DIR / "ymyl_clean.json"))
    qg_clean = run_quality_gate_offline(CLEAN_ARTICLE, CLEAN_RENDERED, CLEAN_META, [])
    clean_content_failures = [g for g in qg_clean["failed_gates"] if g not in RUNTIME_GATES]
    scenarios.append({
        "scenario": "A_clean_empty_corpus",
        "agent_19": {"score": a19_clean["originality_score"], "passed": a19_clean["passed"],
                      "regenerate_sections": a19_clean["regenerate_sections"],
                      "violations": a19_clean["violations"]},
        "agent_17": {"decision": a17_clean["decision"], "blocking": a17_clean["blocking"],
                      "max_composite": a17_clean["max_composite"]},
        "agent_20": {"status": a20_clean["status"], "summary": a20_clean["summary"]},
        "quality_gate": {"decision": qg_clean["decision"], "failed_gates": qg_clean["failed_gates"],
                          "content_gate_failures": clean_content_failures},
    })

    # --- Scenario B: CLEAN topic vs near-duplicate corpus.
    a17_dup = run_cannibalization_offline(
        CLEAN_META["title"], CLEAN_META["keywords"], CLEAN_META["slug"], DUP_CORPUS_POSTS)
    scenarios.append({
        "scenario": "B_cannibalization_near_duplicate",
        "agent_17": {"decision": a17_dup["decision"], "blocking": a17_dup["blocking"],
                      "max_composite": a17_dup["max_composite"], "bands": a17_dup["bands"]},
    })

    # --- Scenario C: BAD article -> Quality Gate must BLOCK on content gates.
    qg_bad = run_quality_gate_offline(BAD_ARTICLE, BAD_RENDERED, BAD_META, [])
    a19_bad = run_originality_check(BAD_ARTICLE, [], str(OUT_DIR / "orig_bad.json"))
    bad_content_failures = [g for g in qg_bad["failed_gates"] if g not in RUNTIME_GATES]
    scenarios.append({
        "scenario": "C_bad_article_must_block",
        "agent_19": {"score": a19_bad["originality_score"], "passed": a19_bad["passed"],
                      "violations": a19_bad["violations"]},
        "quality_gate": {"decision": qg_bad["decision"], "failed_gates": qg_bad["failed_gates"],
                          "content_gate_failures": bad_content_failures},
    })

    # --- Scenario D: contradicted YMYL value -> Agent 20 must FAIL.
    a20_bad = run_ymyl_validation(
        "The TFSA contribution limit is $99,999 for 2025.",
        output_path=str(OUT_DIR / "ymyl_bad.json"))
    scenarios.append({
        "scenario": "D_ymyl_contradiction",
        "agent_20": {"status": a20_bad["status"], "summary": a20_bad["summary"]},
    })

    # --- Expectations (assert DIRECTION / design intent, never invent numbers) ---
    expectations = []
    def expect(name, condition):
        nonlocal ok
        expectations.append({"check": name, "result": "EXPECTED" if condition else "UNEXPECTED"})
        if not condition:
            ok = False

    # Clean article: every CONTENT gate passes; only the runtime gates remain,
    # which correctly block offline (honest PENDING design).
    expect("A: clean article passes ALL content gates (no content failures)",
           clean_content_failures == [])
    expect("A: clean article blocked ONLY by runtime gates offline",
           set(qg_clean["failed_gates"]) <= RUNTIME_GATES)
    expect("A: clean originality passed", a19_clean["passed"] is True)
    expect("A: clean cannibalization ALLOW on empty corpus",
           a17_clean["decision"] == "ALLOW")
    expect("A: clean YMYL PASS", a20_clean["status"] == "PASS")
    expect("B: near-duplicate cannibalization is NOT ALLOW and blocking",
           a17_dup["decision"] != "ALLOW" and a17_dup["blocking"] is True)
    expect("C: bad article quality gate BLOCKED", qg_bad["decision"] == "BLOCKED")
    expect("C: bad article fails CONTENT gates (schema/eeat/formatting/...)",
           len(bad_content_failures) >= 1)
    expect("C: bad article originality NOT passed", a19_bad["passed"] is False)
    expect("D: contradicted YMYL value FAIL", a20_bad["status"] == "FAIL")

    report = {
        "harness": "validate_v4_pipeline",
        "version": "1.1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "embeddings_provider": os.environ.get("EMBEDDINGS_PROVIDER"),
        "wordpress_contacted": False,
        "openai_contacted": False,
        "runtime_gates_pending_offline": sorted(RUNTIME_GATES),
        "scenarios": scenarios,
        "expectations": expectations,
        "all_expected": ok,
    }
    out = OUT_DIR / "validation_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 64)
    print("NEXUS-14 V4 OFFLINE VALIDATION HARNESS")
    print("=" * 64)
    print("embeddings_provider:", os.environ.get("EMBEDDINGS_PROVIDER"))
    print("wordpress_contacted: False    openai_contacted: False")
    print("runtime gates PENDING offline (by design):", sorted(RUNTIME_GATES))
    print("-" * 64)
    for s in scenarios:
        print("SCENARIO", s["scenario"])
        for k in ("agent_17", "agent_19", "agent_20", "quality_gate"):
            if k in s:
                print("   ", k, "->", json.dumps(s[k], ensure_ascii=False))
    print("-" * 64)
    for e in expectations:
        print(("[OK] " if e["result"] == "EXPECTED" else "[XX] ") + e["check"])
    print("-" * 64)
    print("ALL_EXPECTED:", ok)
    print("report:", out)
    print("=" * 64)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
