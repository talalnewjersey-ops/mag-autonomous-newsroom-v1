"""Couche 2 -- deterministic soften pass (NON-BLOCKING).

Runs after agent_04 and before the fact-check gate. For every UNSOURCED numeric
claim (same predicate as the Sprint 10 detection: a _NUM_RE match with no
allow-listed citation within +-100 chars) it removes the fabricated FIGURE while
keeping the directional clause -- never trusting the writer, exactly like the
Sprint 8 sanitizer. It does NOT reject anything: it rewrites the draft and emits
a report. The blocking decision belongs to Couche 3 (G-Substance).

LINK SAFETY (filets-v2, point 3): before doing anything, every markdown link and
bare URL is MASKED to an atomic, indexed placeholder that carries only whether the
link is allow-listed (.gov / canada.ca). All soften operations run on the masked
text, so no strip can ever reach into a URL (a real run once ate a .gov URL tail
when an attribution cue -- "reports" -- happened to sit inside the URL path). Links
are restored byte-for-byte at the end. The placeholder also makes the "is this
number sourced?" check robust to long URLs the +-100 window would otherwise clip.

LEVIER C (2026-07-05): "sourced" no longer means "an allow-listed link sits in
the window" -- it means the number matches the EXACT engraved value of a
Couche 1 STABLE fact whose source_url is that link (agents/_fact_coverage.py).
A number near a link is otherwise treated as unsourced and stripped, even if
the link is a real, live .gov page -- see agents/_fact_coverage.py docstring
for the qualitative-fact guard and the "en cas de doute, on strip" rule.

Rules (mechanical, never the LLM):
  - prose: strip the number + its quantifier ("by 20-40% above" -> "above"); for a
    named attribution ("according to X, 15-25% lower") strip the cue + number too.
  - table row (line starts with '|'): replace the whole offending cell with a FIXED
    qualifying phrase (see COMMERCIAL-FIGURE QUALIFICATION below) -- never "varies"
    alone.
  - after a prose strip, if the residual sentence has fewer than --min-residue-words
    words it is deleted; otherwise the clause is kept.

COMMERCIAL-FIGURE QUALIFICATION (2026-07-05, table-scoped): an unsourced figure in
a COMPARISON TABLE CELL is where the real damage was observed (HISA incident: a
firm, inconsistent commercial rate presented as fact across sections/rows of the
same table). Couche 1 never engraves commercial figures (rates, prices) -- only
government facts -- so a table cell can NEVER be "covered" for that kind of claim,
by design. Rather than a bare "varies", the cell is replaced with the FIXED,
constant phrase _TABLE_QUALIFIER ("varies by provider — confirm directly") --
literal, never templated/generated, so it can never itself invent or vary a
figure. Deliberately TABLE-SCOPED ONLY: short prose already strips-and-keeps-the-
clause well (proven on the insurance article's commercial figures); repeating the
qualifier in prose too would be noisier for no real gain. Confirmed no G3 conflict:
the phrase is 4 content words (G3's duplicate-phrase floor is 8) and an empirical
G3 run with it repeated 12+ times in one table still PASSES (max cosine 0.68 <
0.80 threshold). Extend beyond tables only if a re-run shows commercial
inconsistencies surviving outside them.
"""
import argparse
import bisect
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents._claims import _NUM_RE, _ATTR_RE  # shared claim regexes (single source of truth)
from agents._sources import _classify_url
from agents._fact_coverage import classify_claims
from agents._source_pool import resolve_gate_vertical
from agents._placeholder_scan import scan_body  # post-strip grammar check (2026-07-23, see below)

_SENT = "\x00"  # sentinel marking a stripped figure inside a prose sentence
_SENT_FORCE = "\x01"  # CASE 5b sentinel: this sentence must be dropped, no repair attempt

# ---- link masking (point 3) ----
_MASK_OPEN, _MASK_CLOSE = "\x0e", "\x0f"
_LINK_RE = re.compile(r"\[[^\]]*\]\([^)]+\)|https?://[^\s\)\]>,;]+")  # markdown link OR bare URL
_MASK_IN = re.compile(_MASK_OPEN + r"(\d+)" + _MASK_CLOSE)

