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
#
_DANGLING_CONNECTORS = ["of", "to", "by", "for", "within", "up to", "at least", "plus"]
#
# "exceeding"/"totaling"/"averaging"/"reaching" added 2026-07-23 (post 48931
# dry-run, "APRs exceeding, according to the CFPB." -- a number stripped by
# scripts/soften_claims.py's unsourced-claim removal, whose backward-only
# _QUANT list didn't include these verb-form quantifiers -- since fixed
# there too). Kept in a SEPARATE list, not merged into _DANGLING_CONNECTORS:
# a first attempt widened the shared pattern to \s* (matching a scar glued
# directly to punctuation with no space) for ALL 12 words and, tested
# against a fresh live batch (2026-07-23, workflow run 30013499548), that
# broke on ordinary preposition-stranding English -- "the license type you
# qualify for.", "landlords will look for.", "which products you apply
# for." are all grammatically CORRECT sentences ending in a bare
# preposition (a relative clause with an implied "that/which"), and none of
# them had a leading space before the period either. Prepositions strand at
# a clause's end constantly in natural English; verb-form quantifiers like
# "exceeding"/"totaling" essentially never do (there's no equivalent "what
# was it exceeding." construction) -- so \s* is safe ONLY for the verb
# list, not the preposition list, which keeps requiring \s+ (an actual
# leftover space) exactly as originally designed.
_DANGLING_VERB_QUANTIFIERS = ["exceeding", "totaling", "averaging", "reaching"]
#
# em-dash/en-dash (—/–) added to BOTH punctuation classes 2026-07-24 (post
# 48982, real batch after #93/#94/#95: "will have three tradelines reporting
# within —significantly accelerating eligibility" -- soften_claims.py uses
# an em-dash appositive as scaffolding constantly, see scripts/soften_
# claims.py's own CASE-4 docstring, so a connector left dangling right
# before one is exactly as diagnostic as before a comma/period. Plain ASCII
# "-" deliberately NOT added: this site's finance prose uses a bare hyphen
# as a negative-number sign ("by -5% year over year" after a rate drop),
# and "by -" would false-positive on that -- no real bug has needed it, so
# it's left out rather than guessed at.
_DANGLING_PATTERN_LOOSE_SPACE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in _DANGLING_CONNECTORS) + r")\s+[.,;:)—–]",
    re.IGNORECASE,
)
_DANGLING_PATTERN_TIGHT_SPACE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in _DANGLING_VERB_QUANTIFIERS) + r")\s*[.,;:)—–]",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# 1b. Sentence-initial "After" immediately followed by a comma/period with
#     nothing between -- "After, that single account already gives..."
#     (real bug, post 48982, 2026-07-24: soften_claims.py stripped a bare
#     duration -- "After 6 months, that single account..." -- with no
#     quantifier word for _QUANT to swallow, since "After" at a sentence's
#     own start isn't one).
#
#     Deliberately NOT folded into _DANGLING_CONNECTORS/_DANGLING_VERB_
#     QUANTIFIERS: "after" strands at a CLAUSE's end constantly in natural
#     English ("I'll deal with it after."), the same reason the original 8
#     prepositions couldn't take \s* -- but a sentence-initial "After" is a
#     different grammatical position (introducing a new clause, not ending
#     one) where a bare comma/period directly after it is not a natural
#     English construction either way. Restricting to sentence-initial
#     position (start of text, or right after a sentence-ending [.!?] and
#     whitespace) keeps this narrow instead of flagging every mid-sentence
#     "after," which the confirmed bug never actually needed.
_SENTENCE_INITIAL_AFTER_PATTERN = re.compile(
    r"(?:\A|(?<=[.!?])\s+)After\s*[.,]"
)

