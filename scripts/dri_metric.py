#!/usr/bin/env python3
"""
NEXUS-14 Sprint 2 -- Diffuse Repetition Index (DRI).

Why this metric exists: G3 (cosine) only catches BLOCK overlap. The real defect
on haiku-written articles is DIFFUSE repetition -- the same content trigram
("financial consumer agency", "business days") sprinkled across many sections.
Cosine stays low yet the article feels repetitive. DRI measures exactly that.

DEFINITION (deterministic, LLM-free):
  - Tokenize each body section into content words (lowercased, stopwords and the
    inevitable DOMAIN vocabulary removed, so we don't penalise the topic itself).
  - Build content TRIGRAMS per section. A trigram is counted ONCE per section
    (presence, not frequency) so a single dense section can't inflate the score.
  - For each distinct trigram, count in how many SECTIONS it appears (df).
  - A trigram is "diffuse" when df >= MIN_SECTIONS (default 3): it shows up in at
    least 3 different sections, i.e. it is being re-derived rather than stated once.
  - DRI = number of diffuse trigrams.
  - excess_dispersion = sum(df - (MIN_SECTIONS - 1)) over diffuse trigrams -- a
    secondary magnitude measure (how far past the threshold the spread goes).

Lower is better. Sprint 2 success = a clear DRI drop on the Sonnet + cumulative
context writer versus the haiku baseline (article_2 DRI=32, article_3 DRI=18).
"""
import argparse
import json
import re
import sys
from collections import defaultdict

MIN_SECTIONS = 3
NGRAM = 3

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "for", "on", "with",
    "as", "by", "is", "are", "be", "this", "that", "you", "your", "it", "at",
    "from", "will", "can", "their", "they", "we", "our", "have", "has", "was",
    "were", "not", "if", "so", "do", "does", "such", "these", "those", "than",
    "then", "when", "which", "who", "what", "how", "where", "while", "also",
    "may", "must", "should", "would", "could", "into", "out", "up", "no", "yes",
    "more", "most", "some", "any", "all", "each", "other", "one", "two", "first",
}
# Inevitable business vocabulary -- excluded so the topic itself is not penalised.
_DOMAIN = {
    "bank", "banks", "banking", "account", "accounts", "newcomer", "newcomers",
    "immigrant", "immigrants", "canada", "canadian", "usa", "us", "credit",
    "money", "financial", "finance", "moneyabroadguide",
}


# SPRINT 2 (metric): structural blocks that are SUPPOSED to appear once (disclaimer, author box)
# are excluded from the repetition metric. This measures editorial prose, NOT boilerplate.
# NOTE: this only affects MEASUREMENT. The writer itself must still emit them exactly once
# (enforced at the source in agent_04); filtering here never licenses duplicated boilerplate.
_BOILERPLATE_HEADINGS = (
    "disclaimer", "about the author", "affiliate disclosure", "author box",
    "legal disclaimer", "compliance disclaimer",
)
_URL_RE = re.compile(r"https?://\S+|www\.\S+|\bmoneyabroadguide\.com\S*", re.IGNORECASE)


def _split_sections(markdown):
    md = re.sub(r"^---\n.*?\n---\n", "", markdown, count=1, flags=re.DOTALL)
    parts = re.split(r"(?m)^##\s+", md)
    sections = []
    if parts and len(parts[0].split()) > 30:
        sections.append(parts[0].strip())
    for p in parts[1:]:
        head, _, rest = p.partition("\n")
        # Skip blocks that are supposed to appear once (disclaimer, author box):
        # measuring their repetition is meaningless. Source enforces single emission.
        if head.strip().lower().lstrip("0123456789. )").strip() in _BOILERPLATE_HEADINGS:
            continue
        sections.append(rest.strip())
    return sections


def _content_tokens(text):
    text = _URL_RE.sub(" ", text)  # drop URLs/CTA links: not editorial prose
    return [w for w in _WORD_RE.findall(text.lower())
            if w not in _STOP and w not in _DOMAIN and len(w) > 2]