# Quantifier words that introduce a figure and should be stripped with it.
#
# "exceeding"/"totaling"/"averaging"/"reaching" added 2026-07-23 (real bug,
# post 48931 dry-run/article_2: "Fees routinely translate to APRs exceeding,
# [according to the CFPB](https://www.consumerfinance.gov/...)." -- a real,
# live .gov citation sat right next to the number and it STILL got stripped
# (LEVIER C, 2026-07-05: a link alone is never enough, the number must match
# an engraved Couche-1 fact -- working as designed here, this vertical's APR
# figure just isn't engraved). The bug is purely that these four are
# transitive VERBS, not prepositions -- the original list only ever covered
# preposition-style quantifiers that glue directly onto a bare number ("over
# 400%", "up to $75"), so a verb-form quantifier fell outside its scope and
# only the number got removed, leaving the verb dangling before punctuation.
_QUANT = re.compile(
    r"(?i)(?:\b(?:by|up to|around|about|roughly|nearly|over|under|approximately|"
    r"between|from|of|below|above|at least|at most|as much as|as little as|"
    r"as low as|as high as|exceeding|totaling|averaging|reaching)\s+)$")
# A numeric range prefix immediately before the matched figure, e.g. "20-" in "20-40%".
_RANGE_PREFIX = re.compile(r"\d[\d,\.]*\s*[–—-]\s*$")
# PLAN B (context-aware scaffold): a trailing unit token glued to the figure, e.g. "/month".
_UNIT_RE = re.compile(r"/(?:months?|years?|weeks?|days?|mo|yr|hrs?|hours?)\b", re.I)
_DASH = "—–"  # em-dash, en-dash

# CASE 5 (2026-07-24, root-cause fix after 6 rounds of GATE D whack-a-mole):
# a "bare" figure has no CASE 1/2/4 scaffold at all -- it was a plain clause
# element (verb direct object, adverbial) with nothing wrapped around it.
# CASE 5a: a single preposition immediately after the figure that was only
# there to introduce it gets swallowed too ("holding [$2,000] in savings" ->
# "holding savings"). _FORWARD_PREP_IDIOM_ALLOWLIST guards adverbial idioms
# where the preposition does NOT depend on the figure ("charges $50 on
# average" must NOT become "charges average").
_FORWARD_DANGLING_PREP = re.compile(r"(?i)\s*(of|in)\b")
# A number/currency token right after the matched preposition means it is a
# RANGE CONNECTOR ("$12 to $15", "$15-a dash-range's second half"), not a
# preposition/dash dangling on the removed figure -- must NOT be swallowed
# (the other number is its own separate unsourced-claim span, scaffolded on
# its own pass; real bug found stress-testing against 30 live published
# articles, 2026-07-24: "$15-$35/month for a solid prepaid plan" force-
# deleted the whole sentence because the FIRST number's own scaffold saw the
# internal range dash and mistook it for an unrelated appositive marker).
_LOOKS_LIKE_NUMBER_START = re.compile(r"\s*[$€£]?\d")
# A bare word-form unit directly after the figure ("$50 a month", as opposed
# to the already-handled glued "$50/month") -- same swallow as CASE 3's
# _UNIT_RE, scoped to CASE 5 so it never changes CASE 1/2/4's own boundaries.
_FORWARD_BARE_UNIT = re.compile(r"(?i)\s*a\s+(month|year|week|day)s?\b")
_FORWARD_PREP_IDIOM_ALLOWLIST = {
    "of course", "of late",
    "in general", "in fact", "in short", "in turn", "in full", "in person",
    "in total", "in place", "in effect",
}
# "for", "to", "at", "on", "with" were tried and DROPPED (2026-07-24, real
# regression found stress-testing 30 live published articles): "pay $15-$35
# for a solid prepaid plan" -> stripping the figure alone already gives the
# grammatically complete "pay for a solid prepaid plan" ("for" is the verb's
# own required complement, independent of the amount) -- swallowing "for"
# too produced "pay a solid prepaid plan" (worse, not better). No reliable
# regex-only way found to distinguish that shape from the genuinely-dangling
# "holding $X in savings" shape, so only "of"/"in" ship, and "in" gets an
# extra guard below.
#
# "in" itself has the SAME failure mode when the removed figure was the
# HEAD NOUN of an ordinal/quantifier phrase, not a verb's direct object:
# "your first [10 days] in the USA" -> "your first in the USA" (already a
# pre-existing scar, left as-is by CASE 1-4) -> swallowing "in" blindly gives
# "your first the USA" (worse: now missing "in" too, with nothing gained).
# Found on the same real-corpus stress test. _UNSAFE_IN_PREDECESSOR blocks
# the swallow specifically when the word right before the removed figure is
# one of these ordinal/quantifier adjectives -- "holding"/"with"/"showing"
# style verb-or-preposition predecessors are unaffected and still swallow.
_UNSAFE_IN_PREDECESSOR = re.compile(
    r"(?i)\b(first|next|last|few|several|couple|initial|early|final)\s*$")
