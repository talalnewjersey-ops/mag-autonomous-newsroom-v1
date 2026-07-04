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

Rules (mechanical, never the LLM):
  - prose: strip the number + its quantifier ("by 20-40% above" -> "above"); for a
    named attribution ("according to X, 15-25% lower") strip the cue + number too.
  - table row (line starts with '|'): replace the whole offending cell with "varies".
  - after a prose strip, if the residual sentence has fewer than --min-residue-words
    words it is deleted; otherwise the clause is kept.
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

_SENT = "\x00"  # sentinel marking a stripped figure inside a prose sentence

# ---- link masking (point 3) ----
_MASK_OPEN, _MASK_CLOSE = "\x0e", "\x0f"
_LINK_RE = re.compile(r"\[[^\]]*\]\([^)]+\)|https?://[^\s\)\]>,;]+")  # markdown link OR bare URL
_MASK_IN = re.compile(_MASK_OPEN + r"(\d+)" + _MASK_CLOSE)

# Quantifier words that introduce a figure and should be stripped with it.
_QUANT = re.compile(
    r"(?i)(?:\b(?:by|up to|around|about|roughly|nearly|over|under|approximately|"
    r"between|from|of|below|above|at least|at most|as much as|as little as|"
    r"as low as|as high as)\s+)$")
# A numeric range prefix immediately before the matched figure, e.g. "20-" in "20-40%".
_RANGE_PREFIX = re.compile(r"\d[\d,\.]*\s*[–—-]\s*$")
# PLAN B (context-aware scaffold): a trailing unit token glued to the figure, e.g. "/month".
_UNIT_RE = re.compile(r"/(?:months?|years?|weeks?|days?|mo|yr|hrs?|hours?)\b", re.I)
_DASH = "—–"  # em-dash, en-dash


def _mask_links(text):
    """Replace every markdown link / bare URL with an atomic indexed placeholder.
    Returns (masked_text, originals, official_indices)."""
    originals, official = [], set()
    def repl(m):
        i = len(originals)
        s = m.group(0)
        um = re.search(r"\(([^)]+)\)\s*$", s)   # markdown link -> url inside (...)
        url = um.group(1) if um else s          # bare URL -> itself
        if _classify_url(url) == "official":
            official.add(i)
        originals.append(s)
        return _MASK_OPEN + str(i) + _MASK_CLOSE
    return _LINK_RE.sub(repl, text), originals, official


def _restore_links(text, originals):
    return _MASK_IN.sub(lambda m: originals[int(m.group(1))], text)


def _find_unsourced(masked, official):
    """[(start, end, is_attribution)] for every _NUM_RE match in MASKED text with no
    official-link placeholder within +-100 chars. Attribution cues inside URLs can no
    longer fire (URLs are placeholders)."""
    spans = []
    for m in _NUM_RE.finditer(masked):
        lo, hi = max(0, m.start() - 100), min(len(masked), m.end() + 100)
        window = masked[lo:hi]
        if any(int(g) in official for g in _MASK_IN.findall(window)):
            continue  # sourced: an allow-listed link sits nearby
        spans.append((m.start(), m.end(), bool(_ATTR_RE.search(window))))
    return spans


def _unsourced_spans(text):
    """Public: unsourced numeric spans (masks links internally). Used by Couche 3's
    residual-integrity check (count only)."""
    masked, _originals, official = _mask_links(text)
    return _find_unsourced(masked, official)


