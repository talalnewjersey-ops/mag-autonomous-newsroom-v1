"""LEVIER C -- fact-coverage predicate (single source of truth).

Closes the "proximity-false-sourced" blind spot: an allow-listed (.gov/.gc.ca)
link sitting within +-150 chars of a number was, until now, treated as PROOF
that the number is sourced (agents/agent_05_fact_checker.py + scripts/
soften_claims.py) or that a Couche 1 fact was "cited" (scripts/
g_substance_gate.py, plain `source_url in content` substring check). A real
link only proves the LINK is genuine -- not that the figure next to it is the
one that link actually supports (real incident, run 28731153809: "under 10%"
kept because the CFPB en-318 link -- which supports 30% -- sat nearby).

Approach (validated 2026-07-05): match a numeric claim against the EXACT
engraved value of a Couche 1 STABLE fact (agents/_vertical_facts.py) whose
source_url is the one actually in the window. STRICT normalization, NO
tolerance -- if a claim cannot be shown to equal an engraved value, it is
treated as UNCOVERED (soften/GATE A strip it) even though an official link is
right there. This is "B, not C": no live fetch of the source page, no LLM
judge -- only the facts already verified by hand in Couche 1. A number near a
generic source-pool link (no engraved fact) is ALWAYS uncovered under this
rule; growing coverage means extending Couche 1, not loosening this gate.

QUALITATIVE-FACT GUARD (the delicate case): a Couche 1 fact whose engraved
`value` carries NO numeric token (e.g. "Credit score factors" -- five factors,
explicitly no percentage/no ranking) can never COVER a numeric claim -- it has
nothing numeric to confirm. Two consequences, deliberately different:
  - the fact ITSELF, cited near its own link with no number nearby, is
    legitimate and must not be touched (nothing to strip -- soften only acts
    on _NUM_RE matches) and must still count as "cited" for G-Substance (via
    plain source_url presence -- there is no number to misattribute);
  - a NUMBER that appears next to that same link (e.g. a fabricated FICO
    weighting sitting beside the usa.gov/credit-score "five factors, no %"
    fact -- the exact real-run pattern that motivated PR #44) is NEVER
    covered by it, because `_fact_tokens` for a qualitative fact is empty and
    an empty token set can match nothing. It falls through to whatever OTHER
    candidate fact might cover it (there may be none) -- so it is stripped.

LEVIER C PART 2 (2026-07-05): the same predicate now also covers BARE duration/
count claims (days/weeks/months/years/bureaus -- see agents/_claims.py's
_NUM_RE for the exact scoping and what it deliberately excludes). No new
mechanism: `_token` just gained a branch for this shape, `covering_fact` /
`classify_claims` / `count_cited_stable_facts` are unchanged, so GATE A,
Couche 2 soften, and G-Substance inherit it identically (same symmetry as
part 1 -- one shared regex, one shared predicate, three consumers).
"""
import re

from agents._claims import _ATTR_RE, _NUM_RE, _URL_IN
from agents._vertical_facts import VERTICAL_FACTS