# ---------------------------------------------------------------------------
# 2. Two bare prepositions/connectors back-to-back with nothing but
#    whitespace between them ("to on", "to of") -- natural English
#    essentially never stacks two bare prepositions like this; the fact that
#    it happened means a value was supposed to sit between them.
#
#    GENERIC as of 2026-07-24 (post 48990: "with in a Canadian chequing
#    account", "secure their first independent rental within of arrival" --
#    two more pairs not on the old enumerated list, and a third would
#    obviously follow the same pattern eventually). Originally this was a
#    curated list of specific bad pairs ("to on", "to of", ...), grown one
#    real bug at a time -- reactive and, per this session's own review,
#    guaranteed to keep missing the next pair nobody had seen yet.
#
#    A first version of the ORIGINAL detector tried a full cross-product of
#    a broad connector list (of/to/by/for/within/with/in/on/at/from) and,
#    tested against 15 real published articles, hit false positives from
#    ordinary English: "at least" ("for at least the past two years"),
#    "from within" ("verified digital identity confirmation from within
#    Canadian jurisdiction"), and compound adjectives like "on-time"/
#    "at-fault" ("years of on-time payments", "in at-fault states") -- the
#    on-time/at-fault case specifically because \b matches right before the
#    hyphen, so "of on-time" looked like "of" + bare "on" without the
#    negative lookahead below.
#
#    This version keeps the same connector word set that caused those false
#    positives, but fixes both root causes instead of retreating to
#    enumeration: (1) an explicit ALLOWLIST of the specific legitimate
#    2-word sequences already found in real content ("from within", "up
#    to"), checked before flagging a match, and (2) a negative lookahead
#    blocking a hyphenated compound's first half from matching as a bare
#    connector ("on-time" can never trigger via "on"). Re-validated against
#    the same false-positive fixtures this list was originally narrowed to
#    avoid, plus the full corpus stress-test (2026-07-24) -- see
#    FALSE_POSITIVE_FIXTURES in tests/test_placeholder_gate.py.
_ADJACENT_CONNECTOR_WORDS = ["of", "to", "by", "for", "within", "with", "in", "from", "at", "on", "plus"]
#    "for on" added 2026-07-24: real false positive found stress-testing
#    against post 48982's own FAQ heading, "What credit utilization rate
#    should I aim for on my first U.S. credit card?" -- "aim for" is a
#    phrasal verb that can take any trailing prepositional phrase ("aim for
#    ON/IN/AT/DURING X"), so "for" immediately followed by "on" is not on
#    its own evidence of a dropped word the way the other pairs are.
_ADJACENT_PAIR_ALLOWLIST = {"from within", "up to", "on to", "in to", "for on"}
_ADJACENT_PAIR_PATTERN = re.compile(
    r"\b(" + "|".join(_ADJACENT_CONNECTOR_WORDS) + r")\s+("
    + "|".join(_ADJACENT_CONNECTOR_WORDS) + r")\b(?!-)",
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
# 3b. "generates"/"produces" directly touching "of"/"to" -- added 2026-07-23
#     (post 48931/article_2: "a credit builder loan generates of on-time
#     payment history", scripts/soften_claims.py stripped a bare duration
#     number -- e.g. "generates 6 months of X" -- with no preceding
#     quantifier word to swallow backward, since "generates" isn't one).
#
#     Deliberately its OWN small list, NOT folded into _PERMISSION_VERBS:
#     these two verbs never take a bare "of"/"to" complement in ordinary
#     English regardless of case ("generates of X" / "produces to X" are
#     always broken), unlike authorize/allow/permit/grant/provide, which
#     legitimately take "to" without a number ("permits access to Y") --
#     that's why detector 3 needs the capitalized-word restriction and this
#     one doesn't. Stress-tested against 5 real published articles
#     (2026-07-23): zero matches, so no known false-positive risk yet.
_OF_TO_VERBS = ["generate", "generates", "produce", "produces"]
_OF_TO_VERB_PATTERN = re.compile(r"\b(" + "|".join(_OF_TO_VERBS) + r")\s+(of|to)\s+")


def _find_of_to_verb(text: str) -> List[Dict]:
    return [{
        "type": "missing_quantity_before_of",
        "match": m.group(0).strip(),
        "context": text[max(0, m.start() - 20):m.end() + 40].strip(),
        "position": m.start(),
    } for m in _OF_TO_VERB_PATTERN.finditer(text)]


# ---------------------------------------------------------------------------
# 3c. "have"/"has" directly touching "of" -- added 2026-07-24 (post 48982:
#     "Once you have of clean history, apply for one unsecured card", a bare
#     duration -- "have 6 months of clean history" -- stripped with no
#     quantifier word before it, same failure shape as 3b).
#
#     "of" ONLY, deliberately NOT "to" like 3b's verbs: "have to"/"has to"
#     is the ordinary modal-necessity construction ("you have to apply") and
#     is extremely common, correct English -- folding "to" in here would
#     false-positive constantly. "have of"/"has of" has no such legitimate
#     use; "have" is a transitive verb that needs a direct object before
#     "of" can attach to it ("have SIX MONTHS of clean history"), never "of"
#     immediately.
_OF_ONLY_VERBS = ["have", "has"]
_OF_ONLY_VERB_PATTERN = re.compile(r"\b(" + "|".join(_OF_ONLY_VERBS) + r")\s+of\s+")

# ---------------------------------------------------------------------------
# 3d. "show"/"shows"/"showing" directly touching "of" -- added 2026-07-24
#     (post 48990: "Bank statements showing of rent in a Canadian or foreign
#     account", a bare amount -- "showing 3 months of rent" -- stripped with
#     no quantifier word before it, same shape as 3b/3c).
#
#     NOT folded into _OF_ONLY_VERBS: unlike have/has, "showing"/"show(s)"
#     has a genuinely common NOUN sense where "of" legitimately follows it
#     ("a showing of support", "a showing of solidarity") -- always preceded
#     by an article ("a"/"an"/"the") in that usage. The broken VERB/
#     participle sense (a document "showing X" modifying a preceding noun,
#     as in the real bug) is never preceded by an article right before
#     "showing" -- it's preceded by the noun it modifies ("statements
#     showing", "documents showing"). Guarding on that one signal keeps the
#     noun sense safe without losing the real catch.
_SHOW_OF_PATTERN = re.compile(r"\b(show|shows|showing)\s+of\s+", re.IGNORECASE)
_ARTICLE_IMMEDIATELY_BEFORE = re.compile(r"\b(a|an|the)\s+$", re.IGNORECASE)


def _find_show_of(text: str) -> List[Dict]:
    findings = []
    for m in _SHOW_OF_PATTERN.finditer(text):
        prefix = text[max(0, m.start() - 5):m.start()]
        if _ARTICLE_IMMEDIATELY_BEFORE.search(prefix):
            continue  # "a/the showing of X" -- legitimate noun usage
        findings.append({
            "type": "missing_quantity_before_of",
            "match": m.group(0).strip(),
            "context": text[max(0, m.start() - 20):m.end() + 40].strip(),
            "position": m.start(),
        })
    return findings


def _find_of_only_verb(text: str) -> List[Dict]:
    return [{
        "type": "missing_quantity_before_of",
        "match": m.group(0).strip(),
        "context": text[max(0, m.start() - 20):m.end() + 40].strip(),
        "position": m.start(),
    } for m in _OF_ONLY_VERB_PATTERN.finditer(text)]

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
    matches = list(_DANGLING_PATTERN_LOOSE_SPACE.finditer(text)) + list(_DANGLING_PATTERN_TIGHT_SPACE.finditer(text))
    return [{
        "type": "dangling_connector",
        "match": m.group(0).strip(),
        "context": text[max(0, m.start() - 60):m.end() + 20].strip(),
        "position": m.start(),
    } for m in matches]


def _find_sentence_initial_after(text: str) -> List[Dict]:
    return [{
        "type": "dangling_connector",
        "match": m.group(0).strip(),
        "context": text[max(0, m.start() - 20):m.end() + 40].strip(),
        "position": m.start(),
    } for m in _SENTENCE_INITIAL_AFTER_PATTERN.finditer(text)]


# ---------------------------------------------------------------------------
# 1c. A connector word sitting at the literal END OF A LINE with nothing
#     after it at all -- not even punctuation -- added 2026-07-24 (post
#     48972, a numbered list item: "**Receive a temporary paper license**
#     --the physical card arrives by mail within", nothing after "within").
#     Detector 1's connector-before-punctuation check can't catch this: there
#     IS no punctuation, the line just stops. Detector 9 (missing terminal
#     punctuation) can't either, by design -- it deliberately exempts list
#     items entirely (see its docstring), because most list items in this
#     site's articles are short label phrases that never carry a period
#     ("- Fast processing", "1. Submit application") and flagging every one
#     of those would be constant noise on legitimate content.
#
#     This is narrower and safer than loosening detector 9's list exemption:
#     it only fires when the LAST WORD on the line is itself one of the
#     known-dangling connector/verb words, which a short label phrase
#     essentially never ends on ("Fast processing" ends on a noun, not "of"/
#     "within"/"to"). Confirmed against real drafts (2026-07-24): every
#     other list item in the same numbered list as the real bug -- "Gather
#     identity and status documents", "Pass a knowledge test", etc. -- ends
#     on an ordinary noun and is correctly left alone.
#
#     Header lines are excluded: editorial headings legitimately end on a
#     stranded preposition constantly ("Who This Checklist Is Built For",
#     "What You'll Need") -- a real false positive hit testing this against
#     post 48854's own "### Who This Checklist Is Built For" heading.
_EOL_CONNECTOR_WORDS = (_DANGLING_CONNECTORS + _DANGLING_VERB_QUANTIFIERS + ["after"])
_DANGLING_AT_EOL_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in _EOL_CONNECTOR_WORDS) + r")\s*$",
    re.IGNORECASE,
)
_HEADER_PREFIX = re.compile(r"^\s*#{1,6}\s")