def _strip_span(line, s, e, is_attr):
    """Extend the raw figure span (s, e) to also swallow a leading range prefix, a
    leading quantifier word, and -- for attributions -- the 'according to X,' cue.
    Operates on MASKED text, so it can never cross into a URL."""
    ss = s
    m = _RANGE_PREFIX.search(line[:ss])
    if m:
        ss = m.start()
    m = _QUANT.search(line[:ss])
    if m:
        ss = m.start()
    if is_attr:
        lo = max(0, s - 100)
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
    Operates on MASKED text (URLs are placeholders)."""
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
            return ss, ee                     # parenthetical is self-contained -> done
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
            return dl, dr
    # CASE 2 -- enclosing bold ** ... **.
    bl, br = line.rfind("**", 0, ss), line.find("**", ee)
    if bl != -1 and br != -1 and "**" not in line[bl + 2:ss] and "**" not in line[ee:br]:
        if not _sourced_inside(line[bl + 2:br], official):
            if _content_word_count(line[bl + 2:ss] + " " + line[ee:br]) == 0:
                ss, ee = bl, br + 2           # 2a: bold holds only the figure -> remove it all
            else:
                while ss > 0 and line[ss - 1] == " ":   # 2b: keep the label -> **label** tight
                    ss -= 1
    return ss, ee


def _clean(fragment):
    """Tidy whitespace/punctuation left behind by a strip (sentinels removed)."""
    s = fragment.replace(_SENT, "")
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


def _soften_table_row(line, spans_local, report):
    """Replace each pipe cell that contains an unsourced figure with 'varies'."""
    cells, pos, out = line.split("|"), 0, []
    for cell in cells:
        start, end = pos, pos + len(cell)
        pos = end + 1  # account for the '|' separator
        if any(start <= s < end for (s, _e, _a) in spans_local):
            out.append(" varies ")
            report["table_cells_softened"] += 1
        else:
            out.append(cell)
    return "|".join(out)


def _soften_prose(line, spans_local, min_words, report, official=frozenset(), max_appos_words=4):
    """Strip figures leaving a sentinel, then drop any sentence the strip reduced
    below min_words; keep the clause otherwise. Extended strip-spans are MERGED
    first so overlapping ranges (e.g. "$200-$500") cannot corrupt each other.
    PLAN B: each span is grown to swallow its immediate delimited scaffold so no
    scar (dangling '(', '/month', '**', '— —') is ever created."""
    strips = []
    for (s, e, is_attr) in spans_local:
        ss, ee = _strip_span(line, s, e, is_attr)
        ss, ee = _scaffold_span(line, ss, ee, official, max_appos_words)
        strips.append([ss, ee])
        report["stripped"] += 1
    strips.sort()
    merged = []
    for st in strips:
        if merged and st[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], st[1])
        else:
            merged.append(st)
    for ss, ee in sorted(merged, reverse=True):
        line = line[:ss] + _SENT + line[ee:]
    kept = []
    for sentence in re.split(r"(?<=[.!?])\s+", line):
        if _SENT not in sentence:
            kept.append(sentence)
            continue
        cleaned = _clean(sentence)
        if len(cleaned.split()) < min_words:
            report["sentences_deleted"] += 1  # gutted stat sentence -> drop it
            continue
        kept.append(cleaned)
    return " ".join(k for k in kept if k)


def soften(text, min_residue_words=4, max_appos_words=4):
    report = {"numeric_claims_total": 0, "unsourced_found": 0, "stripped": 0,
              "sentences_deleted": 0, "table_cells_softened": 0}
    masked, originals, official = _mask_links(text)
    report["numeric_claims_total"] = len(_NUM_RE.findall(masked))
    spans = _find_unsourced(masked, official)
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
    ap.add_argument("--min-residue-words", type=int, default=4,
                    help="delete a stripped sentence shorter than this (default 4)")
    ap.add_argument("--max-appos-words", type=int, default=4,
                    help="PLAN B: remove a whole em-dash appositive only if its residue "
                         "(number removed) has <= this many content words (default 4)")
    args = ap.parse_args()

    text = Path(args.input).read_text(encoding="utf-8")
    softened, report = soften(text, args.min_residue_words, args.max_appos_words)
    Path(args.input).write_text(softened, encoding="utf-8")
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[COUCHE-2 soften] {report}")
    # NON-BLOCKING by design: softening never rejects. Blocking is Couche 3.
    sys.exit(0)


if __name__ == "__main__":
    main()
