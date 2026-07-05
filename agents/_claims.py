"""Single source of truth for the numeric-claim / attribution / URL regexes.

Shared by BOTH the Sprint 10 detection (agents/agent_05_fact_checker.py) and the
Couche 2 soften pass (scripts/soften_claims.py). One definition means detection
and softening can never drift apart: the soften pass must strip exactly what the
detector would flag. Pure regex, no dependencies.
"""
import re

# A "hard" numeric claim: a %, a $ / CAD amount, "N times/x", "N out of N",
# a magnitude count ("45 million"), or a score threshold ("650+"). The last two
# were added after a real run let "approximately 45 million ... credit invisible"
# and "650+ score" survive the soften pass (bare numbers _NUM_RE did not match).
#
# LEVIER C PART 2 (2026-07-05): a bare duration/count -- "N day(s)/week(s)/
# month(s)/year(s)/bureau(s)", including the adjective form ("a 24-month
# extension") and an optional N-M range ("12-24 months"). Deliberately SCOPED to
# a small closed unit whitelist immediately adjacent to the number (optionally
# through "business"/"calendar"/"nationwide", the 3 adjectives our own engraved
# facts actually use -- "2 government business days" has 2 adjectives and is a
# known, accepted miss, safe under-capture not a new risk). This is what makes a
# bare calendar year ("2026"), a law/section number ("22 CFR 62.14", "8 U.S.C.
# 1601"), a street address ("123 Main Street"), a form number ("I-901"), or a
# bare age/score ("under 21", "580") NEVER match: none is followed by one of
# these exact unit words. hours/minutes deliberately EXCLUDED (residue,
# conscious): almost no sourceable .gov fact on credit/immigration content is
# stated in hours/minutes, and adding them would raise false-positive risk for
# no real gain -- add only if a real run shows they actually occur.
_NUM_RE = re.compile(
    r"(?:\d+(?:\.\d+)?\s?%|\$\s?\d[\d,]*(?:\.\d+)?|\bCAD\s?\d[\d,]*|"
    r"\b\d+(?:\.\d+)?\s?(?:times|x)\b|\b\d+\s+out of\s+\d+\b|"
    r"\b\d[\d,]*(?:\.\d+)?\s?(?:million|billion|thousand)\b|"
    r"\b\d+(?:\.\d+)?(?:\s?[–—-]\s?\d+)?\s?(?:percentage\s+points|basis\s+points|points|pts|bps)\b|"
    r"\b\d{3}\s?[–—-]\s?\d{3}\b|"   # 3-digit score range, e.g. "620-680" (NOT 4-digit years or 2-digit month ranges)
    r"\b\d{2,}\+|"
    r"\b\d+(?:\.\d+)?(?:\s?[–—-]\s?\d+(?:\.\d+)?)?[\s-]+(?:(?:business|calendar|nationwide)[\s-]+)?"
    r"(?:days?|weeks?|months?|years?|bureaus?)\b)", re.I)

# A named-source attribution cue (raises severity to "unbacked_attribution").
_ATTR_RE = re.compile(
    r"(?i)\b(?:according to|per|based on|reports?|survey|study|found by|data from|says?)\b|\([12]\d{3}\)")

# An inline URL (used to check for an allow-listed citation near a claim).
_URL_IN = re.compile(r"https?://[^\s\)\]>,;]+")