def _find_dangling_connector_at_eol(text: str) -> List[Dict]:
    findings = []
    pos = 0
    for line in text.split("\n"):
        if not _HEADER_PREFIX.match(line):
            m = _DANGLING_AT_EOL_PATTERN.search(line)
            if m:
                findings.append({
                    "type": "dangling_connector",
                    "match": m.group(0).strip(),
                    "context": line.strip()[-100:],
                    "position": pos + m.start(),
                })
        pos += len(line) + 1
    return findings


# ---------------------------------------------------------------------------
# 1d. The same word/phrase repeated back-to-back in a comma-separated list --
#     "including Canada, the UK, India, Mexico, Australia, Australia, and
#     the Philippines" (real bug, post 48982, 2026-07-24). Restricted to
#     CAPITALIZED tokens with an exact (case-sensitive) repeat: emphatic
#     mid-sentence reduplication in real English ("very, very good", "no,
#     no, I insist") is virtually always lowercase-lowercase, since only the
#     first word of a sentence is capitalized -- so this can't confuse a
#     deliberate stylistic repeat with a generation-loop duplicate the way a
#     case-insensitive or lowercase-inclusive version would.
_DUPLICATE_CAPITALIZED_PATTERN = re.compile(r"\b([A-Z][a-zA-Z]{2,}),\s+\1\b")


