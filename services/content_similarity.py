"""
NEXUS-14 V4 - services/content_similarity.py  (M3/M4 shared logic)

Pure, dependency-light similarity + search-intent utilities shared by:
  * Agent 17 (cannibalization)
  * Agent 19 (originality)
  * Quality Gate V4 (independent recomputation)

Everything here is deterministic and unit-testable offline. The only optional
dependency is services.embeddings_service for semantic vectors; callers pass the
embeddings in, so this module itself never makes network calls.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Sequence, Set

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "to", "for", "of", "in", "on", "and", "or", "your", "you",
    "is", "are", "how", "what", "best", "guide", "with", "vs", "2024", "2025", "2026",
}

# Search-intent signal vocabulary.
_INTENT_SIGNALS = {
    "transactional": ("buy", "open", "apply", "sign up", "get", "order", "best card",
                      "cheapest", "deal", "discount", "price"),
    "commercial": ("best", "top", "review", "compare", "comparison", "vs",
                   "alternatives", "which"),
    "navigational": ("login", "log in", "sign in", "official", "website", "portal",
                     "dashboard", "contact"),
    "informational": ("what", "how", "why", "guide", "explained", "meaning",
                      "definition", "rules", "requirements", "eligibility"),
}


def normalize(text: str) -> str:
    return " ".join(_WORD_RE.findall((text or "").lower()))


def token_set(text: str, drop_stopwords: bool = True) -> Set[str]:
    toks = set(_WORD_RE.findall((text or "").lower()))
    if drop_stopwords:
        toks -= _STOPWORDS
    return toks


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def keyword_overlap(keywords_a: Sequence[str], keywords_b: Sequence[str]) -> float:
    """Jaccard over normalized keyword token sets."""
    a = set()
    for k in keywords_a:
        a |= token_set(k)
    b = set()
    for k in keywords_b:
        b |= token_set(k)
    return jaccard(a, b)


def title_similarity(title_a: str, title_b: str) -> float:
    return SequenceMatcher(None, normalize(title_a), normalize(title_b)).ratio()


def slug_similarity(slug_a: str, slug_b: str) -> float:
    a = set((slug_a or "").replace("_", "-").split("-"))
    b = set((slug_b or "").replace("_", "-").split("-"))
    a.discard(""); b.discard("")
    return jaccard(a, b)


def classify_intent(text: str) -> str:
    """Return the dominant search intent for a title/keyword string."""
    t = " " + normalize(text) + " "
    scores: Dict[str, int] = {k: 0 for k in _INTENT_SIGNALS}
    for intent, signals in _INTENT_SIGNALS.items():
        for sig in signals:
            if (" " + sig + " ") in t or t.startswith(sig + " ") or t.endswith(" " + sig):
                scores[intent] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "informational"


def intent_overlap(text_a: str, text_b: str) -> float:
    """1.0 if same dominant intent, else 0.0 (coarse but explainable)."""
    return 1.0 if classify_intent(text_a) == classify_intent(text_b) else 0.0


def composite_overlap(signals: Dict[str, float], weights: Dict[str, float]) -> float:
    """Weighted average of named similarity signals.

    signals/weights share keys; missing weights default to 0. Result in [0,1].
    """
    total_w = sum(weights.get(k, 0.0) for k in signals)
    if total_w == 0:
        return 0.0
    acc = sum(signals[k] * weights.get(k, 0.0) for k in signals)
    return max(0.0, min(1.0, acc / total_w))
