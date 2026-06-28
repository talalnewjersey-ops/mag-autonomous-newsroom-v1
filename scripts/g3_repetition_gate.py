#!/usr/bin/env python3
"""
NEXUS-14 Sprint 2 -- Gate G3: anti-repetition gate (BLOCKING).

Runs AFTER the writer (agent_04) and BEFORE QA. Two checks, both deterministic
and LLM-free:

  1. SECTION SIMILARITY: TF cosine similarity between every pair of body
     sections. If any pair >= COSINE_THRESHOLD, the article is blocked.
  2. DUPLICATE PHRASES: any contiguous run of >= MIN_DUP_WORDS content words
     appearing verbatim in two different sections blocks the article.

Thresholds are FROZEN by calibration on real run #158 articles:
  - COSINE_THRESHOLD = 0.80  (legit max observed 0.59; true dups 0.92-1.00)
  - MIN_DUP_WORDS    = 8

Exit code 0 = PASS, 1 = FAIL (blocking). A JSON report is always written.
"""
import argparse
import json
import math
import re
import sys
from collections import Counter

COSINE_THRESHOLD = 0.80
MIN_DUP_WORDS = 8

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "for", "on", "with",
    "as", "by", "is", "are", "be", "this", "that", "your", "you", "it", "at",
    "from", "will", "can", "your", "their", "they", "we", "our",
}


def _split_sections(markdown):
    """Split an article into (title, body) sections on H2 (## ) boundaries.
    Front-matter and the H1 title block are ignored."""
    # Drop YAML front matter.
    md = re.sub(r"^---\n.*?\n---\n", "", markdown, count=1, flags=re.DOTALL)
    parts = re.split(r"(?m)^##\s+", md)
    sections = []
    for p in parts[1:]:  # parts[0] is intro/preamble before first H2
        line, _, rest = p.partition("\n")
        sections.append((line.strip(), rest.strip()))
    # include the preamble (intro) as its own pseudo-section if non-trivial
    if parts and len(parts[0].split()) > 30:
        sections.insert(0, ("__intro__", parts[0].strip()))
    return sections


def _tokens(text):
    return [w for w in _WORD_RE.findall(text.lower()) if w not in _STOP]


def _cosine(a_counts, b_counts):
    common = set(a_counts) & set(b_counts)
    dot = sum(a_counts[t] * b_counts[t] for t in common)
    na = math.sqrt(sum(v * v for v in a_counts.values()))
    nb = math.sqrt(sum(v * v for v in b_counts.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _duplicate_phrases(tokens_by_section, min_words):
    """Return list of (i, j, phrase) for verbatim content runs shared across
    two distinct sections."""
    shingles = []
    for idx, toks in enumerate(tokens_by_section):
        sset = {}
        for k in range(len(toks) - min_words + 1):
            sh = " ".join(toks[k:k + min_words])
            sset[sh] = True
        shingles.append(sset)
    dups = []
    n = len(shingles)
    for i in range(n):
        for j in range(i + 1, n):
            common = set(shingles[i]) & set(shingles[j])
            for sh in list(common)[:3]:
                dups.append((i, j, sh))
    return dups


def evaluate(markdown, cosine_threshold=COSINE_THRESHOLD, min_dup_words=MIN_DUP_WORDS):
    sections = _split_sections(markdown)
    titles = [t for t, _ in sections]
    tokens_by_section = [_tokens(b) for _, b in sections]
    counts = [Counter(t) for t in tokens_by_section]

    pairs = []
    max_sim = 0.0
    for i in range(len(counts)):
        for j in range(i + 1, len(counts)):
            sim = _cosine(counts[i], counts[j])
            max_sim = max(max_sim, sim)
            if sim >= cosine_threshold:
                pairs.append({"section_a": titles[i], "section_b": titles[j],
                              "cosine": round(sim, 4)})

    dups = _duplicate_phrases(tokens_by_section, min_dup_words)
    dup_report = [{"section_a": titles[i], "section_b": titles[j], "phrase": sh}
                  for (i, j, sh) in dups]

    passed = not pairs and not dup_report
    return {
        "gate": "G3_anti_repetition",
        "passed": passed,
        "cosine_threshold": cosine_threshold,
        "min_dup_words": min_dup_words,
        "section_count": len(sections),
        "max_pairwise_cosine": round(max_sim, 4),
        "over_threshold_pairs": pairs,
        "duplicate_phrases": dup_report,
        "decision": "PASS" if passed else "FAIL",
    }


def main():
    ap = argparse.ArgumentParser(description="Gate G3 anti-repetition (blocking)")
    ap.add_argument("--input", required=True, help="article_draft.md")
    ap.add_argument("--output", required=True, help="g3_report.json")
    ap.add_argument("--cosine-threshold", type=float, default=COSINE_THRESHOLD)
    ap.add_argument("--min-dup-words", type=int, default=MIN_DUP_WORDS)
    args = ap.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            markdown = f.read()
    except OSError as e:
        print("G3 ERROR: cannot read input: %s" % e, file=sys.stderr)
        sys.exit(1)

    result = evaluate(markdown, args.cosine_threshold, args.min_dup_words)

    import os
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    if result["passed"]:
        print("G3 PASS: max cosine %.4f < %.2f, no duplicate phrases"
              % (result["max_pairwise_cosine"], args.cosine_threshold))
        sys.exit(0)
    print("G3 FAIL: %d over-threshold pair(s), %d duplicate phrase(s)"
          % (len(result["over_threshold_pairs"]), len(result["duplicate_phrases"])),
          file=sys.stderr)
    # CI VISIBILITY: list each violation in the logs so no artifact is needed to inspect repetition.
    for _p in result["over_threshold_pairs"]:
        print("  G3 COSINE: \"%s\" <-> \"%s\" cosine=%.4f"
              % (_p["section_a"], _p["section_b"], _p["cosine"]), file=sys.stderr)
    for _d in result["duplicate_phrases"]:
        print("  G3 DUP: [%s] <-> [%s] | \"%s\""
              % (_d["section_a"], _d["section_b"], _d["phrase"]), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