def _find_duplicate_capitalized_word(text: str) -> List[Dict]:
    return [{
        "type": "duplicate_list_item",
        "match": m.group(0),
        "context": text[max(0, m.start() - 40):m.end() + 40].strip(),
        "position": m.start(),
    } for m in _DUPLICATE_CAPITALIZED_PATTERN.finditer(text)]


_AT_LEAST_MOST_TAIL = re.compile(r"^\s*(least|most)\b", re.IGNORECASE)


def _find_adjacent_connector_pairs(text: str) -> List[Dict]:
    findings = []
    for m in _ADJACENT_PAIR_PATTERN.finditer(text):
        normalized = re.sub(r"\s+", " ", m.group(0).lower())
        if normalized in _ADJACENT_PAIR_ALLOWLIST:
            continue
        # "at" is the second word AND is itself the start of the fixed,
        # already-safe idiom "at least"/"at most" ("for at least the past
        # two years") -- real false positive on this exact fixture,
        # 2026-07-24. "at" alone still gets caught pairing with anything
        # else ("with at" isn't a thing); only the least/most continuation
        # is exempted.
        if m.group(2).lower() == "at" and _AT_LEAST_MOST_TAIL.match(text[m.end():]):
            continue
        findings.append({
            "type": "adjacent_connector_pair",
            "match": m.group(0),
            "context": text[max(0, m.start() - 60):m.end() + 20].strip(),
            "position": m.start(),
        })
    return findings


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