# "of" has its own failure mode (found the same way, 2026-07-24): "within
# [60 days] of arrival" -> swallowing "of" alone gives "within arrival",
# missing a duration noun that "within" needs and gaining nothing -- WORSE
# than the pre-existing "within of arrival" residue, which at least GATE D's
# adjacent_connector_pair detector reliably catches (verified against the
# real verbatim bug in tests/test_placeholder_gate.py). "within X of Y" is a
# fixed collocation where "of" is never safe to swallow alone.
_UNSAFE_OF_PREDECESSOR = re.compile(r"(?i)\bwithin\s*$")


def _link_url(s):
    """Extract the bare URL from a masked-link ORIGINAL: markdown link -> the url
    inside (...); bare URL -> itself. Kept as one function so a placeholder
    resolves to the same URL for both official-classification and (LEVIER C)
    fact-coverage matching -- `originals` itself must keep the FULL markdown
    syntax (brackets + display text) for byte-exact restoration, so callers that
    need the bare url (covering_fact requires exact source_url equality) must
    go through this, not read `originals[i]` directly."""
    um = re.search(r"\(([^)]+)\)\s*$", s)   # markdown link -> url inside (...)
    return um.group(1) if um else s         # bare URL -> itself


def _mask_links(text):
    """Replace every markdown link / bare URL with an atomic indexed placeholder.
    Returns (masked_text, originals, official_indices)."""
    originals, official = [], set()
    def repl(m):
        i = len(originals)
        s = m.group(0)
        if _classify_url(_link_url(s)) == "official":
            official.add(i)
        originals.append(s)
        return _MASK_OPEN + str(i) + _MASK_CLOSE
    return _LINK_RE.sub(repl, text), originals, official


def _restore_links(text, originals):
    return _MASK_IN.sub(lambda m: originals[int(m.group(1))], text)


def _find_unsourced(masked, originals, vertical):
    """[(start, end, is_attribution)] for every _NUM_RE match in MASKED text NOT
    covered by an engraved Couche 1 STABLE fact (LEVIER C, agents/_fact_coverage.py:
    a nearby allow-listed link is no longer sufficient proof -- the number must
    match that fact's exact engraved value). Placeholders are resolved back to
    their original URL string so coverage matching sees the real source_url;
    attribution cues inside URLs can no longer fire (URLs are placeholders).
    Placeholder spans are found ONCE over the whole masked text and filtered by
    overlap with each claim's window -- same overlap-not-slice contract as
    agents._fact_coverage._default_url_finder (placeholders are short and atomic
    so slicing would rarely truncate one, but the contract stays uniform)."""
    placeholders = [(int(g.group(1)), g.start(), g.end()) for g in _MASK_IN.finditer(masked)]

    def finder(lo, hi):
        return [_link_url(originals[i]) for (i, s, e) in placeholders if s < hi and e > lo]
    return [(c["start"], c["end"], c["is_attr"])
            for c in classify_claims(masked, vertical, url_finder=finder)
            if c["fact"] is None]