# PROXIMITY CHECK REDESIGN (2026-07-06): a fixed character window was tried
# first (100, then widened to 150 -- see git history/tests/test_proximity_
# window_150.py) but kept getting beaten by longer real sentences: Texas/NY
# state minimums sat 119/134 chars from their citation (fixed by 150), then a
# THIRD real case -- "students must wait at least 10 days after U.S. arrival
# and at least 2 government business days after their SEVIS record is marked
# Active before applying for a state driver's license -- [DHS link]" -- sat
# 203 chars away, beating 150 too. A fixed window is structurally guaranteed
# to keep losing this way; there is no "big enough" number, only a bigger
# real sentence waiting to be written.
#
# Replaced with a SENTENCE boundary: a claim's citation is "nearby" if it
# sits in the SAME SENTENCE, regardless of how many words that takes -- see
# _sentence_span(). This closes the whole class of "longer sentence beats
# the window" false positives, not just the 3 instances found so far.
#
# SAFE BY CONSTRUCTION, same argument as the old fixed window: widening what
# counts as "nearby" can only affect whether the CORRECT source_url is found
# -- it can never relax `covering_fact`'s separate, unconditional requirement
# that the claim's own numeric token exactly equal one of that fact's
# engraved tokens. A fabricated/divergent value in the same sentence as the
# right link still stays uncovered (verified with a window of 999999 chars
# in the old design; a same-sentence span is bounded even MORE tightly than
# that, so the property holds a fortiori).
#
# TABLE-ROW / PARAGRAPH SAFETY: markdown table cells rarely contain a period,
# so a naive "nearest .!?" search could otherwise let a claim in one table
# row "borrow" a citation from unrelated PROSE many paragraphs later (a real
# near-miss found during this redesign: a comparison table's last row sat
# right before a citation-bearing paragraph with no period in between). Two
# extra, deliberately conservative stops close this: a table row (a line
# starting with "|") never looks past its OWN line; ordinary prose never
# looks past the nearest blank line (paragraph break) in either direction.
# Both are real structural boundaries in this project's article format, not
# arbitrary cutoffs.

# The attribution-cue check (below) is a SEPARATE, narrower heuristic ("does an
# 'according to'/'reports'/'says'-style word sit near this claim") -- kept at
# its original 100 deliberately. Widening it to 150 exposed a real side effect
# in testing: a long .gov URL's own slug can contain a cue-shaped substring
# (e.g. ".../credit-report-en-323" -- "report" matches \breports?\b) that a
# wider window reaches into, misclassifying `is_attr` for a citation that was
# never actually attributed in prose. Not this fix's scope to redesign (would
# need URL-masking before the cue search); keeping this window unchanged avoids
# the regression entirely.
_ATTR_CUE_WINDOW_CHARS = 100

_BLANK_LINE_RE = re.compile(r"\n[ \t]*\n")
# A period is NOT a sentence end if the character right before it is a single
# uppercase letter that itself starts a word (the "U."/"S." shape of "U.S.",
# "N.Y.", etc.) -- a real case found while testing this redesign: without this
# guard, "...after U.S. arrival..." was cut mid-abbreviation, right after "U.",
# which excluded the actual citation later in the same real sentence.
_SENTENCE_END_RE = re.compile(r"(?<!\b[A-Z])[.!?]")
# A markdown link's DISPLAY TEXT is sometimes itself a domain-shaped string,
# e.g. "[studyinthestates.dhs.gov](https://studyinthestates.dhs.gov/...)" --
# another real case found while testing this redesign: the dots in the
# display text (which comes BEFORE the real URL) were being treated as
# sentence-enders, cutting the span short before the actual https:// URL
# even started. A period/link-dot anywhere inside a markdown link's span
# (display text OR URL) must never end a sentence -- the whole link is one
# atomic unit.
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\([^)]*\)")


def _link_spans(text):
    return [(m.start(), m.end()) for m in _MD_LINK_RE.finditer(text)]


def _inside_a_link(pos, link_spans):
    return any(s <= pos < e for (s, e) in link_spans)


def _block_span(text, pos):
    """[lo, hi) of the paragraph/table-row containing `pos`. A markdown TABLE
    ROW (a line starting with "|") never extends beyond its own line -- rows
    rarely contain a period, and must never borrow a citation from an
    unrelated row or from prose that follows the table. Ordinary prose is
    bounded by the nearest blank line (paragraph break) on either side -- a
    real structural boundary in this project's article format, not an
    arbitrary cutoff."""
    line_start = text.rfind("\n", 0, pos) + 1
    line_end_idx = text.find("\n", pos)
    line_end = line_end_idx if line_end_idx != -1 else len(text)
    if text[line_start:line_end].lstrip().startswith("|"):
        return line_start, line_end
    lo = 0
    for m in _BLANK_LINE_RE.finditer(text, 0, pos):
        lo = m.end()
    m2 = _BLANK_LINE_RE.search(text, pos)
    hi = m2.start() if m2 else len(text)
    return lo, hi


