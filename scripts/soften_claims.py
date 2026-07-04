"""Couche 2 -- deterministic soften pass (NON-BLOCKING).

Runs after agent_04 and before the fact-check gate. For every UNSOURCED numeric
claim (same predicate as the Sprint 10 detection: a _NUM_RE match with no
allow-listed URL within +-100 chars) it removes the fabricated FIGURE while
keeping the directional clause -- never trusting the writer, exactly like the
Sprint 8 sanitizer. It does NOT reject anything: it rewrites the draft and emits
a report. The blocking decision belongs to Couche 3 (G-Substance), which consumes
that report.

Rules (mechanical, never the LLM):
  - prose: strip the number + its quantifier ("by 20-40% above" -> "above"); for a
    named attribution ("according to X, 15-25% lower") strip the cue + number too.
  - table row (line starts with '|'): replace the whole offending cell with "varies"
    so the table stays well-formed and honest.
  - after a prose strip, if the residual sentence has fewer than --min-residue-words
    words it is deleted (a gutted stat sentence); otherwise the clause is kept.

Sourced numbers, Couche 1 supplied facts (both carry a .gov link) and all markdown
structure are left untouched. The pass is idempotent and a no-op on a clean draft.
"""
import argparse
import bisect
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents._claims import _NUM_RE, _ATTR_RE, _URL_IN  # single source of truth
from agents._sources import _classify_url

_SENT = "\x00"  # sentinel marking a stripped figure inside a prose sentence

# Quantifier words that introduce a figure and should be stripped with it.
_QUANT = re.compile(
    r"(?i)(?:\b(?:by|up to|around|about|roughly|nearly|over|under|approximately|"
    r"between|from|of|below|above|at least|at most|as much as|as little as|"
    r"as low as|as high as)\s+)$")
# A numeric range prefix immediately before the matched figure, e.g. "20-" in "20-40%".
_RANGE_PREFIX = re.compile(r"\d[\d,\.]*\s*[–—-]\s*$")


def _unsourced_spans(text):
    """[(start, end, is_attribution)] for every _NUM_RE match NOT backed by an
    allow-listed URL within +-100 chars. Identical predicate to agent_05."""
    spans = []
    for m in _NUM_RE.finditer(text):
        lo, hi = max(0, m.start() - 100), min(len(text), m.end() + 100)
        window = text[lo:hi]
        if any(_classify_url(u) == "official" for u in _URL_IN.findall(window)):
            continue
        spans.append((m.start(), m.end(), bool(_ATTR_RE.search(window))))
    return spans


def _strip_span(line, s, e, is_attr):
    """Extend the raw figure span (s, e) to also swallow a leading range prefix, a
    leading quantifier word, and -- for attributions -- the 'according to X,' cue."""
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


def _clean(fragment):
    """Tidy whitespace/punctuation left behind by a strip (sentinels removed)."""
    s = fragment.replace(_SENT, "")
    s = re.sub(r"\*\*\s*\*\*", "", s)         # empty bold left by a stripped **30%**
    s = re.sub(r"\(\s*\)", "", s)             # empty parens
    s = re.sub(r"\s+([,.;:%!?\)])", r"\1", s) # space before punctuation / close-paren
    s = re.sub(r"([(–—-])\s+", r"\1", s)
    s = re.sub(r",\s*,", ",", s)              # doubled commas
    s = re.sub(r"\s{2,}", " ", s)             # collapse runs of spaces
    s = re.sub(r"^[\s,;:–—-]+", "", s)        # leading junk
    return s.strip()


def _soften_table_row(line, spans_local, report):
    """Replace each pipe cell that contains an unsourced figure with 'varies'."""
    cells, pos, out = line.split("|"), 0, []
    for idx, cell in enumerate(cells):
        start, end = pos, pos + len(cell)
        pos = end + 1  # account for the '|' separator
        if any(start <= s < end for (s, _e, _a) in spans_local):
            out.append(" varies ")
            report["table_cells_softened"] += 1
        else:
            out.append(cell)
    return "|".join(out)


def _soften_prose(line, spans_local, min_words, report):
    """Strip figures leaving a sentinel, then drop any sentence the strip reduced
    below min_words; keep the clause otherwise. Extended strip-spans are MERGED
    first so overlapping ranges (e.g. "$200-$500") cannot corrupt each other
    (that bug ate letters, e.g. "from" -> "rom")."""
    strips = []
    for (s, e, is_attr) in spans_local:
        strips.append(list(_strip_span(line, s, e, is_attr)))
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


def soften(text, min_residue_words=4):
    report = {"numeric_claims_total": 0, "unsourced_found": 0, "stripped": 0,
              "sentences_deleted": 0, "table_cells_softened": 0}
    report["numeric_claims_total"] = len(_NUM_RE.findall(text))
    spans = _unsourced_spans(text)
    report["unsourced_found"] = len(spans)
    if not spans:
        return text, report

    lines = text.split("\n")
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
            lines[li] = _soften_prose(lines[li], sp, min_residue_words, report)
    return "\n".join(lines), report


def main():
    ap = argparse.ArgumentParser(description="Couche 2 soften pass (non-blocking).")
    ap.add_argument("--input", required=True, help="article_draft.md (rewritten in place)")
    ap.add_argument("--report", default=None, help="path for soften_report.json")
    ap.add_argument("--min-residue-words", type=int, default=4,
                    help="delete a stripped sentence shorter than this (default 4)")
    args = ap.parse_args()

    text = Path(args.input).read_text(encoding="utf-8")
    softened, report = soften(text, args.min_residue_words)
    Path(args.input).write_text(softened, encoding="utf-8")
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[COUCHE-2 soften] {report}")
    # NON-BLOCKING by design: softening never rejects. Blocking is Couche 3.
    sys.exit(0)


if __name__ == "__main__":
    main()