# ---------------------------------------------------------------------------
# 8. "a" immediately followed by a vowel-sound word ("a emergency" instead of
#    "an emergency") -- added 2026-07-23 (post 48931: "a newcomer facing a
#    emergency might use a payday loan"). This is a reliable fingerprint of a
#    deleted word: the original almost certainly had a quantity between them
#    ("a $400 emergency"), and removing it left the article's a/an agreement
#    broken against the next word's actual sound.
#
#    Exceptions are words that START with a vowel LETTER but a consonant
#    SOUND ("a university", "a U.S. bank", "a one-time fee") -- English a/an
#    agreement follows pronunciation, not spelling. Curated + validated
#    against 5 real published articles (2026-07-23): the only real hits were
#    "U.S.-equivalent/-readable/-compatible" compounds, all correctly using
#    "a" -- covered by the u.s.-prefix rule below, not a fixed word list.
_A_AN_EXCEPTIONS = {
    "us", "usa", "uk", "uae",
    "united", "unique", "uniform", "uniformed", "unanimous",
    "usual", "usually", "user", "users", "utility", "utilities",
    "university", "universities", "universal", "one", "one-time", "once",
    "european", "europe", "u-visa", "usc",
    # 2026-07-23 addition (real miss found on a fresh live batch, workflow run
    # 30013499548): "unit"/"union"/"unify" etc. are also "yoo-" pronounced.
    # Deliberately NOT a blanket "uni-" prefix rule -- "un-" + a real word
    # (uninsured, unintended, unimportant, unidentified) is the negation
    # prefix, genuinely vowel-sound, and must stay flaggable ("a uninsured
    # driver" is a real bug this insurance-content site could produce).
    "unit", "units", "union", "unions", "unify", "unified", "unicorn",
    "unilateral",
}
# [^\s—–]+ (not \S+): an em/en-dash used as punctuation is often glued
# directly to the next word with no space ("a unit—meaningfully compresses
# the process"), and \S+ would swallow it into the captured token, making
# "unit—meaningfully" (not in any exception list) instead of "unit" (a
# known exception) -- real miss found 2026-07-23, workflow run 30013499548.
_A_AN_PATTERN = re.compile(r"\ba\s+([^\s—–]+)")


def _is_a_an_exception(word_lower: str) -> bool:
    if word_lower.startswith("u.s") or word_lower.startswith("us-"):
        return True
    return word_lower in _A_AN_EXCEPTIONS


def _find_a_an_disagreement(text: str) -> List[Dict]:
    findings = []
    for m in _A_AN_PATTERN.finditer(text):
        word = m.group(1)
        low = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z.\-]+$", "", word).lower()
        if not low or low[0] not in "aeiou":
            continue
        if _is_a_an_exception(low):
            continue
        findings.append({
            "type": "a_an_disagreement",
            "match": f"a {word}",
            "context": text[max(0, m.start() - 40):m.end() + 20].strip(),
            "position": m.start(),
        })
    return findings