def _strip_span(line, s, e, is_attr):
    """Extend the raw figure span (s, e) to also swallow a leading range prefix, a
    leading quantifier word, and -- for attributions -- the 'according to X,' cue.
    Operates on MASKED text, so it can never cross into a URL.

    LEVIER C PART 2 bugfix: the attribution-cue lookback is clamped to NEVER cross
    a DIFFERENT citation's placeholder. Found via a real case: "...report for 7
    years ([CFPB](url)). It can linger for up to 8 years..." -- the bare word
    "report" (part of the FIRST, legitimately-covered claim's own sentence) is an
    _ATTR_RE cue, and the naive 100-char lookback for the SECOND (uncovered "8
    years") claim swallowed everything back to "report", eating the first
    citation's real link and its correctly-sourced "7 years" too. A masked-link
    placeholder is an unambiguous citation boundary -- an attribution cue for THIS
    claim can never legitimately sit on the other side of a DIFFERENT citation."""
    ss = s
    m = _RANGE_PREFIX.search(line[:ss])
    if m:
        ss = m.start()
    m = _QUANT.search(line[:ss])
    if m:
        ss = m.start()
    if is_attr:
        lo = max(0, s - 100)
        for pm in _MASK_IN.finditer(line, lo, s):
            lo = max(lo, pm.end())
        cues = list(_ATTR_RE.finditer(line[lo:s]))
        if cues:
            ss = min(ss, lo + cues[-1].start())
    return ss, e


def _content_word_count(s):
    """Alphabetic words remaining after masked links + markup/punctuation are removed."""
    s = _MASK_IN.sub("", s)
    s = re.sub(r"[*_`#>|~$%(),.;:!?/" + _DASH + r"-]", " ", s)
    return sum(1 for w in s.split() if any(c.isalpha() for c in w))


def _sourced_inside(segment, official):
    """True if `segment` holds a masked placeholder for an official (allow-listed) link."""
    return any(int(g) in official for g in _MASK_IN.findall(segment))


