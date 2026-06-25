#!/usr/bin/env python3
"""
NEXUS-14 V4 - Agent 19: Originality Engine  (M3 — Originality)
MoneyAbroadGuide.com | Ensures every article is structurally and semantically
distinct from previously published content and free of repeated AI patterns.

WHAT IT CHECKS
  1. Section-level similarity vs the published corpus, separately for:
       - introduction
       - conclusion
       - FAQ block
       - body paragraphs
     using BOTH n-gram (shingle Jaccard) and embedding cosine similarity.
  2. Heading-structure repetition (the same H2 skeleton reused article to article).
  3. Repeated AI patterns: banned openers/phrases, emoji headings, templated
     "Quick Answer" framing, low sentence-structure variety.

OUTPUT  output/agent_19/originality_report.json
  {
    "originality_score": 0-100,
    "passed": bool,
    "regenerate_sections": ["introduction", "faq", ...],
    "violations": [...],
    "section_similarity": {...}
  }

REGENERATION CONTRACT
  Agent 19 does NOT call the LLM itself. It returns the list of sections that
  must be regenerated. The Writer (Agent 04) consumes regenerate_sections and
  re-emits only those sections with an explicit "differentiate from prior"
  instruction. Publishing is blocked (passed=False) until originality passes.

EXIT CODES
  0 -> passed ; 2 -> needs regeneration (sections listed) ; 1 -> hard fail.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from services.embeddings_service import get_embeddings_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("agent_19")

# ---- Thresholds (overridable via config/originality.yaml) -------------------
SECTION_SIM_MAX = {          # max allowed similarity to ANY published section
    "introduction": 0.82,
    "conclusion": 0.82,
    "faq": 0.85,
    "body": 0.88,
}
HEADING_STRUCT_MAX = 0.80    # max Jaccard of H2 skeletons
NGRAM_N = 5                  # shingle size for n-gram Jaccard
MIN_ORIGINALITY_SCORE = 80   # gate threshold

BANNED_OPENERS = (
    "in today's world", "in today's fast-paced", "in the world of",
    "navigating the complexities", "when it comes to", "it's important to note",
    "in this article", "this comprehensive guide", "look no further",
)
BANNED_PHRASES = (
    "in conclusion", "at the end of the day", "needless to say",
    "it goes without saying", "in summary,", "as we all know",
)
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
)
_WORD_RE = re.compile(r"[a-z0-9']+")
_HEADING_RE = re.compile(r'^\s*##\s+(.*)$', re.MULTILINE)
_H3_RE = re.compile(r'^\s*###\s+(.*?)\s*$', re.MULTILINE)


def _words(text: str) -> List[str]:
    return _WORD_RE.findall((text or "").lower())


def shingles(text: str, n: int = NGRAM_N) -> set:
    w = _words(text)
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def ngram_jaccard(a: str, b: str, n: int = NGRAM_N) -> float:
    sa, sb = shingles(a, n), shingles(b, n)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


# ---- Section extraction -----------------------------------------------------
def split_sections(markdown: str) -> Dict[str, str]:
    """Extract introduction, conclusion, faq, and body from article markdown."""
    intro = ""
    m_first_h2 = _HEADING_RE.search(markdown)
    intro = markdown[: m_first_h2.start()].strip() if m_first_h2 else markdown[:1500]

    faq = ""
    m_faq = re.search(
        r'##\s+(?:FAQ|Frequently Asked Questions)(.*?)(?=\n##\s+[A-Z]|$)',
        markdown, re.DOTALL | re.IGNORECASE,
    )
    if m_faq:
        faq = m_faq.group(1).strip()

    conclusion = ""
    m_concl = re.search(
        r'##\s+(?:Conclusion|Final Thoughts|Key Takeaways)(.*?)(?=\n##\s+[A-Z]|$)',
        markdown, re.DOTALL | re.IGNORECASE,
    )
    if m_concl:
        conclusion = m_concl.group(1).strip()

    body = markdown
    for seg in (faq, conclusion):
        if seg:
            body = body.replace(seg, "")
    return {"introduction": intro, "conclusion": conclusion, "faq": faq, "body": body}


def heading_skeleton(markdown: str) -> List[str]:
    return [h.strip().lower() for h in _HEADING_RE.findall(markdown)]


def heading_jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# ---- AI-pattern detection ---------------------------------------------------
def detect_ai_patterns(markdown: str) -> List[Dict]:
    violations: List[Dict] = []
    low = markdown.lower()
    for opener in BANNED_OPENERS:
        if opener in low:
            violations.append({"type": "banned_opener", "value": opener})
    for phrase in BANNED_PHRASES:
        if phrase in low:
            violations.append({"type": "banned_phrase", "value": phrase})
    # Emoji in headings.
    for h in _HEADING_RE.findall(markdown) + _H3_RE.findall(markdown):
        if EMOJI_RE.search(h):
            violations.append({"type": "emoji_heading", "value": h.strip()})
    # Sentence-structure variety: ratio of unique sentence-opening trigrams.
    sentences = re.split(r'(?<=[.!?])\s+', markdown)
    openers = [" ".join(_words(s)[:3]) for s in sentences if s.strip()]
    if openers:
        variety = len(set(openers)) / len(openers)
        if variety < 0.6:
            violations.append({"type": "low_sentence_variety",
                               "value": round(variety, 3)})
    return violations


# ---- Corpus comparison ------------------------------------------------------
def _max_section_similarity(section_text: str, corpus_sections: List[str], emb) -> float:
    if not section_text or not corpus_sections:
        return 0.0
    new_vec = emb.embed_text(section_text)
    best = 0.0
    for other in corpus_sections:
        if not other:
            continue
        sem = max(0.0, emb.cosine_similarity(new_vec, emb.embed_text(other)))
        ngram = ngram_jaccard(section_text, other)
        best = max(best, max(sem, ngram))
    return best


def run_originality_check(
    article_markdown: str,
    corpus: List[Dict],
    output_path: str = "output/agent_19/originality_report.json",
) -> Dict:
    """corpus: list of {"markdown": str} for previously published articles."""
    emb = get_embeddings_service()
    sections = split_sections(article_markdown)
    corpus_sections_by_kind: Dict[str, List[str]] = {k: [] for k in sections}
    corpus_headings: List[List[str]] = []
    for doc in corpus:
        md = doc.get("markdown", "")
        cs = split_sections(md)
        for k in corpus_sections_by_kind:
            corpus_sections_by_kind[k].append(cs.get(k, ""))
        corpus_headings.append(heading_skeleton(md))

    section_similarity: Dict[str, float] = {}
    regenerate: List[str] = []
    for kind, text in sections.items():
        sim = _max_section_similarity(text, corpus_sections_by_kind[kind], emb)
        section_similarity[kind] = round(sim, 4)
        if sim > SECTION_SIM_MAX.get(kind, 0.85):
            regenerate.append(kind)

    new_headings = heading_skeleton(article_markdown)
    heading_sim = max(
        (heading_jaccard(new_headings, h) for h in corpus_headings), default=0.0
    )
    if heading_sim > HEADING_STRUCT_MAX and "body" not in regenerate:
        regenerate.append("body")

    violations = detect_ai_patterns(article_markdown)

    # Score: start 100, subtract for similarity overages, violations, heading reuse.
    score = 100.0
    for kind, sim in section_similarity.items():
        over = sim - SECTION_SIM_MAX.get(kind, 0.85)
        if over > 0:
            score -= over * 100
    score -= max(0.0, heading_sim - HEADING_STRUCT_MAX) * 50
    score -= len(violations) * 4
    score = max(0.0, min(100.0, score))

    passed = (not regenerate) and (not violations) and score >= MIN_ORIGINALITY_SCORE

    report = {
        "agent": "agent_19_originality",
        "version": "4.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "originality_score": round(score, 2),
        "passed": passed,
        "min_score": MIN_ORIGINALITY_SCORE,
        "regenerate_sections": sorted(set(regenerate)),
        "heading_similarity": round(heading_sim, 4),
        "section_similarity": section_similarity,
        "violations": violations,
        "corpus_size": len(corpus),
    }
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "Agent 19 score=%.1f passed=%s regen=%s violations=%d -> %s",
        score, passed, report["regenerate_sections"], len(violations), out,
    )
    return report


def _load_corpus_from_dir(path: str) -> List[Dict]:
    p = Path(path)
    if not p.exists():
        return []
    docs = []
    for f in sorted(p.glob("*.md")):
        docs.append({"markdown": f.read_text(encoding="utf-8")})
    return docs


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Agent 19 - Originality Engine (V4)")
    parser.add_argument("--input", required=True, help="article markdown file")
    parser.add_argument("--corpus-dir", default="output/published_corpus")
    parser.add_argument("--output", default="output/agent_19/originality_report.json")
    args = parser.parse_args()

    markdown = Path(args.input).read_text(encoding="utf-8")
    corpus = _load_corpus_from_dir(args.corpus_dir)
    report = run_originality_check(markdown, corpus, args.output)

    if report["passed"]:
        sys.exit(0)
    if report["regenerate_sections"]:
        sys.exit(2)  # caller should regenerate listed sections
    sys.exit(1)


if __name__ == "__main__":
    main()