def _sentence_span(text, start, end, link_spans=None):
    """[lo, hi) of the sentence containing text[start:end]: bounded first by
    its paragraph/table-row block (_block_span), then narrowed to the nearest
    preceding/following sentence-ending punctuation within that block -- a
    punctuation mark INSIDE a markdown link's span (display text or URL) is
    never treated as a sentence end (see _MD_LINK_RE). No fixed length -- a
    citation anywhere in the SAME sentence is found, however long that
    sentence is. `link_spans` may be precomputed once per text by the caller
    (classify_claims) to avoid re-scanning the whole text per claim."""
    if link_spans is None:
        link_spans = _link_spans(text)
    block_lo, block_hi = _block_span(text, start)
    lo = block_lo
    for m in _SENTENCE_END_RE.finditer(text, block_lo, start):
        if not _inside_a_link(m.start(), link_spans):
            lo = m.end()
    hi = block_hi
    for m in _SENTENCE_END_RE.finditer(text, end, block_hi):
        if not _inside_a_link(m.start(), link_spans):
            hi = m.end()
            break
    return lo, hi


_UNIT_WORDS = ("percentage points", "basis points", "points", "pts", "bps")
# LEVIER C PART 2: bare duration/count units -- deliberately days/weeks/months/
# years/bureaus ONLY (hours/minutes excluded, conscious residue: see agents/
# _claims.py docstring).
_BARE_UNIT_RE = re.compile(
    r"^(\d+(?:\.\d+)?)(?:[-–—](\d+(?:\.\d+)?))?[\s-]*(?:business|calendar|nationwide)?[\s-]*"
    r"(days?|weeks?|months?|years?|bureaus?)$")


def _token(raw):
    """Normalize a _NUM_RE match to a strict (unit, value) tuple. Returns None if
    the span cannot be classified unambiguously -- an unparseable span can never
    cover, nor be covered (doubt -> strip, never a fuzzy/tolerant match)."""
    s = raw.strip().lower()
    m = re.match(r"^(\d{3})\s*[-–—]\s*(\d{3})$", s)
    if m:
        return ("score_range", (int(m.group(1)), int(m.group(2))))
    m = _BARE_UNIT_RE.match(s)
    if m:
        unit = m.group(3).rstrip("s")  # "days"/"day" -> "day", same key either way
        if m.group(2):
            return (f"{unit}_range", (float(m.group(1)), float(m.group(2))))
        return (unit, float(m.group(1)))
    for unit in _UNIT_WORDS:
        m = re.match(r"^(\d+(?:\.\d+)?)\s*" + unit.replace(" ", r"\s+") + r"$", s)
        if m:
            return (unit.replace(" ", "_"), float(m.group(1)))
    m = re.match(r"^(\d+(?:\.\d+)?)\s*%$", s)
    if m:
        return ("percent", float(m.group(1)))
    m = re.match(r"^\$\s*([\d,]+(?:\.\d+)?)$", s)
    if m:
        return ("dollar", float(m.group(1).replace(",", "")))
    m = re.match(r"^cad\s*([\d,]+(?:\.\d+)?)$", s)
    if m:
        return ("cad", float(m.group(1).replace(",", "")))
    m = re.match(r"^(\d[\d,]*(?:\.\d+)?)\s*(million|billion|thousand)$", s)
    if m:
        return (m.group(2), float(m.group(1).replace(",", "")))
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(?:times|x)$", s)
    if m:
        return ("multiplier", float(m.group(1)))
    m = re.match(r"^(\d+)\s+out of\s+(\d+)$", s)
    if m:
        return ("ratio", (int(m.group(1)), int(m.group(2))))
    m = re.match(r"^(\d{2,})\+$", s)
    if m:
        return ("threshold_plus", int(m.group(1)))
    return None


