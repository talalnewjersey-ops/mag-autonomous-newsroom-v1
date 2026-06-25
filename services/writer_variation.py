"""
NEXUS-14 V4 - services/writer_variation.py (M2 - Writer V4 variation layer)

Completes the Writer V4 contract. Agent 19 (Originality Engine) decides WHICH
sections must be regenerated and WHY; this module turns that decision into
concrete, deterministic instructions the Writer (Agent 04) sends back to the LLM
so the regenerated sections are demonstrably different from prior output and free
of the AI footprint patterns Agent 19 bans.

DESIGN PRINCIPLES
* Single source of truth: the banned-opener / banned-phrase vocabulary is imported
  from agents.agent_19_originality. This module never re-declares those lists, so
  the writer and the originality gate can never drift apart.
* Deterministic + offline-testable: every function here is pure (no LLM, no
  network). The only LLM call lives in Agent 04; this module only builds the
  prompt directives and post-processes returned text.
* Honest scope: this does NOT itself rewrite prose with an LLM. It (a) builds the
  differentiation directives, and (b) provides a deterministic guard
  (strip_banned_patterns) that removes/repairs banned openers so a regenerated
  section cannot reintroduce a known AI footprint.

CONTRACT (consumed by Agent 04)
  directives = build_variation_directives(regenerate_sections, prior_sections, seed)
    -> {section: directive_str}
  cleaned, changed = strip_banned_patterns(text)
    -> text with banned openers/phrases neutralised + list of what changed
"""

from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Optional, Sequence, Tuple

# SSOT: reuse the exact banned vocabulary the originality gate enforces.
from agents.agent_19_originality import (
    BANNED_OPENERS,
    BANNED_PHRASES,
    split_sections,
    detect_ai_patterns,
    ngram_jaccard,
)

# Deterministic pools of approved, varied alternative openings. These are NOT
# random at runtime: a stable seed (e.g. the article slug) selects one, so the
# same article always regenerates the same way (reproducible builds + tests).
APPROVED_OPENERS = (
    "Here is what actually matters:",
    "Start with the numbers:",
    "The short version:",
    "Most newcomers get this wrong:",
    "Consider a concrete case.",
    "Begin with the rule that applies to you.",
    "The practical answer depends on two things:",
    "Skip the theory for a moment:",
)

# Per-section differentiation guidance the LLM receives in addition to the base
# instruction. Keys match the section names produced by split_sections().
SECTION_DIRECTIVES = {
    "introduction": (
        "Open with a specific scenario, statistic, or decision the reader faces. "
        "Do NOT use a generic hook or a Quick-Answer template framing."
    ),
    "conclusion": (
        "Summarise as concrete next actions, not a restatement. Do NOT begin with "
        "a summary clause; lead with the single most important decision."
    ),
    "faq": (
        "Replace each flagged question with a distinct question that targets a "
        "different sub-intent. Vary answer length and structure between answers."
    ),
    "body": (
        "Re-sequence the argument and vary sentence openings. Introduce at least "
        "one comparison or worked example not present in the prior version."
    ),
}


def _seed_index(seed: str, modulo: int) -> int:
    """Deterministic index from an arbitrary seed string."""
    if modulo <= 0:
        return 0
    h = int(hashlib.md5((seed or "").encode("utf-8")).hexdigest(), 16)
    return h % modulo


def pick_opener(seed: str) -> str:
    """Deterministically choose an approved opener for a given seed."""
    return APPROVED_OPENERS[_seed_index(seed, len(APPROVED_OPENERS))]