# ---------------------------------------------------------------------------
# 9. A prose paragraph that ends with no terminal punctuation at all -- the
#    fingerprint of scripts/soften_claims.py's CASE-4 appositive strip, which
#    can delete from an opening em-dash through the rest of the line
#    (including the final period) when the residual clause is short enough.
#    Added 2026-07-23 (post 48931: "...but a foundation for" -- nothing
#    after "for", not even a period).
#
#    Deliberately narrow to avoid false-positives on markdown structure that
#    legitimately has no terminal punctuation: headers, list items, table
#    rows, blockquotes, and bolded pseudo-headings ("**Week 1-2: Identity
#    and Status Foundation**"). Validated against 5 real published articles
#    (2026-07-23) after two false positives were found and excluded: a
#    blockquote-style internal-link callout, and a bolded step-header line.
#
#    PER-LINE as of 2026-07-24 (post 48990: a 3-item bullet list's last item
#    was immediately followed, with no blank line, by an unmarked
#    continuation line -- "- **Pre-authorized payment setup:** Offering
#    automatic rent withdrawal signals reliability\nBritish Columbia allows
#    first and last month" -- itself truncated, no ending punctuation). The
#    ORIGINAL version bailed on the ENTIRE paragraph block the moment ANY
#    line in it had a list/header marker, specifically to avoid judging a
#    real paragraph by a header's own last word when the two were fused
#    with no blank line between them (see git history). That blanket
#    bailout also silently protected this shape: a block mixing legitimate
#    marker-exempt list lines with one genuine unmarked, truncated
#    continuation line never got evaluated at all. Now each line in a block
#    is judged independently -- marked lines stay exempt, but an unmarked
#    line is checked on its own text, so a header/list line preceding real
#    prose can no longer corrupt that prose's own judgment, and a truncated
#    unmarked continuation can no longer hide behind its marked neighbors.
#    Safe only because this pipeline's paragraphs are single un-wrapped
#    lines (confirmed empirically, 2026-07-23: no artificial mid-sentence
#    line breaks in real drafts) -- a hard-wrapped-paragraph pipeline would
#    need a different check here, since a wrapped line legitimately ends
#    without punctuation too.
_LIST_OR_HEADER_PREFIX = re.compile(r"^\s*(#{1,6}\s|[-*+]\s|\d+[.)]\s|>\s|\|)")
_TRAILING_EMPHASIS = re.compile(r"[*_]+$")
_ACCEPTABLE_TERMINAL_CHARS = '.!?"\')”’:'
_STOPWORDS_FOR_HEADING_CHECK = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with",
    "at", "by", "from", "your", "you",
}


def _looks_like_heading(stripped_para: str) -> bool:
    """Title-Case-throughout short line -- a bolded/plain pseudo-heading
    rather than real prose, even without markdown '#' syntax."""
    words = stripped_para.split()
    if len(words) > 12:
        return False
    for w in words:
        core = re.sub(r"[^a-zA-Z]", "", w)
        if not core:
            continue  # pure numbers/punctuation tokens ("1-2:") don't count
        if core.lower() in _STOPWORDS_FOR_HEADING_CHECK:
            continue
        if not core[0].isupper():
            return False
    return True


_CONTAINS_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")


def _find_missing_terminal_punctuation(text: str) -> List[Dict]:
    findings = []
    pos = 0
    for line in text.split("\n"):
        line_start = pos
        pos += len(line) + 1
        raw = line.strip()
        if not raw or _LIST_OR_HEADER_PREFIX.match(raw):
            continue
        # Structured markup (raw HTML tables/figures/spans some pipeline
        # steps embed directly in the draft) isn't prose and legitimately
        # has no terminal punctuation -- skip it rather than risk flagging a
        # <table>/<td> fragment. Confirmed necessary testing against real
        # WordPress output (2026-07-23): TOC spans and table cells produced
        # exactly this kind of false positive.
        if _CONTAINS_HTML_TAG.search(raw):
            continue
        stripped = _TRAILING_EMPHASIS.sub("", raw).rstrip()
        if not stripped or len(stripped.split()) < 6:
            continue
        if _looks_like_heading(stripped):
            continue
        if stripped[-1] not in _ACCEPTABLE_TERMINAL_CHARS:
            findings.append({
                "type": "missing_terminal_punctuation",
                "match": stripped[-80:],
                "context": stripped[-120:],
                "position": line_start,
            })
    return findings


