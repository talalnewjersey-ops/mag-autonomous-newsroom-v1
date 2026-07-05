"""Couche 3 -- G-Substance gate (BLOCKING), judging the CLEANED article.

Runs at Phase 4.45, AFTER the Couche 2 soften and BEFORE every phase that can
reach WordPress (fact-check Phase 5; WordPress draft Phase 11). It judges the
article AFTER soften has neutralised the unsourced figures -- NOT the raw
fabrication rate. Rationale (proven on a real run): the writer decorates real,
substantial prose with fabricated %/$; once soften removes them, a genuinely
useful article remains. So we gate on what's LEFT, not on how much was faked.

FAIL if ANY (OR / strict gate):
  (1) distinct allow-listed sources < tier floor (PILLAR 6 / STANDARD 4 / OPPORTUNITY 3);
  (2) fewer than --min-cited-facts (default 2, Option B) STABLE-valued facts of the
      article's vertical are actually cited (their source_url present) -- guarantees
      >=N real, concrete, sourced figures on screen (never a 100%-qualitative article);
  (3) structure broken -- no FAQ section, or H2 count < tier floor;
  (4) any unsourced numeric figure SURVIVES in the cleaned article (soften-integrity)
      -- catches a fabrication soften missed.

LEVIER C (2026-07-05): criteria (2) and (4) both now go through
agents._fact_coverage.classify_claims -- "cited" means a number in the content
was matched to the EXACT engraved value of a STABLE fact, not merely that the
fact's source_url string appears somewhere in the page (closes the
proximity-false-sourced blind spot: a real link no longer certifies an
unrelated figure sitting next to it). See agents/_fact_coverage.py docstring.

On FAIL exit!=0 -> workflow `continue` -> agent_11 (Phase 11) never runs -> NO
WordPress object, no PRODUCED.json -> reconcile keeps the topic candidate. A
rejected article can never be published (sprint 9/10 invariant, enforced early).
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents._claims import _URL_IN
from agents._sources import _classify_url
from agents._fact_coverage import classify_claims, count_cited_stable_facts
from agents._source_pool import resolve_gate_vertical  # relocated (hygiene); re-exported below

TIER = {
    "PILLAR":      {"min_sources": 6, "min_h2": 5},
    "STANDARD":    {"min_sources": 4, "min_h2": 4},
    "GOLD":        {"min_sources": 4, "min_h2": 4},
    "OPPORTUNITY": {"min_sources": 3, "min_h2": 3},
}
# Heading-level agnostic: the writer often emits the FAQ as H1; the agent_11
# sanitizer demotes H1->H2 later (Phase 11), but G-Substance runs earlier (4.45),
# so accept any heading level here to avoid a false "no FAQ" rejection.
_FAQ_RE = re.compile(r"#{1,6}\s+(?:Frequently Asked Questions|FAQ)", re.IGNORECASE)
_H2_RE = re.compile(r"(?m)^##\s+\S")  # H2 only ("## x", never "### x")


def evaluate(content, article_type, vertical, min_cited_facts=2):
    cfg = TIER.get((article_type or "STANDARD").upper(), TIER["STANDARD"])
    distinct_sources = len({u for u in _URL_IN.findall(content) if _classify_url(u) == "official"})
    h2_count = len(_H2_RE.findall(content))
    has_faq = bool(_FAQ_RE.search(content))
    claims = classify_claims(content, vertical)
    cited_facts = count_cited_stable_facts(content, vertical, claims=claims)
    residual_unsourced = sum(1 for c in claims if c["fact"] is None)

    reasons = []  # OR gate: any single reason -> FAIL
    if distinct_sources < cfg["min_sources"]:
        reasons.append(f"only {distinct_sources} distinct official sources (need >= {cfg['min_sources']})")
    if cited_facts < min_cited_facts:
        reasons.append(f"only {cited_facts} STABLE facts cited (need >= {min_cited_facts})")
    if not has_faq:
        reasons.append("no FAQ section")
    if h2_count < cfg["min_h2"]:
        reasons.append(f"only {h2_count} H2 sections (need >= {cfg['min_h2']})")
    if residual_unsourced > 0:
        reasons.append(f"{residual_unsourced} unsourced figure(s) survived soften")

    return {
        "verdict": "FAIL" if reasons else "PASS",
        "reasons": reasons,
        "tier": (article_type or "STANDARD").upper(),
        "vertical": vertical,
        "distinct_sources": distinct_sources,
        "cited_stable_facts": cited_facts,
        "residual_unsourced": residual_unsourced,
        "h2_count": h2_count,
        "has_faq": has_faq,
    }


def main():
    ap = argparse.ArgumentParser(description="Couche 3 G-Substance gate (BLOCKING).")
    ap.add_argument("--input", required=True, help="softened article_draft.md")
    ap.add_argument("--article-type", default="STANDARD")
    ap.add_argument("--market", default="")
    ap.add_argument("--category", default="")
    ap.add_argument("--min-cited-facts", type=int, default=2)
    ap.add_argument("--output", default=None)
    ap.add_argument("--soften-report", default=None, help="accepted for compatibility; not used")
    args = ap.parse_args()

    content = Path(args.input).read_text(encoding="utf-8")
    vertical = resolve_gate_vertical(args.market, args.category)
    result = evaluate(content, args.article_type, vertical, args.min_cited_facts)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[COUCHE-3 G-Substance] {result['verdict']} | {result}")
    # BLOCKING: FAIL -> non-zero -> workflow `continue` -> no WordPress, topic candidate.
    sys.exit(1 if result["verdict"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
