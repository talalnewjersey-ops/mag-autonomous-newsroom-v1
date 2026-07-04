"""Prose-polish pass -- DELETION-ONLY, deterministic (no LLM, no rewrite, no refill).

Couche 2 strips an unsourced number but leaves the grammatical SCAFFOLD that held
it (prepositions, "(of your FICO score)", "/month", bold), producing scars. This
pass DELETES the orphaned scaffold; it NEVER inserts, rewrites or refills -- so a
removed number can never reappear (repair != reinvention). If a sentence is still
broken after cleanup, the WHOLE sentence is dropped rather than left as a stump.

Runs AFTER Couche 2 soften, BEFORE Couche 3 G-Substance (separate from detection).

HARD INVARIANT (tested): the output is deletion-only -> every digit in the output
was already in the input. No digit absent from the input can appear.
"""
import re

# em-dash appositive that CONTAINS a scar residue -> drop the whole appositive.
_APPOS_SCAR = re.compile(
    r"\s*[—–]\s*[^—–.]*?(?:\bfor of\b|\bat\s*\*\*|\bcontributes of\b|"
    r"\baccounting for of\b|\*\*\s*of\b)[^—–.]*?(?:\s*[—–]|(?=\s*\.|$))", re.I)
# parenthetical opening on a stripped-number preposition and containing NO digit.
_PAREN_SCAR = re.compile(r"\s*\((?:of|at|below|above|by)\b[^)0-9]*\)", re.I)
# empty / half bold left by a stripped **X%**
_BOLD_SCAR = (re.compile(r"\*\*\s*of\b[^*]*\*\*", re.I), re.compile(r"\*\*\s*\*\*"))
# residual "hard" scars that cannot be cleanly repaired -> DELETE the sentence.
_HARD_SCAR = re.compile(
    r"\bthat\)|\bat\s*/|\b(?:for|contributes|accounting for)\s+of\b|\*\*\s+of\b", re.I)

# PART 2 -- minimal dangle filet. LAST RESORT, only for a stripped $/APR that Couche 1
# cannot supply: the strip can glue a verb to a preposition it never takes ("represents
# of", "drives of", "ranging to"). NARROW, curated list -- NOT a catch-all. A recurring
# class must be prevented by Couche 1 (supply the real fact), never by widening this.
_DANGLE = re.compile(
    r"\b(?:represents?|comprises?|constitutes?|drives?|averages?|"
    r"accounts?\s+for|makes?\s+up)\s+of\b"
    r"|\baveraging\s+(?:of|on)\b"
    r"|\branging\s+to\b", re.I)
# Only a ';' reliably marks an INDEPENDENT clause we can drop without leaving a stump.
# (A comma can separate a subordinate opener -- "According to X, <clause>" -- so dropping
# a comma segment can strand "According to X" as a stump/run-on; an em-dash can sit
# mid-main-clause too.) When the dangle is not ';'-isolable, the caller drops the WHOLE
# sentence -- never a stump. Cost: a dangle inside a rich sentence loses that sentence;
# Couche 1 + the anti-fabrication prompt make that rare (this filet is a last resort).
_CLAUSE_SPLIT = re.compile(r"(\s*;\s*)")

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
# An abbreviation ("U.S.", "e.g.", "Inc.") ends in a '.' that is NOT a sentence end.
# We split on _SENT_SPLIT then re-merge any fragment whose predecessor ended in one,
# so a sentence is never cut mid-abbreviation (which would strand "...of U.S." stumps).
_ABBR_END = re.compile(r"(?:(?:\b[A-Za-z]\.){2,}|\b(?:e\.g|i\.e|Inc|Corp|Co|vs|etc|no|approx|Ph\.D|U\.S)\.)\s*$", re.I)


def _split_sentences(text):
    frags, out = _SENT_SPLIT.split(text), []
    for f in frags:
        if out and _ABBR_END.search(out[-1]):
            out[-1] = out[-1] + " " + f
        else:
            out.append(f)
    return out


def _cleanup(s):
    s = _APPOS_SCAR.sub(" ", s)   # space, so the flanking words never get joined
    s = _PAREN_SCAR.sub("", s)
    for rx in _BOLD_SCAR:
        s = rx.sub("", s)
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def _content_words(s):
    return re.findall(r"[A-Za-z][A-Za-z'-]+", re.sub(r"\*\*|__", "", s))


def _drop_dangling(sent):
    """Deletion-only: split the sentence on ; / em-dash boundaries and drop ONLY the
    clause that holds the dangle, keeping the rest. Returns (result, still_dangling).
    If the dangle cannot be isolated to a clause, `still_dangling` is True and the
    caller drops the whole sentence."""
    parts = _CLAUSE_SPLIT.split(sent)
    segs, seps = parts[0::2], parts[1::2]
    keep = [i for i, s in enumerate(segs) if not _DANGLE.search(s)]
    if not keep:
        return "", True
    out = segs[keep[0]]
    for j in keep[1:]:
        out += seps[j - 1] + segs[j]          # reconnect kept clauses with their separator
    out = re.sub(r"\s{2,}", " ", out.strip(" ;,—–"))
    return out, bool(_DANGLE.search(out))


def polish(text, min_words=4):
    report = {"sentences_deleted": 0, "sentences_cleaned": 0, "dangles_pruned": 0}
    out = []
    for line in text.split("\n"):
        st = line.lstrip()
        if not st or st[0] in "#|>":          # headings / tables / blockquotes pass through
            out.append(line)
            continue
        kept = []
        for sent in _split_sentences(line):    # abbreviation-aware -> never cuts "U.S." mid-word
            if not sent.strip():
                continue
            cleaned = _cleanup(sent)           # try to remove orphaned scaffold FIRST
            if _HARD_SCAR.search(cleaned):     # a scar SURVIVED cleanup -> unrepairable -> drop
                report["sentences_deleted"] += 1
                continue
            if _DANGLE.search(cleaned):        # PART 2: prune only the dangling clause (deletion-only)
                pruned, still = _drop_dangling(cleaned)
                report["dangles_pruned"] += 1
                if still or len(_content_words(pruned)) < min_words:
                    report["sentences_deleted"] += 1   # dangle not isolable / stump -> drop sentence
                    continue
                kept.append(pruned)
                continue
            if cleaned == sent:
                kept.append(sent)              # untouched (incl. legit short ones) -> keep as-is
                continue
            report["sentences_cleaned"] += 1
            if len(_content_words(cleaned)) < min_words:
                report["sentences_deleted"] += 1  # cleanup reduced it to a stump -> drop it
                continue
            kept.append(cleaned)
        out.append(" ".join(kept))
    return "\n".join(out), report


def main():
    import argparse
    import json
    import sys
    from pathlib import Path
    ap = argparse.ArgumentParser(description="Prose-polish pass (deletion-only, non-blocking).")
    ap.add_argument("--input", required=True, help="article_draft.md (rewritten in place)")
    ap.add_argument("--report", default=None, help="path for polish_report.json")
    ap.add_argument("--min-words", type=int, default=4)
    args = ap.parse_args()
    text = Path(args.input).read_text(encoding="utf-8")
    polished, report = polish(text, args.min_words)
    Path(args.input).write_text(polished, encoding="utf-8")
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[POLISH] {report}")
    sys.exit(0)  # NON-BLOCKING: polish never rejects


if __name__ == "__main__":
    main()
