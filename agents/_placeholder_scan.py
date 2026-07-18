"""Detects generation-pipeline artifacts that leak an unfilled template value
into published prose. Pure regex, no dependencies -- shared by agent_12's
in-scoring hard cap and scripts/placeholder_gate.py's standalone pipeline gate.

Same bug class shipped to production TWICE before this existed:
  - 48754 (2026-07-13): "within the first...", "contract rate plus...",
    "with of Canadian T4 income..." (paraphrased in AUDIT-LOG.md, exact
    article text not preserved) -- scored 100/100, gap noted but never built.
  - 48854 (2026-07-18): four distinct missing-value shapes, exact text
    preserved and used as the test fixtures below --
      1. "your first 60 to on campus" (two connectors back-to-back: "to on")
      2. "USCIS may authorize of Optional Practical Training" (an
         authorization verb directly touching "of" with no quantity between)
      3. "a combined potential authorization window of U.S.-sourced
         employment income" (a duration-noun "window of X" where X is a
         capitalized/hyphenated phrase and no digit appears nearby --
         grammatically valid-LOOKING English, semantically missing "up to 36
         months")
      4. a fully fused sentence+link: "...valid status.uscis.gov/...-for-f-1-
         students)." (dropped "F-1 status (see <a href=\"https://www.")
    plus a broken-Title-Case post title ("Checklist Usa"). Scored 98.8/100.
    This module is the fix, built the same day it was caught the second time.

None of these patterns are semantically "wrong" in a way a grammar checker
would catch -- they're syntactically odd (a preposition where a noun/number
belongs) in ways generic prose rarely produces naturally, which is exactly
why they're worth flagging even at some false-positive risk: a human (or a
downstream retry) reviewing 2-3 flagged snippets per article is far cheaper
than a live USCIS-deadline article missing a number.

NOT claimed to be exhaustive. "within the first..." and "contract rate
plus..." from the 48754 case are not mechanically reproduced here (the
exact original text wasn't preserved to build a real test fixture from) --
a known, documented gap rather than a silently overclaimed one.

`scan_body()` and `scan_title()` are pure functions (str in, findings out) so
they're independently unit-testable without touching the agent framework.
"""
import re
from typing import Dict, List

# ---------------------------------------------------------------------------
# 1. A preposition/connector immediately followed by terminal punctuation --
#    the object (a template value) is missing entirely. "with"/"in"/"as"
#    tried and dropped: too many real false positives in this site's prose
#    ("Registered Retirement Savings Plan (RRSP), for example, ..." reads
#    fine; "for" isn't dangling there because it's not followed by
#    punctuation, but broader connector sets pulled in unrelated noise).
_DANGLING_CONNECTORS = ["of", "to", "by", "for", "within", "up to", "at least", "plus"]
_DANGLING_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in _DANGLING_CONNECTORS) + r")\s+[.,;:)]",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# 2. Two bare prepositions/connectors back-to-back with nothing but
#    whitespace between them ("to on", "to of") -- natural English
#    essentially never stacks two bare prepositions like this; the fact that
#    it happened means a value was supposed to sit between them.
#
#    A first version tried a full cross-product of a broad connector list
#    (of/to/by/for/within/with/in/on/at/from) and, tested against 15 real
#    published articles, hit a wall of false positives from perfectly
#    ordinary English: "at least" ("for at least the past two years"),
#    "from within" ("verified digital identity confirmation from within
#    Canadian jurisdiction"), and compound adjectives like "on-time"/
#    "at-fault" ("years of on-time payments", "in at-fault states"). Narrowed
#    to a curated allowlist of pairs actually observed in confirmed template
#    bugs (48854's "to on", 48733's "to of") rather than a generative
#    cross-product -- precision over recall, since this is a hard-blocking
#    gate and a false positive halts autonomous publishing.
_KNOWN_BAD_ADJACENT_PAIRS = ["to on", "to of", "with of", "of to", "for to"]
_ADJACENT_PAIR_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in _KNOWN_BAD_ADJACENT_PAIRS) + r")\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# 3. An authorization/permission verb directly touching "of"/"to" with no
#    quantity between them -- "may authorize of X" instead of "may authorize
#    up to N months of X".
_PERMISSION_VERBS = ["authorize", "authorizes", "allow", "allows", "permit",
                      "permits", "grant", "grants", "provide", "provides"]
_VERB_CONNECTOR_PATTERN = re.compile(
    r"\b(" + "|".join(_PERMISSION_VERBS) + r")\s+(of|to)\s+([A-Z][a-zA-Z\-]*)",
)

# ---------------------------------------------------------------------------
# 4. A duration-related noun followed by "of" then a capitalized/hyphenated
#    phrase with no digit anywhere in the next few words -- "authorization
#    window of U.S.-sourced employment income" instead of "...window of up
#    to 36 months of U.S.-sourced...". Deliberately requires the capitalized
#    follow-on word (lowercase, e.g. "a window of opportunity", is common,
#    valid English and must not be flagged).
_DURATION_NOUNS = ["window", "period", "duration", "extension", "authorization"]
_DURATION_NOUN_PATTERN = re.compile(
    r"\b(" + "|".join(_DURATION_NOUNS) + r")\s+of\s+([A-Z][a-zA-Z.\-]*)",
)
# Nationality/demonym adjectives are ordinary capitalized words in this
# context ("the period of Canadian residency") -- not evidence of a missing
# quantity. Real false positive caught testing against 15 live articles.
_DEMONYM_ADJECTIVES = {
    "canadian", "american", "u.s.", "mexican", "british", "indian", "chinese",
    "filipino", "nigerian", "brazilian",
}