def _scaffold_span(line, ss, ee, official, max_appos_words):
    """PLAN B: extend an (already left-trimmed) unsourced-figure span (ss, ee) to also
    swallow the IMMEDIATE DELIMITED scaffold that only existed to present the number:
    a trailing /unit, an enclosing ( ), ** **, or — — appositive. Removal-only; the
    extension STOPS at the delimiter and never crosses it. Suppressed whenever the
    scaffold holds sourced content (an official link) so a citation is never deleted.
    Operates on MASKED text (URLs are placeholders).

    Returns (ss, ee, force_delete_sentence) -- force_delete_sentence is True only
    for CASE 5b (see below); every other case returns False."""
    orig_ss = ss  # CASE 5's openness checks below must use the ORIGINAL left
                  # boundary, not one CASE 2's 2b branch may tighten further.
    # CASE 3 -- trailing unit token immediately after the figure -> extend RIGHT.
    um = _UNIT_RE.match(line, ee)
    if um:
        ee = um.end()
    # CASE 1 -- enclosing parenthesis ( ... ) with the figure inside and no nested ')'.
    op, cp = line.rfind("(", 0, ss), line.find(")", ee)
    if op != -1 and cp != -1 and ")" not in line[op + 1:ss] and "(" not in line[ee:cp]:
        if not _sourced_inside(line[op + 1:cp], official) and \
           _content_word_count(line[op + 1:ss] + " " + line[ee:cp]) <= 6:
            ss, ee = op, cp + 1
            if ee < len(line) and line[ee] == " ":
                ee += 1                       # swallow one adjacent space, keep grammar tight
            elif ss > 0 and line[ss - 1] == " ":
                ss -= 1
            return ss, ee, False              # parenthetical is self-contained -> done
    # CASE 4 -- enclosing em-dash appositive — ... — (or — ... . / — ... <eol>).
    dl = max((line.rfind(d, 0, ss) for d in _DASH), default=-1)
    if dl != -1 and not any(c in line[dl + 1:ss] for c in ".!?"):
        rest = line[ee:]
        m = re.search(r"[" + _DASH + r".!?]", rest)
        if m and rest[m.start()] in _DASH:
            dr, tail = ee + m.start() + 1, line[ee:ee + m.start()]   # consume closing dash
        elif m:
            dr, tail = ee + m.start(), line[ee:ee + m.start()]       # stop before sentence-end
        else:
            dr, tail = len(line), rest                              # runs to end of line
        if not _sourced_inside(line[dl + 1:dr], official) and \
           _content_word_count(line[dl + 1:ss] + " " + tail) <= max_appos_words:
            return dl, dr, False
    # CASE 2 -- enclosing bold ** ... **.
    bl, br = line.rfind("**", 0, ss), line.find("**", ee)
    if bl != -1 and br != -1 and "**" not in line[bl + 2:ss] and "**" not in line[ee:br]:
        if not _sourced_inside(line[bl + 2:br], official):
            if _content_word_count(line[bl + 2:ss] + " " + line[ee:br]) == 0:
                ss, ee = bl, br + 2           # 2a: bold holds only the figure -> remove it all
            else:
                while ss > 0 and line[ss - 1] == " ":   # 2b: keep the label -> **label** tight
                    ss -= 1
    # CASE 5 -- truly bare figure: none of CASE 1/2/4 has a GENUINELY OPEN
    # scaffold around this figure. 2026-07-25 bugfix (real dry-run evidence,
    # post 48945 GATE D finding "with of flawless repayment"): the original
    # gate checked bare op/dl/bl != -1, which only means "rfind found SOME
    # delimiter character somewhere earlier in the line" -- NOT that it still
    # encloses this figure. A completely unrelated, already-CLOSED "(...)"
    # earlier in the same paragraph (e.g. "(Equifax, Experian, TransUnion)")
    # was silently disqualifying every later bare figure in that line from
    # CASE 5, even though CASE 1 itself had already correctly determined that
    # parenthetical was irrelevant (its own cp lookup failed). Re-derive
    # "genuinely open" with the SAME conditions CASE 1/2/4 use internally.
    #
    # A parenthesis/dash/bold that IS genuinely open but was declined (too
    # many words, sourced content) is a DIFFERENT, already-tested tradeoff
    # (e.g. the long-appositive "at of your score" residue locked in by
    # test_guard_long_appositive_is_kept_number_only_stripped) and is
    # deliberately left untouched here -- one fix at a time.
    paren_open = op != -1 and ")" not in line[op + 1:orig_ss]
    dash_open = dl != -1 and not any(c in line[dl + 1:orig_ss] for c in ".!?")
    bold_open = bl != -1 and "**" not in line[bl + 2:orig_ss]
    if not paren_open and not dash_open and not bold_open:
        # CASE 5a -- default: reformulate cleanly (user-approved option "a").
        # A bare word-form unit ("a month") is swallowed first so a trailing
        # preposition check below (if any) sees the text that actually
        # follows it, not the unit itself.
        um2 = _FORWARD_BARE_UNIT.match(line, ee)
        if um2:
            ee = um2.end()
        fm = _FORWARD_DANGLING_PREP.match(line, ee)
        if fm and not _LOOKS_LIKE_NUMBER_START.match(line, fm.end()):
            prep = fm.group(1).lower()
            idiom = " ".join(w.lower().strip(".,;:!?") for w in line[ee:].split()[:2])
            allowed = idiom not in _FORWARD_PREP_IDIOM_ALLOWLIST
            if prep == "in" and _UNSAFE_IN_PREDECESSOR.search(line[:ss]):
                allowed = False
            if prep == "of" and _UNSAFE_OF_PREDECESSOR.search(line[:ss]):
                allowed = False
            if allowed:
                return ss, fm.end(), False
        if um2:
            return ss, ee, False  # unit swallowed even if no trailing prep followed it
        # CASE 5b -- last resort: nothing forward to swallow, and the figure
        # is immediately followed by an unrelated appositive dash (not one
        # that encloses it -- that is CASE 4, and not a range separator --
        # guarded by _LOOKS_LIKE_NUMBER_START, see above). The clause's
        # object is simply gone with no local text to repair it with; drop
        # the whole sentence rather than leave a scar (user-approved option
        # "c", never a stub).
        dm = re.match(r"\s*[" + _DASH + r"]", line[ee:])
        if dm and not _LOOKS_LIKE_NUMBER_START.match(line[ee:][dm.end():]):
            return ss, ee, True
    return ss, ee, False


def _clean(fragment):
    """Tidy whitespace/punctuation left behind by a strip (sentinels removed)."""
    s = fragment.replace(_SENT, "").replace(_SENT_FORCE, "")
    # Hold a leading list marker ("- ", "* ", "+ ", "1. ") OUT of the cleanup: the
    # "leading junk" strip below has '-' in its char class and would otherwise eat a
    # bullet's dash. The marker is RE-ATTACHED verbatim (nothing new is introduced).
    m = re.match(r"\s*(?:[-*+]|\d+\.)\s+", s)
    marker = (m.group(0).strip() + " ") if m else ""
    if m:
        s = s[m.end():]
    s = re.sub(r"\*\*\s*\*\*", "", s)         # empty bold left by a stripped **30%**
    s = re.sub(r"\(\s*\)", "", s)             # empty parens
    s = re.sub(r"\s+([,.;:%!?\)])", r"\1", s) # space before punctuation / close-paren
    s = re.sub(r"([(–—-])\s+", r"\1", s)
    s = re.sub(r",\s*,", ",", s)              # doubled commas
    s = re.sub(r"\s{2,}", " ", s)             # collapse runs of spaces
    s = re.sub(r"^[\s,;:–—-]+", "", s)        # leading junk (marker safely held out)
    return marker + s.strip()


