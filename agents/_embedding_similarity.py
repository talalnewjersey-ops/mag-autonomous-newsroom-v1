"""Semantic similarity for the cannibalization gate (Task 4 proposal, 2026-07-19).

WHY THIS EXISTS: agent_17_cannibalization.py already computes two lexical
signals (SequenceMatcher title similarity, Jaccard keyword overlap) and takes
their max. Empirically, on 5 confirmed real-world duplicate pairs found during
the 2026-07-19 editorial audit, that combined lexical score ranged 0.44-0.80 --
FOUR of the five fell below agent_17's own 0.72 observation threshold entirely,
and none reached its 0.85 REJECT threshold. Lexical similarity cannot see that
"Best Credit Cards for Newcomers USA 2026 (No SSN Needed)" and "Best Credit
Cards For New Immigrants No Ssn: Complete Guide for USA Immigrants (2026)" are
the same page. This module adds a real semantic-similarity signal to close
that gap.

Two implementations, same interface:
  - `openai_embedding_similarity()` -- the real thing. Uses OPENAI_API_KEY
    (already a configured repo secret, used elsewhere by generate_drafts.py /
    workflows/lib/openai_client.py) and OpenAI's text-embedding-3-small.
    Threshold 0.86 on cosine similarity, per the Task 4 spec.
  - `tfidf_proxy_similarity()` -- a pure-stdlib TF-IDF cosine fallback for
    offline dry-run demonstration ONLY (e.g. this session, with no API key
    available locally). Its cosine values are NOT on the same scale as
    embedding cosine -- do not reuse the 0.86 threshold with this function.
    See PROXY_THRESHOLD below for its own, separately-calibrated cutoff.

Neither function is wired into a blocking decision anywhere by this patch --
see agent_17_cannibalization.py's diff in this same branch, which only adds
the score to the existing (already non-blocking, OBSERVE_ONLY) report.
"""
import math
import os
import re
from collections import Counter
from typing import List

STOPWORDS = {
    "a", "an", "the", "is", "in", "on", "at", "to", "for", "of", "and", "or",
    "but", "with", "how", "what", "when", "where", "why", "your", "our",
    "best", "top", "guide", "complete", "ultimate", "new", "get", "2026",
}

# Calibration result (2026-07-19), and an honest limitation, not a clean win:
# tested against the audit's 5 confirmed-duplicate pairs and 3 confirmed-
# distinct control pairs, using title+meta-description text and this repo's
# 51-post corpus as the IDF background. Scores: dupes ranged 0.19-0.57,
# controls ranged 0.13-0.38 -- THE RANGES OVERLAP. No single threshold
# separates the two classes cleanly; 0.30 below catches 3 of 5 known dupes
# and flags 1 of 3 controls (itself a genuine partial-overlap case per the
# audit, not a clean miss). This is not a tuning failure -- it is the
# expected ceiling of ANY lexical method (SequenceMatcher, Jaccard, or
# TF-IDF alike) on this domain, where duplicate pages describe the same
# real-world entities (e.g. "Wise, Remitly, TD, RBC") in deliberately varied
# marketing language. Treat this constant, and this whole function, as an
# illustrative stand-in for the dry-run log only -- it is NOT a substitute
# for openai_embedding_similarity() in production, and should not be tuned
# further in the hope of matching embedding-grade separation; it structurally
# cannot get there.
PROXY_THRESHOLD = 0.30


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def _tfidf_vectors(corpus_texts: List[str]) -> List[Counter]:
    """Return one TF-IDF weight vector (as a Counter) per input text, using
    the full corpus_texts list as the IDF background."""
    tokenized = [_tokenize(t) for t in corpus_texts]
    df = Counter()
    for tokens in tokenized:
        for term in set(tokens):
            df[term] += 1
    n_docs = len(corpus_texts)
    vectors = []
    for tokens in tokenized:
        tf = Counter(tokens)
        vec = Counter()
        for term, count in tf.items():
            idf = math.log((n_docs + 1) / (df[term] + 1)) + 1.0
            vec[term] = count * idf
        vectors.append(vec)
    return vectors


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[t] * b.get(t, 0.0) for t in a)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def tfidf_proxy_similarity(candidate_text: str, existing_texts: List[str]) -> List[float]:
    """DRY-RUN PROXY ONLY -- see module docstring. Returns one cosine score
    per entry in existing_texts, using the combined set as the IDF background."""
    all_texts = [candidate_text] + list(existing_texts)
    vectors = _tfidf_vectors(all_texts)
    candidate_vec, existing_vecs = vectors[0], vectors[1:]
    return [_cosine(candidate_vec, v) for v in existing_vecs]


def openai_embedding_similarity(candidate_text: str, existing_texts: List[str]) -> List[float]:
    """Real semantic similarity via OpenAI text-embedding-3-small. Requires
    OPENAI_API_KEY. Raises RuntimeError if the key is not set -- callers
    should catch this and fall back to tfidf_proxy_similarity() with a loud
    log line, never silently, so a missing key is visible in run logs rather
    than quietly degrading gate quality."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set -- real embedding similarity unavailable. "
            "Caller must explicitly fall back to tfidf_proxy_similarity() and "
            "log that the gate is running in degraded (lexical-proxy) mode."
        )
    import openai  # local import: only required when this path actually runs
    client = openai.OpenAI(api_key=api_key)
    all_texts = [candidate_text] + list(existing_texts)
    resp = client.embeddings.create(model="text-embedding-3-small", input=all_texts)
    vectors = [d.embedding for d in resp.data]
    candidate_vec, existing_vecs = vectors[0], vectors[1:]

    def cos(u, v):
        dot = sum(x * y for x, y in zip(u, v))
        nu = math.sqrt(sum(x * x for x in u))
        nv = math.sqrt(sum(x * x for x in v))
        return dot / (nu * nv) if nu and nv else 0.0

    return [cos(candidate_vec, v) for v in existing_vecs]