def _has_nearby_digit(text: str, start: int, lookback: int = 40) -> bool:
    return bool(re.search(r"\d", text[max(0, start - lookback):start]))


def _find_dangling_connectors(text: str) -> List[Dict]:
    return [{
        "type": "dangling_connector",
        "match": m.group(0).strip(),
        "context": text[max(0, m.start() - 60):m.end() + 20].strip(),
        "position": m.start(),
    } for m in _DANGLING_PATTERN.finditer(text)]


def _find_adjacent_connector_pairs(text: str) -> List[Dict]:
    return [{
        "type": "adjacent_connector_pair",
        "match": m.group(0),
        "context": text[max(0, m.start() - 60):m.end() + 20].strip(),
        "position": m.start(),
    } for m in _ADJACENT_PAIR_PATTERN.finditer(text)]


def _find_verb_connector_capitalized(text: str) -> List[Dict]:
    findings = []
    for m in _VERB_CONNECTOR_PATTERN.finditer(text):
        if _has_nearby_digit(text, m.start(), lookback=5):
            continue  # e.g. "authorize up to 12 months of X" already has a value
        findings.append({
            "type": "missing_quantity_before_of",
            "match": m.group(0),
            "context": text[max(0, m.start() - 20):m.end() + 40].strip(),
            "position": m.start(),
        })
    return findings


def _find_duration_noun_missing_quantity(text: str) -> List[Dict]:
    findings = []
    for m in _DURATION_NOUN_PATTERN.finditer(text):
        if _has_nearby_digit(text, m.start(), lookback=40):
            continue
        if m.group(2).lower() in _DEMONYM_ADJECTIVES:
            continue
        findings.append({
            "type": "missing_quantity_before_of",
            "match": m.group(0),
            "context": text[max(0, m.start() - 20):m.end() + 40].strip(),
            "position": m.start(),
        })
    return findings


# ---------------------------------------------------------------------------
# 5. A raw bare domain (no http/https, no markdown/HTML link syntax
#    immediately before it) directly followed by a URL path -- the
#    fingerprint of an f-string that dropped its own "(see <a href=\"https://
#    www." prefix and fused the rest of the anchor onto the sentence.
_FUSED_LINK_PATTERN = re.compile(
    r"\b[a-z][a-z.\-]*\.(?:gov|com|org|edu|net)/[a-zA-Z0-9/_\-]+\)?[.,]",
    re.IGNORECASE,
)


def _find_fused_link_sentences(text: str) -> List[Dict]:
    findings = []
    for m in _FUSED_LINK_PATTERN.finditer(text):
        prefix = text[max(0, m.start() - 10):m.start()]
        if "http" in prefix or "](" in prefix or "href=" in prefix:
            continue
        findings.append({
            "type": "fused_link_sentence",
            "match": m.group(0),
            "context": text[max(0, m.start() - 60):m.end() + 20].strip(),
            "position": m.start(),
        })
    return findings


# ---------------------------------------------------------------------------
# 6. An <img> tag with a missing/empty src attribute.
_IMG_TAG_PATTERN = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_SRC_ATTR_PATTERN = re.compile(r"""src\s*=\s*["']([^"']*)["']""", re.IGNORECASE)


def _find_empty_image_src(text: str) -> List[Dict]:
    findings = []
    for m in _IMG_TAG_PATTERN.finditer(text):
        tag = m.group(0)
        src_match = _SRC_ATTR_PATTERN.search(tag)
        if not src_match or not src_match.group(1).strip():
            findings.append({
                "type": "empty_image_src",
                "match": tag[:150],
                "context": tag[:150],
                "position": m.start(),
            })
    return findings


# ---------------------------------------------------------------------------
# 7. A known acronym rendered in broken Title Case (e.g. "Usa" instead of
#    "USA"). Small, closed allowlist -- deliberately NOT a general all-caps
#    heuristic, which would false-positive on ordinary emphasis words.
_KNOWN_ACRONYMS = {
    "usa", "ssn", "itin", "opt", "sevis", "dhs", "cra", "irs", "cpt", "dso",
    "fica", "tfsa", "rrsp", "ofx", "faq", "eeat", "seo", "gst", "hst", "sin",
    "cpp", "ei", "uscis", "ice", "stem",
}


def scan_title(title: str) -> List[Dict]:
    """Flag a known acronym rendered in broken Title Case within a post title."""
    findings = []
    for w in re.findall(r"[A-Za-z']+", title):
        lw = w.lower()
        if lw in _KNOWN_ACRONYMS and w != w.upper() and w[:1].isupper():
            findings.append({
                "type": "broken_title_case_acronym",
                "match": w,
                "context": title,
                "position": title.find(w),
            })
    return findings


def scan_body(text: str) -> List[Dict]:
    """Run every body-content detector and return all findings, sorted by
    position in the text."""
    findings = []
    findings += _find_dangling_connectors(text)
    findings += _find_adjacent_connector_pairs(text)
    findings += _find_verb_connector_capitalized(text)
    findings += _find_duration_noun_missing_quantity(text)
    findings += _find_fused_link_sentences(text)
    findings += _find_empty_image_src(text)
    return sorted(findings, key=lambda f: f["position"])


def scan(text: str, title: str = "") -> List[Dict]:
    """Convenience wrapper: scan_body(text) + scan_title(title) combined."""
    findings = scan_body(text)
    if title:
        findings += scan_title(title)
    return findings