def build_variation_directives(
    regenerate_sections: Sequence[str],
    prior_sections: Optional[Dict[str, str]] = None,
    seed: str = "",
) -> Dict[str, str]:
    """Build a per-section differentiation directive for the Writer.

    regenerate_sections: section names Agent 19 flagged (introduction/body/faq/...).
    prior_sections: the previous text per section, so the directive can tell the
        model exactly what to avoid repeating (first ~240 chars are referenced).
    seed: stable seed (article slug) for reproducible opener selection.
    """
    prior_sections = prior_sections or {}
    directives: Dict[str, str] = {}
    banned = ", ".join(sorted(set(BANNED_OPENERS) | set(BANNED_PHRASES)))
    for section in regenerate_sections:
        base = SECTION_DIRECTIVES.get(
            section,
            "Rewrite this section to be substantially different from the prior "
            "version while preserving factual accuracy.",
        )
        prior = (prior_sections.get(section) or "").strip()
        avoid = ""
        if prior:
            snippet = re.sub(r"\s+", " ", prior)[:240]
            avoid = (
                " Do NOT repeat the phrasing or structure of the previous version, "
                "which began: \"" + snippet + "\"."
            )
        directive = (
            base
            + avoid
            + " Never use any of these banned AI-footprint phrases: "
            + banned + "."
        )
        if section in ("introduction", "body"):
            directive += " A suitable fresh opening style is: \"" + pick_opener(seed + section) + "\""
        directives[section] = directive
    return directives


def _neutralise_opener(text: str, seed: str) -> Tuple[str, bool]:
    """If the text STARTS with a banned opener, replace that opening clause."""
    stripped = text.lstrip()
    low = stripped.lower()
    for opener in BANNED_OPENERS:
        if low.startswith(opener):
            # Drop the banned opening clause up to the first sentence boundary.
            rest = stripped[len(opener):].lstrip(" ,.;:-")
            replacement = pick_opener(seed)
            return replacement + " " + rest, True
    return text, False


def strip_banned_patterns(text: str, seed: str = "") -> Tuple[str, List[Dict]]:
    """Deterministically neutralise banned AI-footprint patterns in a section.

    * A banned opener at the START of the text is replaced with an approved one.
    * Banned phrases anywhere are removed (with surrounding punctuation tidied).
    Returns (cleaned_text, changes). changes is a list of {type, value}.
    """
    changes: List[Dict] = []
    cleaned, replaced = _neutralise_opener(text, seed)
    if replaced:
        changes.append({"type": "opener_replaced", "value": pick_opener(seed)})

    low = cleaned.lower()
    for phrase in BANNED_PHRASES:
        if phrase in low:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            cleaned = pattern.sub("", cleaned)
            low = cleaned.lower()
            changes.append({"type": "phrase_removed", "value": phrase})
    # Tidy doubled spaces / dangling punctuation left by removals.
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"(^|\n)\s*[,;:]\s*", r"\1", cleaned)
    return cleaned.strip(), changes


def verify_variation(
    new_text: str,
    prior_text: str,
    max_similarity: float = 0.82,
) -> Dict:
    """Confirm a regenerated section is sufficiently different + footprint-free.

    Uses the SAME n-gram Jaccard the originality gate uses, so a section that
    passes verify_variation() here is consistent with Agent 19 thresholds.
    """
    similarity = ngram_jaccard(new_text, prior_text)
    violations = detect_ai_patterns(new_text)
    return {
        "similarity": round(similarity, 4),
        "max_similarity": max_similarity,
        "sufficiently_different": similarity <= max_similarity,
        "ai_pattern_violations": violations,
        "passed": similarity <= max_similarity and not violations,
    }


def plan_regeneration(
    article_markdown: str,
    regenerate_sections: Sequence[str],
    seed: str = "",
) -> Dict:
    """Convenience entry point for Agent 04.

    Splits the current article, then returns the directives + the prior text for
    only the sections that must be regenerated. Agent 04 calls the LLM with these
    directives, then runs strip_banned_patterns()/verify_variation() on each
    returned section before reassembling the article.
    """
    sections = split_sections(article_markdown)
    prior = {s: sections.get(s, "") for s in regenerate_sections}
    directives = build_variation_directives(regenerate_sections, prior, seed)
    return {
        "regenerate_sections": list(regenerate_sections),
        "directives": directives,
        "prior_sections": prior,
    }
