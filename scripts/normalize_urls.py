"""URL normalization pass -- runs AFTER soften/polish, BEFORE agent_05 (fact-check).
NON-BLOCKING.

The writer occasionally MUTATES a supplied .gov URL: observed on a real run it wrote
consumer.ftc.gov/articles/disputing-errors-ON-your-credit-reports (an inserted "on-")
instead of the canonical .../disputing-errors-your-credit-reports -> 404. A well-formed
but WRONG .gov URL is false verifiability (P3). This deterministic pass repairs each
.gov URL:

  (a) EXACT match to a SUPPLIED url (a _vertical_facts source OR a source-pool page) -> keep.
  (b) UNAMBIGUOUS near-miss of exactly ONE ENGRAVED FACT url (_vertical_facts, which were
      verbatim-verified) -> RESTORE to that canonical url. Restoration targets are ONLY the
      engraved fact URLs -- never a guessed / merely-well-formed url.
  (c) otherwise (no match, no unambiguous near-miss) -> REMOVE the url, keep the anchor
      text: never publish an unverified .gov link that may point to the wrong page.

An ambiguous near-miss (close to >=2 fact urls) is treated as unknown -> removed, NEVER
restored to a wrong page. Only .gov links are touched; internal moneyabroadguide.com and
off-list links are left untouched (dead internal links are a separate chantier).
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents._vertical_facts import VERTICAL_FACTS
from agents._source_pool import resolve_vertical, select_official_sources

# markdown link whose URL is on a .gov host
_MDLINK = re.compile(r"\[([^\]]*)\]\((https?://[^)]*\.gov[^)\s]*)\)", re.I)
_NEAR_MIN = 0.70     # min path-token Jaccard to be a near-miss candidate
_NEAR_MARGIN = 0.15  # the best target must beat the 2nd best by this -> unambiguous


def _path_tokens(url):
    return set(t for t in re.split(r"[/\-_.]+", urlparse(url).path.lower()) if t)


def _jaccard(a, b):
    return len(a & b) / len(a | b) if (a and b) else 0.0


def _restore_target(url, fact_urls):
    """The single engraved fact url this url is an UNAMBIGUOUS near-miss of, else None."""
    host = urlparse(url).netloc.lower()
    scored = sorted(
        ((_jaccard(_path_tokens(url), _path_tokens(t)), t)
         for t in fact_urls if urlparse(t).netloc.lower() == host),
        key=lambda x: x[0], reverse=True)
    if not scored or scored[0][0] < _NEAR_MIN:
        return None
    if len(scored) > 1 and scored[1][0] >= scored[0][0] - _NEAR_MARGIN:
        return None                       # ambiguous -> do NOT guess
    return scored[0][1]


def normalize(text, fact_urls, known_good):
    known = {u.rstrip("/") for u in known_good}
    report = {"kept": 0, "restored": [], "removed": []}

    def fix(url):
        if url.rstrip("/") in known:
            report["kept"] += 1
            return url                     # (a) exact supplied url -> keep
        tgt = _restore_target(url, fact_urls)
        if tgt:
            report["restored"].append({"from": url, "to": tgt})
            return tgt                     # (b) unambiguous near-miss -> restore to fact url
        report["removed"].append(url)
        return None                        # (c) unknown -> drop the url, keep the text

    def repl(m):
        anchor, url = m.group(1), m.group(2)
        new = fix(url)
        return f"[{anchor}]({new})" if new else anchor

    return _MDLINK.sub(repl, text), report


def _canonical_urls(market, category):
    vertical = resolve_vertical(market, category) or "us_default"
    fact_urls = [f["source_url"] for f in VERTICAL_FACTS.get(vertical, []) if f.get("source_url")]
    pool = []
    for s in select_official_sources(vertical, 12):
        m = re.search(r"https?://\S+", s if isinstance(s, str) else "")
        if m:
            pool.append(m.group(0))
    return fact_urls, fact_urls + pool     # (restoration targets, keep-if-exact set)


def main():
    ap = argparse.ArgumentParser(description="URL normalization pass (non-blocking).")
    ap.add_argument("--input", required=True, help="article_draft.md (rewritten in place)")
    ap.add_argument("--market", default="")
    ap.add_argument("--category", default="")
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    fact_urls, known_good = _canonical_urls(args.market, args.category)
    text = Path(args.input).read_text(encoding="utf-8")
    fixed, report = normalize(text, fact_urls, known_good)
    Path(args.input).write_text(fixed, encoding="utf-8")
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[URL-NORMALIZE] kept={report['kept']} "
          f"restored={len(report['restored'])} removed={len(report['removed'])}")
    sys.exit(0)  # NON-BLOCKING: the blocking verification stays with agent_05


if __name__ == "__main__":
    main()
