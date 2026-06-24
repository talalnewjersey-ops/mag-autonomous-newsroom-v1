#!/usr/bin/env python3
"""
Gate 20 — Originality & Anti-Thin-Content Validation
NEXUS-14 Quality Pipeline

PURPOSE
-------
Deterministically estimate whether an article is *original* and *substantive*
enough to publish. This gate complements Agent 17 (cannibalization) and
Gate 19 (country/category). It does NOT use any AI model: every score here is
computed from the text itself so results are reproducible and auditable.

ROLLOUT (two stages, per approved proposal PR #8):
  * Stage 1 (DEFAULT): mode="warn" — never blocks. Emits a structured report
    so we can collect false-positive / false-negative data over many real runs.
  * Stage 2: mode="block" — only after thresholds are validated against
    collected data. Enabling block mode is an explicit config change.

The gate reports a decision of PASS, WARN, or FAIL plus per-check detail.
In warn mode a FAIL is downgraded to WARN (status_effective) but the raw
deterministic verdict is preserved in 'verdict_raw' for analysis.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Thresholds (tunable; Stage 1 collects data to validate these before blocking)
# ---------------------------------------------------------------------------
THRESHOLDS = {
    # Minimum substantive (HTML-stripped, boilerplate-removed) word count.
    # Below this an article is considered thin regardless of other signals.
    "min_effective_words": 900,
    # Lexical diversity = unique_words / total_words (type-token ratio).
    # Very low diversity => repetitive / padded / spun text.
    "min_lexical_diversity": 0.34,
    # Internal repetition: fraction of duplicated 8-word shingles within the
    # article itself. High => copy/paste padding.
    "max_internal_repetition": 0.18,
    # Paragraph self-similarity: max Jaccard overlap between any two paragraphs.
    # High => near-duplicate paragraphs (filler).
    "max_paragraph_similarity": 0.72,
    # Corpus duplication: max fraction of 8-word shingles shared with ANY
    # single existing article in the provided corpus. High => near-duplicate.
    "max_corpus_duplication": 0.22,
    # Minimum count of "substantive elements" (data points, examples, lists,
    # tables, numbers, citations) — proxy for real informational value / EEAT.
    "min_substantive_elements": 8,
    # Shingle size (in words) used for repetition / duplication checks.
    "shingle_size": 8,
}


# ---------------------------------------------------------------------------
# Text utilities (deterministic, no external deps)
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[A-Za-z0-9']+")
# Boilerplate phrases stripped before counting "effective" words.
_BOILERPLATE = [
    "share this article", "subscribe to our newsletter", "advertisement",
    "read more", "related articles", "leave a comment", "table of contents",
]


def strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    return _WS_RE.sub(" ", text).strip()


def words(text: str) -> List[str]:
    """Lowercase word tokens."""
    return [w.lower() for w in _WORD_RE.findall(text or "")]


def effective_word_count(text: str) -> int:
    """Word count after stripping HTML and known boilerplate phrases."""
    clean = strip_html(text).lower()
    for bp in _BOILERPLATE:
        clean = clean.replace(bp, " ")
    return len(words(clean))


def shingles(tokens: List[str], n: int) -> List[Tuple[str, ...]]:
    """Return list of n-word shingles (overlapping)."""
    if len(tokens) < n:
        return []
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def lexical_diversity(tokens: List[str]) -> float:
    """Type-token ratio. Returns 1.0 for empty (neutral)."""
    if not tokens:
        return 1.0
    return len(set(tokens)) / len(tokens)


def internal_repetition(tokens: List[str], n: int) -> float:
    """Fraction of shingles that are duplicated within the same document."""
    sh = shingles(tokens, n)
    if not sh:
        return 0.0
    counts = Counter(sh)
    duplicated = sum(c for c in counts.values() if c > 1) - len(
        [c for c in counts.values() if c > 1]
    )
    return duplicated / len(sh)


def _paragraphs(text: str) -> List[str]:
    clean = strip_html(text)
    parts = re.split(r"\n\s*\n|</p>|<br\s*/?>", text)
    paras = [strip_html(p) for p in parts]
    paras = [p for p in paras if len(words(p)) >= 20]
    return paras or ([clean] if clean else [])


def paragraph_self_similarity(text: str) -> float:
    """Max Jaccard word-set overlap between any two paragraphs."""
    paras = _paragraphs(text)
    if len(paras) < 2:
        return 0.0
    sets = [set(words(p)) for p in paras]
    worst = 0.0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            a, b = sets[i], sets[j]
            if not a or not b:
                continue
            jac = len(a & b) / len(a | b)
            if jac > worst:
                worst = jac
    return worst


def corpus_duplication(tokens: List[str], corpus: List[str], n: int) -> float:
    """Max fraction of this article's shingles shared with any single
    corpus document."""
    art = set(shingles(tokens, n))
    if not art:
        return 0.0
    worst = 0.0
    for doc in corpus or []:
        doc_sh = set(shingles(words(strip_html(doc)), n))
        if not doc_sh:
            continue
        shared = len(art & doc_sh) / len(art)
        if shared > worst:
            worst = shared
    return worst


def count_substantive_elements(text: str, meta: Optional[Dict]) -> int:
    """Heuristic count of informational/EEAT signals."""
    count = 0
    # Numbers / data points (years, amounts, percentages).
    count += len(re.findall(r"\b\d[\d,\.]*\s*(?:%|percent|usd|cad|\$)?", text or ""))
    # Lists and tables.
    count += len(re.findall(r"<li\b", text or ""))
    count += 3 * len(re.findall(r"<table\b", text or ""))
    # External citations / links.
    count += len(re.findall(r"<a\s+[^>]*href=", text or ""))
    # Headings (structure => depth).
    count += len(re.findall(r"<h[2-4]\b", text or ""))
    if meta:
        count += len(meta.get("sources", []) or [])
        count += len(meta.get("examples", []) or [])
    return count


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------
def evaluate(
    content: str,
    meta: Optional[Dict] = None,
    corpus: Optional[List[str]] = None,
    thresholds: Optional[Dict] = None,
    mode: str = "warn",
) -> Dict:
    """Run all deterministic checks and return a structured report.

    mode: "warn" (default, never blocks) or "block".
    """
    th = dict(THRESHOLDS)
    if thresholds:
        th.update(thresholds)

    clean = strip_html(content)
    toks = words(clean)
    n = th["shingle_size"]

    eff_words = effective_word_count(content)
    lex = lexical_diversity(toks)
    rep = internal_repetition(toks, n)
    para_sim = paragraph_self_similarity(content)
    corp_dup = corpus_duplication(toks, corpus or [], n)
    subst = count_substantive_elements(content, meta)

    checks = {
        "effective_words": {
            "value": eff_words, "threshold": th["min_effective_words"],
            "pass": eff_words >= th["min_effective_words"], "direction": "min",
        },
        "lexical_diversity": {
            "value": round(lex, 4), "threshold": th["min_lexical_diversity"],
            "pass": lex >= th["min_lexical_diversity"], "direction": "min",
        },
        "internal_repetition": {
            "value": round(rep, 4), "threshold": th["max_internal_repetition"],
            "pass": rep <= th["max_internal_repetition"], "direction": "max",
        },
        "paragraph_similarity": {
            "value": round(para_sim, 4), "threshold": th["max_paragraph_similarity"],
            "pass": para_sim <= th["max_paragraph_similarity"], "direction": "max",
        },
        "corpus_duplication": {
            "value": round(corp_dup, 4), "threshold": th["max_corpus_duplication"],
            "pass": corp_dup <= th["max_corpus_duplication"], "direction": "max",
        },
        "substantive_elements": {
            "value": subst, "threshold": th["min_substantive_elements"],
            "pass": subst >= th["min_substantive_elements"], "direction": "min",
        },
    }

    failed = [k for k, v in checks.items() if not v["pass"]]
    # Deterministic raw verdict is authoritative for analysis.
    verdict_raw = "PASS" if not failed else "FAIL"

    # In warn mode a FAIL is reported but downgraded so it never blocks.
    if mode == "block":
        status_effective = verdict_raw
        blocks_publication = (verdict_raw == "FAIL")
    else:
        status_effective = "PASS" if verdict_raw == "PASS" else "WARN"
        blocks_publication = False

    return {
        "gate": "gate_20_originality",
        "mode": mode,
        "verdict_raw": verdict_raw,
        "status_effective": status_effective,
        "blocks_publication": blocks_publication,
        "failed_checks": failed,
        "checks": checks,
        "thresholds": th,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _read(path: Optional[str]) -> str:
    if not path:
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Gate 20 originality & thin-content check")
    p.add_argument("--content", help="Path to article HTML/text file")
    p.add_argument("--content-text", help="Inline article text (overrides --content)")
    p.add_argument("--meta", help="Path to JSON metadata (sources, examples)")
    p.add_argument("--corpus", help="Path to JSON list of existing article texts")
    p.add_argument("--mode", choices=["warn", "block"], default="warn",
                   help="warn (default, never blocks) or block")
    p.add_argument("--output", help="Path to write JSON report (default stdout)")
    args = p.parse_args(argv)

    content = args.content_text if args.content_text else _read(args.content)
    meta = json.loads(_read(args.meta)) if args.meta else None
    corpus = json.loads(_read(args.corpus)) if args.corpus else None

    report = evaluate(content, meta=meta, corpus=corpus, mode=args.mode)
    out = json.dumps(report, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        print(out)

    # Exit code: 0 unless block-mode publication block.
    return 1 if report["blocks_publication"] else 0


if __name__ == "__main__":
    sys.exit(main())