def _fact_tokens(fact):
    """Every normalized numeric token found in a fact's engraved `value`. EMPTY
    for a purely qualitative fact (no digit in `value`, e.g. the FICO-factors
    fact) -- by construction, an empty set can cover nothing (see module
    docstring, QUALITATIVE-FACT GUARD)."""
    value = fact.get("value") or ""
    return frozenset(
        t for t in (_token(m.group(0)) for m in _NUM_RE.finditer(value)) if t is not None
    )


def covering_fact(claim_raw, candidate_urls, vertical):
    """The STABLE fact of `vertical` that genuinely covers this numeric claim, or
    None. `candidate_urls` are the (already window-extracted) URL strings found
    near the claim. A fact only counts if its exact source_url is among them
    AND its engraved value contains a numeric token identical to the claim's
    (strict equality, no tolerance)."""
    tok = _token(claim_raw)
    if tok is None:
        return None
    candidates = [
        f for f in VERTICAL_FACTS.get(vertical or "", [])
        if f.get("status") == "STABLE" and f.get("value") and f["source_url"] in candidate_urls
    ]
    for f in candidates:
        toks = _fact_tokens(f)
        if toks and tok in toks:  # empty toks (qualitative fact) can never cover a number
            return f
    return None


def _default_url_finder(text):
    """URLs whose span OVERLAPS a given [lo, hi) window in `text`. Finds every URL
    in the WHOLE text once, then filters by span -- never slices the window
    first: a long .gov URL (often 80-100+ chars) sliced at +-100 chars would be
    truncated mid-string, and a truncated URL can never string-equal an engraved
    source_url, which would silently defeat every coverage match."""
    spans = [(m.start(), m.end(), m.group(0)) for m in _URL_IN.finditer(text)]

    def finder(lo, hi):
        return [u for (s, e, u) in spans if s < hi and e > lo]
    return finder


def classify_claims(text, vertical, url_finder=None):
    """One pass over every _NUM_RE match in `text`: for each, resolve the URLs
    whose citation is in the SAME SENTENCE (via `_sentence_span`, then
    `url_finder(lo, hi)`, default = `_default_url_finder(text)` on the
    unmasked text -- callers on masked text, e.g. soften_claims, pass a
    mask-aware finder with the same overlap-not-slice contract) and try to
    attach a covering STABLE fact. Returns [{start, end, is_attr, fact}],
    `fact` is None when uncovered."""
    url_finder = url_finder or _default_url_finder(text)
    link_spans = _link_spans(text)
    out = []
    for m in _NUM_RE.finditer(text):
        lo, hi = _sentence_span(text, m.start(), m.end(), link_spans=link_spans)
        fact = covering_fact(m.group(0), url_finder(lo, hi), vertical)
        attr_lo = max(0, m.start() - _ATTR_CUE_WINDOW_CHARS)
        attr_hi = min(len(text), m.end() + _ATTR_CUE_WINDOW_CHARS)
        is_attr = fact is None and bool(_ATTR_RE.search(text[attr_lo:attr_hi]))
        out.append({"start": m.start(), "end": m.end(), "is_attr": is_attr, "fact": fact})
    return out


def count_cited_stable_facts(content, vertical, claims=None):
    """G-Substance helper: distinct STABLE facts of `vertical` genuinely cited in
    `content`. A QUALITATIVE fact (no numeric value -- nothing to misattribute)
    counts via plain source_url presence, same as before this lot. A NUMERIC
    fact counts ONLY if `classify_claims` matched an actual claim to it (a real,
    value-correct citation -- not just its link sitting somewhere in the page)."""
    if claims is None:
        claims = classify_claims(content, vertical)
    numeric_cited = {c["fact"]["source_url"] for c in claims if c["fact"]}
    qualitative_cited = {
        f["source_url"] for f in VERTICAL_FACTS.get(vertical or "", [])
        if f.get("status") == "STABLE" and f.get("value")
        and not _fact_tokens(f) and f["source_url"] in content
    }
    return len(numeric_cited | qualitative_cited)
