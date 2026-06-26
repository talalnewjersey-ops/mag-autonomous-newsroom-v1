#!/usr/bin/env python3
"""
NEXUS-14 V4 - services/content_quality.py (M8 - newcomer content-quality gate)

A DETERMINISTIC, OFFLINE quality scorer for finished article markdown. It is the
quality analogue of the originality gate (agent_19): it inspects an article and
returns a 0-100 score, per-signal detail, and the list of section names that
should be regenerated. Those section names are the SAME vocabulary used by
services.writer_variation.plan_regeneration / build_variation_directives, so a
failing article feeds straight into the existing targeted-regeneration loop.

HONEST SCOPE
No LLM, no network, no fabricated metrics. Every signal is computed from the
article text itself using transparent, auditable heuristics. The scorer never
rewrites content; it only MEASURES and POINTS to weak sections. Real
regeneration still requires the Anthropic API (gated in agent_04_writer_v4).

The newcomer lens (US/CA immigrants) is encoded as small, editable keyword and
structure checks - not as live search/affiliate data, which we do not have.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from agents.agent_19_originality import split_sections, heading_skeleton

# --- Tunable editorial thresholds (auditable, no external data) ---------------
MIN_QUALITY_SCORE = 70          # gate threshold (0-100)
MIN_WORDS = 700                 # a useful newcomer guide is rarely shorter
MIN_H2 = 3                      # at least a few structured sections
MIN_FAQ_QUESTIONS = 2           # newcomers search question-shaped queries
LONG_SENTENCE_WORDS = 34        # readability ceiling per sentence
MAX_LONG_SENTENCE_RATIO = 0.30  # at most 30% of sentences may be very long

# Signal weights (sum = 1.0). Editorial judgement; documented, not data-derived.
WEIGHTS = {
    "length": 0.18,
    "structure": 0.20,
    "newcomer_actionability": 0.24,
    "eeat_surface": 0.18,
    "faq_coverage": 0.10,
    "readability": 0.10,
}

# Newcomer-actionability vocabulary: concrete, decision-useful language an
# immigrant guide should contain. Editable; intentionally small and transparent.
NEWCOMER_TERMS = (
    "ssn", "social security", "sin number", "credit score", "credit history",
    "bank account", "routing number", "ein", "itin", "tax", "irs", "cra",
    "lease", "deposit", "documents", "eligibility", "apply", "requirements",
    "fees", "cost", "step", "checklist", "deadline", "newcomer", "immigrant",
)

# Surface markers of experience / expertise / trust (EEAT) - presence checks,
# never a claim that the content is authoritative.
EEAT_MARKERS = (
    "according to", "official", ".gov", ".gc.ca", "source", "as of",
    "updated", "disclaimer", "consult", "verify", "documentation",
)

_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_SENT_RE = re.compile(r"[.!?]+\s+")
_FAQ_Q_RE = re.compile(r"^\s*(#{2,4}\s+.*\?|\*\*.*\?\*\*|.*\?)\s*$", re.MULTILINE)


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text or ""))


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def score_length(markdown: str) -> Tuple[float, Dict]:
    """Fraction of MIN_WORDS achieved (capped at 1.0)."""
    words = _word_count(markdown)
    ratio = _clamp(words / float(MIN_WORDS))
    return ratio, {"words": words, "min_words": MIN_WORDS}


def score_structure(markdown: str) -> Tuple[float, Dict]:
    """Reward H2 coverage up to MIN_H2; small bonus for a conclusion."""
    headings = heading_skeleton(markdown)
    h2 = len(headings)
    base = _clamp(h2 / float(MIN_H2))
    has_conclusion = any("conclus" in h.lower() for h in headings)
    score = _clamp(0.85 * base + (0.15 if has_conclusion else 0.0))
    return score, {"h2_count": h2, "min_h2": MIN_H2, "has_conclusion": has_conclusion}


def score_newcomer_actionability(markdown: str) -> Tuple[float, Dict]:
    """How many distinct newcomer-actionability terms appear (saturating)."""
    low = (markdown or "").lower()
    hits = sorted({t for t in NEWCOMER_TERMS if t in low})
    target = max(1, len(NEWCOMER_TERMS) // 3)  # saturate at ~1/3 of vocabulary
    score = _clamp(len(hits) / float(target))
    return score, {"matched_terms": hits, "target_distinct": target}


def score_eeat_surface(markdown: str) -> Tuple[float, Dict]:
    """Presence of trust/expertise surface markers (saturating)."""
    low = (markdown or "").lower()
    hits = sorted({m for m in EEAT_MARKERS if m in low})
    target = max(1, len(EEAT_MARKERS) // 3)
    score = _clamp(len(hits) / float(target))
    return score, {"matched_markers": hits, "target_distinct": target}


def score_faq_coverage(markdown: str) -> Tuple[float, Dict]:
    """Reward an FAQ section with at least MIN_FAQ_QUESTIONS question lines."""
    sections = split_sections(markdown)
    faq = sections.get("faq", "")
    questions = [q for q in _FAQ_Q_RE.findall(faq) if "?" in q]
    n = len(questions)
    score = _clamp(n / float(MIN_FAQ_QUESTIONS))
    return score, {"faq_questions": n, "min_questions": MIN_FAQ_QUESTIONS}


def score_readability(markdown: str) -> Tuple[float, Dict]:
    """Penalise a high ratio of very long sentences."""
    sentences = [s for s in _SENT_RE.split(markdown or "") if s.strip()]
    if not sentences:
        return 0.0, {"sentences": 0, "long_ratio": 1.0}
    long_n = sum(1 for s in sentences if _word_count(s) > LONG_SENTENCE_WORDS)
    long_ratio = long_n / float(len(sentences))
    score = _clamp(1.0 - (long_ratio / MAX_LONG_SENTENCE_RATIO))
    return score, {
        "sentences": len(sentences),
        "long_sentences": long_n,
        "long_ratio": round(long_ratio, 4),
    }


# Map a weak signal to the section(s) that should be regenerated. Section names
# match services.writer_variation / agent_19 split_sections vocabulary.
_SIGNAL_TO_SECTIONS = {
    "length": ["body"],
    "structure": ["body"],
    "newcomer_actionability": ["body", "introduction"],
    "eeat_surface": ["body"],
    "faq_coverage": ["faq"],
    "readability": ["body"],
}

# A signal is "weak" (contributes to regeneration) below this per-signal floor.
SIGNAL_PASS_FLOOR = 0.60


def assess_quality(markdown: str) -> Dict:
    """Score an article and report weak signals + sections to regenerate.

    Returns a dict with: score (0-100 int), passed (bool), signals (per-signal
    score+detail), weak_signals (list), and regenerate_sections (ordered, unique).
    Pure function: no IO, no network, no mutation of the input.
    """
    md = markdown or ""
    scorers = {
        "length": score_length,
        "structure": score_structure,
        "newcomer_actionability": score_newcomer_actionability,
        "eeat_surface": score_eeat_surface,
        "faq_coverage": score_faq_coverage,
        "readability": score_readability,
    }
    signals: Dict[str, Dict] = {}
    weighted = 0.0
    weak_signals: List[str] = []
    for name, fn in scorers.items():
        value, detail = fn(md)
        signals[name] = {"score": round(value, 4), "detail": detail}
        weighted += WEIGHTS[name] * value
        if value < SIGNAL_PASS_FLOOR:
            weak_signals.append(name)
    score_100 = int(round(_clamp(weighted) * 100))

    regenerate: List[str] = []
    for sig in weak_signals:
        for sec in _SIGNAL_TO_SECTIONS.get(sig, []):
            if sec not in regenerate:
                regenerate.append(sec)

    return {
        "score": score_100,
        "passed": score_100 >= MIN_QUALITY_SCORE,
        "signals": signals,
        "weak_signals": weak_signals,
        "regenerate_sections": regenerate,
        "threshold": MIN_QUALITY_SCORE,
    }


def needs_quality_pass(markdown: str) -> bool:
    """Convenience predicate: True when the article should be regenerated."""
    return not assess_quality(markdown)["passed"]

# end of M8 content-quality gate