# ---------------------------------------------------------------------------
# 10. Internal image-prompt labels (agents/agent_09_image_prompt_generator.py
#     alt_text f-strings: "Comparison guide: ...", "Step-by-step checklist:
#     ...", "Supporting image: ...", "How to X: step-by-step process for
#     newcomers") leaking somewhere they'd be reader-visible.
#
#     IMPORTANT: $DRAFT (what scan_body actually receives in the real
#     pipeline, agent_04/article_draft.md) never contains these strings --
#     agent_09 only ever writes them to image_prompts.json, and agent_11
#     writes them straight into the WordPress media alt="" attribute without
#     ever touching $DRAFT. The alt="" and <figcaption> regexes below are
#     dead weight against today's real body_text input; they exist only as
#     defense-in-depth (a future refactor that inlines images into $DRAFT, or
#     the still-live legacy scripts/produce_article.py::inject_4_body_images
#     figcaption path, both flow through this same scan_body()). The
#     mechanism that actually catches today's real bug is scan_alt_texts()
#     below, wired into scripts/placeholder_gate.py's --image-prompts flag,
#     which reads image_prompts.json directly. Added 2026-07-23.
_INTERNAL_LABEL_PREFIXES = (
    "comparison guide:",
    "step-by-step checklist:",
    "supporting image:",
)
_PROCESS_LABEL_PATTERN = re.compile(r"^how to .+:\s*step-by-step process for", re.IGNORECASE)
_ALT_ATTR_PATTERN = re.compile(r'alt=["\']([^"\']*)["\']', re.IGNORECASE)
_FIGCAPTION_PATTERN = re.compile(r"<figcaption[^>]*>(.*?)</figcaption>", re.IGNORECASE | re.DOTALL)
_DUPLICATE_HOWTO_PATTERN = re.compile(r"\bhow to how to\b", re.IGNORECASE)


def _is_leaked_internal_label(value: str) -> bool:
    low = value.strip().strip('"\'').lower()
    return low.startswith(_INTERNAL_LABEL_PREFIXES) or bool(_PROCESS_LABEL_PATTERN.match(value.strip()))


def scan_alt_texts(alt_texts: List[str]) -> List[Dict]:
    """Check agent_09's image_prompts.json alt_text values directly, rather
    than relying on finding them inline in body text -- the current pipeline
    never writes alt_text into $DRAFT (the file scan_body actually runs on):
    agent_09 stores it in image_prompts.json and agent_11 writes it straight
    into the WordPress media alt="" attribute, a step scan_body never sees.
    Wired into scripts/placeholder_gate.py via the optional --image-prompts
    flag (2026-07-23)."""
    findings = []
    for i, alt in enumerate(alt_texts):
        if alt and _is_leaked_internal_label(alt):
            findings.append({
                "type": "leaked_internal_label_alt",
                "match": alt[:100],
                "context": f"image_prompts[{i}].alt_text = {alt!r}"[:150],
                "position": i,
            })
    return findings


def _find_leaked_internal_labels(text: str) -> List[Dict]:
    findings = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and _is_leaked_internal_label(stripped):
            findings.append({
                "type": "leaked_internal_label",
                "match": stripped[:100],
                "context": stripped[:150],
                "position": text.find(line),
            })
    for m in _ALT_ATTR_PATTERN.finditer(text):
        if _is_leaked_internal_label(m.group(1)):
            findings.append({
                "type": "leaked_internal_label_alt",
                "match": m.group(1)[:100],
                "context": m.group(0)[:150],
                "position": m.start(),
            })
    for m in _FIGCAPTION_PATTERN.finditer(text):
        inner = re.sub(r"<[^>]+>", "", m.group(1))
        if _is_leaked_internal_label(inner):
            findings.append({
                "type": "leaked_internal_label_figcaption",
                "match": inner.strip()[:100],
                "context": m.group(0)[:150],
                "position": m.start(),
            })
    for m in _DUPLICATE_HOWTO_PATTERN.finditer(text):
        findings.append({
            "type": "duplicate_how_to",
            "match": m.group(0),
            "context": text[max(0, m.start() - 20):m.end() + 60].strip(),
            "position": m.start(),
        })
    return findings


