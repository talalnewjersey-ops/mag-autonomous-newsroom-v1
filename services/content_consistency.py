#!/usr/bin/env python3
"""
NEXUS-14 V4 - services/content_consistency.py (M9 - internal-consistency gate)

A DETERMINISTIC, OFFLINE check for an article contradicting ITSELF. It is the
internal-coherence companion to:
  - agent_19 (originality, vs the published corpus),
  - services.content_quality (M8, newcomer quality),
  - agent_20 (YMYL, figures vs an external authoritative registry).

M9 verifies NOTHING about the outside world. It only flags self-contradiction
and citation hygiene that are checkable from the text alone:
  1. numeric/currency clashes - the same labelled metric stated with two
     different values in the same article;
  2. unsupported absolute claims - "always/never/guaranteed/100%" style
     sentences with no citation marker nearby;
  3. dangling cross-references - "see the section above/below/Section 9" with
     no matching heading;
  4. temporal incoherence - a "as of YYYY" year far in the future / past.

It returns a 0-100 score, per-check findings, and regenerate_sections using the
SAME section vocabulary as services.writer_variation, so a failing article
feeds the existing targeted-regeneration loop. No network, no LLM, no fabricated
data. External truth-checking remains agent_05 (gated, network) and agent_20.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from agents.agent_19_originality import split_sections, heading_skeleton

# --- Tunable thresholds (auditable, no external data) -------------------------
MIN_CONSISTENCY_SCORE = 75      # gate threshold (0-100)
CITATION_WINDOW = 240           # chars around an absolute claim to find a cite
CURRENT_YEAR = 2025             # reference year; editable, not a live clock
FUTURE_YEAR_SLACK = 1           # a year > CURRENT_YEAR + slack is suspicious
PAST_YEAR_FLOOR = 1990          # a year < this in an "as of" context is suspicious

# Penalty per finding-class (subtracted from 100, then clamped).
PENALTY = {
    "numeric_clash": 18,
    "unsupported_absolute": 8,
    "dangling_reference": 10,
    "temporal": 12,
}

ABSOLUTE_TERMS = (
    "always", "never", "guaranteed", "guarantee", "100%", "everyone",
    "no one", "impossible", "definitely", "all banks", "every newcomer",
)

# Citation markers that make an absolute claim acceptable (presence nearby).
CITATION_MARKERS = (
    "according to", "source", "http://", "https://", ".gov", ".gc.ca",
    "official", "as of", "[", "(see",
)

_LABELLED_MONEY_RE = re.compile(
    r"([A-Za-z][A-Za-z \-]{2,40}?)\s*(?:is|of|:|costs?|=)?\s*\$\s?(\d[\d,]*(?:\.\d+)?)",
)
_SENT_RE = re.compile(r"[.!?]+\s+")
_AS_OF_YEAR_RE = re.compile(r"as of\s+(?:[A-Za-z]+\s+)?(\d{4})", re.IGNORECASE)
_SECTION_REF_RE = re.compile(r"\bsection\s+(\d{1,2})\b", re.IGNORECASE)


def _to_number(raw: str):
    try:
        return float(raw.replace(",", ""))
    except (ValueError, AttributeError):
        return None


# Filler words stripped so a metric label matches regardless of leading words
# ("the application fee" == "later the application fee" -> "application fee").
_LABEL_STOPWORDS = frozenset((
    "the", "a", "an", "this", "that", "later", "then", "also", "is", "of",
    "for", "to", "and", "but", "here", "there", "now", "your", "my", "its",
))


def _norm_label(label: str) -> str:
    words = re.sub(r"\s+", " ", label.strip().lower()).split(" ")
    words = [w for w in words if w and w not in _LABEL_STOPWORDS]
    # Keep the last (up to) 3 significant words: the noun phrase next to the $.
    return " ".join(words[-3:])


def find_numeric_clashes(text: str) -> List[Dict]:
    """Same money label stated with two different values => contradiction."""
    by_label: Dict[str, set] = {}
    for m in _LABELLED_MONEY_RE.finditer(text or ""):
        label = _norm_label(m.group(1))
        value = _to_number(m.group(2))
        if not label or value is None or len(label) < 3:
            continue
        by_label.setdefault(label, set()).add(value)
    clashes = []
    for label, values in by_label.items():
        if len(values) > 1:
            clashes.append({"label": label, "values": sorted(values)})
    return clashes


def _has_citation_near(text: str, start: int, end: int) -> bool:
    lo = max(0, start - CITATION_WINDOW)
    hi = min(len(text), end + CITATION_WINDOW)
    window = text[lo:hi].lower()
    return any(mark in window for mark in CITATION_MARKERS)


def find_unsupported_absolutes(text: str) -> List[Dict]:
    """Absolute-claim sentences with no citation marker in their neighbourhood."""
    low = (text or "").lower()
    findings = []
    for term in ABSOLUTE_TERMS:
        for m in re.finditer(re.escape(term), low):
            if not _has_citation_near(text or "", m.start(), m.end()):
                findings.append({"term": term, "pos": m.start()})
    return findings


def find_dangling_references(text: str) -> List[Dict]:
    """'Section N' references with no matching H2 ordinal / heading present."""
    headings = heading_skeleton(text or "")
    n_headings = len(headings)
    findings = []
    for m in _SECTION_REF_RE.finditer(text or ""):
        ref_n = int(m.group(1))
        if ref_n == 0 or ref_n > n_headings:
            findings.append({"reference": m.group(0), "section_count": n_headings})
    return findings


def find_temporal_issues(text: str) -> List[Dict]:
    """'As of YYYY' years implausibly far in the future or past."""
    findings = []
    for m in _AS_OF_YEAR_RE.finditer(text or ""):
        year = int(m.group(1))
        if year > CURRENT_YEAR + FUTURE_YEAR_SLACK or year < PAST_YEAR_FLOOR:
            findings.append({"year": year, "matched": m.group(0)})
    return findings


# Map a finding-class to the section(s) that should be regenerated.
_CLASS_TO_SECTIONS = {
    "numeric_clash": ["body"],
    "unsupported_absolute": ["body", "introduction"],
    "dangling_reference": ["body"],
    "temporal": ["body"],
}


def assess_consistency(text: str) -> Dict:
    """Score internal consistency and report sections to regenerate.

    Returns score (0-100), passed (bool), findings (per-class lists),
    and regenerate_sections (ordered, unique). Pure: no IO, no mutation.
    """
    md = text or ""
    findings = {
        "numeric_clash": find_numeric_clashes(md),
        "unsupported_absolute": find_unsupported_absolutes(md),
        "dangling_reference": find_dangling_references(md),
        "temporal": find_temporal_issues(md),
    }
    penalty = 0
    for cls, items in findings.items():
        penalty += PENALTY[cls] * len(items)
    score = max(0, min(100, 100 - penalty))

    regenerate: List[str] = []
    for cls, items in findings.items():
        if not items:
            continue
        for sec in _CLASS_TO_SECTIONS.get(cls, []):
            if sec not in regenerate:
                regenerate.append(sec)

    return {
        "score": score,
        "passed": score >= MIN_CONSISTENCY_SCORE,
        "findings": findings,
        "regenerate_sections": regenerate,
        "threshold": MIN_CONSISTENCY_SCORE,
    }


def consistency_sections(text: str) -> List[str]:
    """Adapter matching the writer-loop quality_check signature (-> sections)."""
    return assess_consistency(text)["regenerate_sections"]


def combine_checks(*checks):
    """Compose several quality_check callables into one (union of sections).

    Each check maps markdown -> List[str]. A failing/raising check contributes
    nothing (never blocks). Order-preserving, de-duplicated. This lets the
    Writer V4 loop run the M8 quality gate and the M9 consistency gate together.
    """
    def _combined(markdown: str) -> List[str]:
        out: List[str] = []
        for check in checks:
            try:
                for sec in check(markdown) or []:
                    if sec not in out:
                        out.append(sec)
            except Exception:  # pragma: no cover - defensive: never block
                continue
        return out
    return _combined

# end of M9 internal-consistency gate