# LEVIER C commercial-figure qualification (table-scoped, see module docstring).
# FIXED and CONSTANT -- never templated/generated from article content, so it can
# never itself invent or vary a figure.
_TABLE_QUALIFIER = "varies by provider — confirm directly"


def _soften_table_row(line, spans_local, report):
    """Replace each pipe cell that contains an unsourced figure with the fixed
    _TABLE_QUALIFIER phrase (never a bare 'varies', never generated)."""
    cells, pos, out = line.split("|"), 0, []
    for cell in cells:
        start, end = pos, pos + len(cell)
        pos = end + 1  # account for the '|' separator
        if any(start <= s < end for (s, _e, _a) in spans_local):
            out.append(f" {_TABLE_QUALIFIER} ")
            report["table_cells_softened"] += 1
        else:
            out.append(cell)
    return "|".join(out)


_LIST_MARKER_LINE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")


def _soften_prose(line, spans_local, min_words, report, official=frozenset(), max_appos_words=4):
    """Strip figures leaving a sentinel, then drop any sentence the strip reduced
    below min_words; keep the clause otherwise. Extended strip-spans are MERGED
    first so overlapping ranges (e.g. "$200-$500") cannot corrupt each other.
    PLAN B: each span is grown to swallow its immediate delimited scaffold so no
    scar (dangling '(', '/month', '**', '— —') is ever created."""
    # A numbered marker's OWN period ("1. ") is indistinguishable from a
    # sentence-ending period to the split below, so a list line's first
    # "sentence" piece is really just its marker, split off from the rest of
    # the line -- harmless before 2026-07-23 (that orphaned tail always
    # survived), but the new post-strip grammar check below would otherwise
    # flag it as a lone unpunctuated fragment and delete real list content.
    # List lines are legitimately exempt from terminal punctuation anyway
    # (same convention as agents/_placeholder_scan.py's own list-line
    # exclusion), so skip the check entirely rather than special-case the
    # split.
    is_list_line = bool(_LIST_MARKER_LINE.match(line))
    strips = []
    for (s, e, is_attr) in spans_local:
        ss, ee = _strip_span(line, s, e, is_attr)
        ss, ee, force_delete = _scaffold_span(line, ss, ee, official, max_appos_words)
        strips.append([ss, ee, force_delete])
        report["stripped"] += 1
    strips.sort(key=lambda t: t[0])
    merged = []
    for st in strips:
        if merged and st[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], st[1])
            merged[-1][2] = merged[-1][2] or st[2]  # CASE 5b force-delete wins on overlap
        else:
            merged.append(st)
    for ss, ee, force_delete in sorted(merged, key=lambda t: t[0], reverse=True):
        line = line[:ss] + (_SENT_FORCE if force_delete else _SENT) + line[ee:]
    kept = []
    for sentence in re.split(r"(?<=[.!?])\s+", line):
        if _SENT not in sentence and _SENT_FORCE not in sentence:
            kept.append(sentence)
            continue
        if _SENT_FORCE in sentence:
            # CASE 5b: unrepairable, drop unconditionally -- never a stub.
            report["sentences_deleted"] += 1
            report["case5_forced_deletions"] = report.get("case5_forced_deletions", 0) + 1
            continue
        cleaned = _clean(sentence)
        if len(cleaned.split()) < min_words:
            report["sentences_deleted"] += 1  # gutted stat sentence -> drop it
            continue
        # 2026-07-23: a strip can leave a FORWARD dependency orphaned even when
        # the residual clause is long enough to survive the word-count check --
        # e.g. "generates [6 months] of on-time payment history" -> "generates
        # of on-time payment history" (real bug, post 48931/article_2). _QUANT
        # only ever swallows quantifier words BACKWARD from the figure; nothing
        # here repairs a complement phrase that depended on the removed number
        # forward of it. Rather than attempt a risky general forward-grammar
        # repair (same idiom false-positive trap as a broader GATE D detector
        # would hit -- "pay in full"/"pay on time" are fine without a number),
        # reuse the same battle-tested scan_body() detectors GATE D uses and
        # drop the whole sentence if the repaired clause still reads broken.
        # Safe here specifically because this pass is NON-BLOCKING: worst case
        # is one extra deleted sentence, never a corrupted one reaching GATE D.
        #
        # EXCEPT "adjacent_connector_pair" (2026-07-24): _scaffold_span's own
        # CASE 4 deliberately KEEPS a long em-dash appositive rather than
        # deleting it, accepting a minor residue scar as the tradeoff for not
        # losing real informative content (e.g. "at 35 percentage points of
        # your score" -> "at of your score" once the unsourced number is
        # stripped -- tests/test_lot_soften_scaffold.py locks this exact
        # tradeoff in by name). That "at of" shape is exactly what GATE D's
        # generic adjacent-connector-pair detector now catches -- correct
        # for GATE D's job, but it would silently overrule CASE 4's own
        # keep-the-content decision if reused here unfiltered. GATE D itself
        # still runs, unfiltered, as the real blocking check on the finished
        # draft afterward -- this filter only affects whether soften nukes
        # the sentence preemptively, not whether the scar can reach
        # WordPress.
        _grammar_findings = [f for f in scan_body(cleaned) if f["type"] != "adjacent_connector_pair"]
        if not is_list_line and _grammar_findings:
            report["sentences_deleted"] += 1
            report["grammar_check_deletions"] = report.get("grammar_check_deletions", 0) + 1
            continue
        kept.append(cleaned)
    return " ".join(k for k in kept if k)