# ---------------------------------------------------------------------------
# 11. A paragraph immediately after a heading that opens with a forward-
#     anaphora discourse phrase ("Beyond that,", "Additionally,", ...) --
#     added 2026-07-24 (post 48990, FAQ "How much money should I set aside
#     before signing a lease?": the answer opened with "Beyond that, budget
#     for utility connection fees..." -- "that" has nothing to refer to.
#
#     Root cause (agents/_fact_coverage.py + scripts/soften_claims.py):
#     _soften_prose's EXISTING, intentional min_residue_words rule deletes a
#     whole SENTENCE (not just its number) when stripping an unsourced
#     figure leaves fewer than 4 content words behind -- documented,
#     already-tested behavior, not a new bug. What's new is the visible
#     damage: this FAQ answer's first sentence was almost certainly a
#     short, number-only lead ("Budget $X-$Y for move-in costs.") that got
#     fully deleted under that existing rule, and a SECOND sentence in the
#     same answer happened to open with a discourse connective that
#     depended on the first ("Beyond THAT..."). The original text isn't
#     recoverable (soften rewrites the draft in place, no pre-strip
#     snapshot survives past that pipeline step) -- this detector is the
#     downstream safety net, not a fix to the deletion rule itself.
#
#     Deliberately scoped to right after a HEADING, not every paragraph:
#     between two ORDINARY paragraphs, opening with "Additionally," to
#     continue the previous paragraph's thought is completely normal,
#     correct English -- flagging that generally would be constant noise.
#     A heading is a real "fresh start" boundary (a new FAQ question, a new
#     section) where a forward reference to content before it is never
#     correct, so scoping there keeps this both safe and exactly targeted
#     at the real bug (FAQ answers are headed by an H3 in this pipeline).
_HEADING_LINE = re.compile(r"^\s*#{1,6}\s")
_ORPHANED_ANAPHORA_PHRASES = (
    "beyond that", "in addition to that", "additionally", "as a result",
    "because of this", "this means", "as such", "on top of that",
    "furthermore", "moreover", "that said", "with that",
)


def _find_orphaned_anaphora_after_heading(text: str) -> List[Dict]:
    findings = []
    lines = text.split("\n")
    pos = 0
    offsets = []
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1
    prev_was_heading = False
    for i, line in enumerate(lines):
        raw = line.strip()
        if not raw:
            continue
        if _HEADING_LINE.match(raw):
            prev_was_heading = True
            continue
        if prev_was_heading:
            stripped = _TRAILING_EMPHASIS.sub("", raw).lstrip("*_ ")
            low = stripped.lower()
            if low.startswith(_ORPHANED_ANAPHORA_PHRASES):
                findings.append({
                    "type": "orphaned_anaphora",
                    "match": stripped[:60],
                    "context": stripped[:120],
                    "position": offsets[i],
                })
        prev_was_heading = False
    return findings


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
    findings += _find_sentence_initial_after(text)
    findings += _find_dangling_connector_at_eol(text)
    findings += _find_duplicate_capitalized_word(text)
    findings += _find_adjacent_connector_pairs(text)
    findings += _find_verb_connector_capitalized(text)
    findings += _find_of_to_verb(text)
    findings += _find_of_only_verb(text)
    findings += _find_show_of(text)
    findings += _find_duration_noun_missing_quantity(text)
    findings += _find_fused_link_sentences(text)
    findings += _find_empty_image_src(text)
    findings += _find_a_an_disagreement(text)
    findings += _find_missing_terminal_punctuation(text)
    findings += _find_orphaned_anaphora_after_heading(text)
    findings += _find_leaked_internal_labels(text)
    return sorted(findings, key=lambda f: f["position"])


def scan(text: str, title: str = "") -> List[Dict]:
    """Convenience wrapper: scan_body(text) + scan_title(title) combined."""
    findings = scan_body(text)
    if title:
        findings += scan_title(title)
    return findings