def _trigrams(tokens, n=NGRAM):
    return {" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def compute_dri(markdown, min_sections=MIN_SECTIONS, ngram=NGRAM):
    sections = _split_sections(markdown)
    df = defaultdict(int)            # trigram -> number of distinct sections
    for sec in sections:
        toks = _content_tokens(sec)
        for tg in _trigrams(toks, ngram):
            df[tg] += 1
    diffuse = {tg: c for tg, c in df.items() if c >= min_sections}
    dri = len(diffuse)
    excess = sum(c - (min_sections - 1) for c in diffuse.values())
    top = sorted(diffuse.items(), key=lambda kv: kv[1], reverse=True)[:10]
    return {
        "metric": "diffuse_repetition_index",
        "ngram": ngram,
        "min_sections": min_sections,
        "section_count": len(sections),
        "dri": dri,
        "excess_dispersion": excess,
        "top_diffuse_trigrams": [{"trigram": t, "sections": c} for t, c in top],
    }


# SPRINT 2 (b): UNFILTERED diagnostic. Proves the SOURCE is fixed (boilerplate confined to
# one block), not merely hidden by the metric filter. Counts, over ALL sections, how many
# distinct sections contain the disclaimer and the author box. Target after the source fix: 1 each.
_DISCLAIMER_MARKERS = re.compile(
    r"not\s+financial\s+advice|compliance\s+disclaimer|legal\s+disclaimer"
    r"|consult\s+a?\s*licensed|this\s+(?:article|content)\s+is\s+for\s+informational",
    re.IGNORECASE)
_AUTHORBOX_MARKERS = re.compile(
    r"about\s+the\s+author|author\s+box|talal\s+eddaouahiri|founder\s+of\s+moneyabroadguide",
    re.IGNORECASE)

def boilerplate_dispersion(markdown):
    md = re.sub(r"^---\n.*?\n---\n", "", markdown, count=1, flags=re.DOTALL)
    parts = re.split(r"(?m)^##\s+", md)
    blocks = []
    if parts:
        blocks.append(parts[0])
        blocks.extend(parts[1:])
    disclaimer = sum(1 for b in blocks if _DISCLAIMER_MARKERS.search(b))
    authorbox = sum(1 for b in blocks if _AUTHORBOX_MARKERS.search(b))
    return {"disclaimer_sections": disclaimer, "authorbox_sections": authorbox}


def main():
    ap = argparse.ArgumentParser(description="Diffuse Repetition Index (DRI)")
    ap.add_argument("--input", required=True, help="article_draft.md")
    ap.add_argument("--output", required=True, help="dri_report.json")
    ap.add_argument("--min-sections", type=int, default=MIN_SECTIONS)
    ap.add_argument("--ngram", type=int, default=NGRAM)
    args = ap.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            markdown = f.read()
    except OSError as e:
        print("DRI ERROR: cannot read input: %s" % e, file=sys.stderr)
        sys.exit(1)

    result = compute_dri(markdown, args.min_sections, args.ngram)

    import os
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("DRI = %d (excess dispersion = %d) over %d sections"
          % (result["dri"], result["excess_dispersion"], result["section_count"]))
    _disp = boilerplate_dispersion(markdown)
    print("BOILERPLATE DISPERSION: disclaimer in %d section(s), author-box in %d section(s)"
          % (_disp["disclaimer_sections"], _disp["authorbox_sections"]))
    # CI VISIBILITY: print the most-dispersed trigrams so DRI detail is readable in logs (no artifact needed).
    _top = result["top_diffuse_trigrams"]
    if _top:
        print("DRI DETAIL: top %d diffuse trigrams (trigram | # sections):" % min(15, len(_top)))
        for _t in _top[:15]:
            print("  - \"%s\" in %d sections" % (_t["trigram"], _t["sections"]))
    # DRI is a REPORTING metric, never blocking on its own. Always exit 0.
    sys.exit(0)


if __name__ == "__main__":
    main()