def soften(text, vertical, min_residue_words=4, max_appos_words=4):
    report = {"numeric_claims_total": 0, "unsourced_found": 0, "stripped": 0,
              "sentences_deleted": 0, "table_cells_softened": 0,
              "grammar_check_deletions": 0, "case5_forced_deletions": 0}
    masked, originals, official = _mask_links(text)
    report["numeric_claims_total"] = len(_NUM_RE.findall(masked))
    spans = _find_unsourced(masked, originals, vertical)
    report["unsourced_found"] = len(spans)
    if not spans:
        return text, report  # nothing to do -> original text, links untouched

    lines = masked.split("\n")
    starts, off = [], 0
    for ln in lines:
        starts.append(off)
        off += len(ln) + 1
    per_line = {}
    for (s, e, is_attr) in spans:
        li = bisect.bisect_right(starts, s) - 1
        per_line.setdefault(li, []).append((s - starts[li], e - starts[li], is_attr))

    for li, sp in per_line.items():
        if lines[li].lstrip().startswith("|"):
            lines[li] = _soften_table_row(lines[li], sp, report)
        else:
            lines[li] = _soften_prose(lines[li], sp, min_residue_words, report,
                                      official, max_appos_words)
    return _restore_links("\n".join(lines), originals), report


def main():
    ap = argparse.ArgumentParser(description="Couche 2 soften pass (non-blocking).")
    ap.add_argument("--input", required=True, help="article_draft.md (rewritten in place)")
    ap.add_argument("--report", default=None, help="path for soften_report.json")
    ap.add_argument("--market", default="", help="LEVIER C: routes vertical for fact coverage")
    ap.add_argument("--category", default="", help="LEVIER C: routes vertical for fact coverage")
    ap.add_argument("--min-residue-words", type=int, default=4,
                    help="delete a stripped sentence shorter than this (default 4)")
    ap.add_argument("--max-appos-words", type=int, default=4,
                    help="PLAN B: remove a whole em-dash appositive only if its residue "
                         "(number removed) has <= this many content words (default 4)")
    args = ap.parse_args()

    text = Path(args.input).read_text(encoding="utf-8")
    vertical = resolve_gate_vertical(args.market, args.category)
    softened, report = soften(text, vertical, args.min_residue_words, args.max_appos_words)
    Path(args.input).write_text(softened, encoding="utf-8")
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[COUCHE-2 soften] {report}")
    # NON-BLOCKING by design: softening never rejects. Blocking is Couche 3.
    sys.exit(0)


if __name__ == "__main__":
    main()
