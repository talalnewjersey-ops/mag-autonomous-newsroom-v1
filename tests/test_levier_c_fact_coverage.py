"""LEVIER C -- fact-coverage predicate (agents/_fact_coverage.py). Offline, no
network, no LLM.

Central scenario (reproduces the real incident, run 28731153809): a genuine,
live CFPB link supports "30%" (the engraved us_credit utilization fact). A
fabricated "10%" sitting in the SAME window, next to the SAME link, must be
detected and treated as unsourced -- the link's presence does not certify it.

Also proves the qualitative-fact guard (the delicate case flagged before
coding): a fact with NO numeric value (e.g. "five factors, no %") legitimately
covers ITSELF when cited with no number nearby, but can NEVER cover a number
that happens to sit beside its link -- an empty token set matches nothing.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents._fact_coverage import (
    _token, _fact_tokens, covering_fact, classify_claims, count_cited_stable_facts,
)

# Real us_credit STABLE facts (agents/_vertical_facts.py), verbatim URLs/values.
CFPB_UTIL = "https://www.consumerfinance.gov/ask-cfpb/how-do-i-get-and-keep-a-good-credit-score-en-318/"
USAGOV_FACTORS = "https://www.usa.gov/credit-score"                 # qualitative: 5 factors, NO %
FTC_DISPUTE = "https://consumer.ftc.gov/articles/disputing-errors-your-credit-reports"

# Real us_auto STABLE fact: Texas minimum liability, 3 distinct dollar values.
TX_URL = "https://www.tdi.texas.gov/pubs/consumer/cb020.html"

# Real us_credit STABLE facts for PART 2 (bare durations/counts).
CFPB_RETENTION = "https://www.consumerfinance.gov/ask-cfpb/how-long-does-negative-information-remain-on-my-credit-report-en-323/"
FTC_FREE = "https://consumer.ftc.gov/articles/free-credit-reports"


# ---------------- _token: strict normalization, no tolerance ----------------

def test_token_percent():
    assert _token("30%") == ("percent", 30.0)


def test_token_dollar_strips_commas():
    assert _token("$30,000") == ("dollar", 30000.0)


def test_token_bps_and_points_are_not_fungible():
    assert _token("50 bps") != _token("50 points")
    assert _token("50 bps")[0] == "bps"
    assert _token("50 points")[0] == "points"


def test_token_unparseable_span_returns_none():
    # A points-RANGE ("20-40 points") is deliberately not reduced to one value --
    # doubt -> None -> can never be "covered" by anything.
    assert _token("20-40 points") is None


# ---------------- covering_fact: the central real-incident scenario ----------------

def test_covered_number_matches_engraved_value():
    fact = covering_fact("30%", [CFPB_UTIL], "us_credit")
    assert fact is not None and fact["source_url"] == CFPB_UTIL


def test_uncovered_number_next_to_the_SAME_real_link_is_not_covered():
    # The incident: "10%" sits next to the exact link that supports 30%. The link
    # existing is not proof -- 10 is not in the fact's token set.
    fact = covering_fact("10%", [CFPB_UTIL], "us_credit")
    assert fact is None


def test_no_engraved_fact_for_this_url_is_never_covered():
    # A number near a real .gov link that has NO Couche 1 fact at all (e.g. a
    # generic source-pool page) -- Approach B: always uncovered, no exceptions.
    fact = covering_fact("25%", ["https://www.consumerfinance.gov/consumer-tools/credit-cards/"],
                          "us_credit")
    assert fact is None


# ---------------- multi-value fact: endpoint match, strict non-tolerance ----------------

def test_one_endpoint_of_a_multi_value_fact_is_covered():
    # TX fact value = "$30,000 .../ $60,000 .../ $25,000 ..." -- citing any ONE
    # of the three values at the real URL is genuinely covered.
    assert covering_fact("$25,000", [TX_URL], "us_auto") is not None
    assert covering_fact("$60,000", [TX_URL], "us_auto") is not None


def test_near_miss_value_is_NOT_covered_no_tolerance():
    # $27,500 is close to both $25,000 and $30,000 but equals neither -- strict
    # rule: "en cas de doute, on strip", no fuzzy/rounding tolerance.
    assert covering_fact("$27,500", [TX_URL], "us_auto") is None


# ---------------- QUALITATIVE-FACT GUARD (the delicate case) ----------------

def test_qualitative_fact_has_no_numeric_tokens():
    from agents._vertical_facts import VERTICAL_FACTS
    factors_fact = next(f for f in VERTICAL_FACTS["us_credit"] if f["source_url"] == USAGOV_FACTORS)
    assert _fact_tokens(factors_fact) == frozenset()


def test_qualitative_fact_can_never_cover_a_number():
    # A fabricated FICO weighting sitting beside the "5 factors, no %" fact's own
    # link must NOT be laundered by it (the real draft-48438 fabrication pattern).
    assert covering_fact("35%", [USAGOV_FACTORS], "us_credit") is None


def test_qualitative_fact_with_no_number_nearby_is_legitimate_via_classify_claims():
    # The fact cited on its own (no digit anywhere near it) produces NO numeric
    # claim at all -- classify_claims never even considers it "unsourced", because
    # there is nothing for _NUM_RE to flag. Nothing to strip.
    text = (f"Your score reflects several factors from your credit report "
            f"([USA.gov]({USAGOV_FACTORS})), including payment history.")
    claims = classify_claims(text, "us_credit")
    assert claims == []


# ---------------- classify_claims: end-to-end, single traversal ----------------

def test_classify_claims_marks_covered_vs_uncovered_in_one_pass():
    text = (f"Experts advise keeping your credit use to no more than 30% of your "
            f"total credit limit ([CFPB]({CFPB_UTIL})). Some advisors even recommend "
            f"staying under 10% for an excellent score.")
    claims = classify_claims(text, "us_credit")
    by_number = {text[c["start"]:c["end"]]: c for c in claims}
    assert by_number["30%"]["fact"] is not None
    assert by_number["10%"]["fact"] is None


# ---------------- count_cited_stable_facts: G-Substance's "cited correctly" ----------------

def test_count_cited_stable_facts_qualitative_via_url_presence_numeric_via_match():
    text = (f"Dispute errors within 30 days ([FTC]({FTC_DISPUTE})). "
            f"Keep utilization no more than 30% of your limit ([CFPB]({CFPB_UTIL})).")
    n = count_cited_stable_facts(text, "us_credit")
    # Both are numeric-matched post PART 2 (30 days -> dispute fact's own engraved
    # value; 30% -> utilization fact's own engraved value) -- 2 distinct facts.
    assert n == 2


def test_count_cited_stable_facts_does_not_credit_a_wrong_number_near_the_link():
    text = (f"Dispute errors within 30 days ([FTC]({FTC_DISPUTE})). "
            f"Some say keep utilization under 10% ([CFPB]({CFPB_UTIL})).")
    n = count_cited_stable_facts(text, "us_credit")
    assert n == 1   # FTC_DISPUTE only -- the utilization fact is NOT credited by proximity alone


# ---------------- LEVIER C PART 2: bare duration/count units ----------------
# days/weeks/months/years/bureaus ONLY. hours/minutes deliberately excluded
# (conscious residue -- see agents/_claims.py docstring).

def test_token_bare_duration_and_adjective_form():
    assert _token("7 years") == ("year", 7.0)
    assert _token("24-month") == ("month", 24.0)          # adjective form, hyphen, singular
    assert _token("3 nationwide bureaus") == ("bureau", 3.0)


def test_token_bare_range():
    assert _token("12-24 months") == ("month_range", (12.0, 24.0))


def test_token_bare_number_without_known_unit_returns_none():
    # "2026" (calendar year), "under 21" (bare age), "580" (bare score) -- none
    # has a days/weeks/months/years/bureaus word attached -> unparseable -> None.
    assert _token("2026") is None
    assert _token("21") is None
    assert _token("580") is None


def test_covered_bare_duration_matches_engraved_value():
    fact = covering_fact("7 years", [CFPB_RETENTION], "us_credit")
    assert fact is not None and fact["source_url"] == CFPB_RETENTION


def test_uncovered_bare_duration_next_to_the_SAME_real_link_is_not_covered():
    # The bare-number "under 10%": a fabricated "8 years" beside the link that
    # actually supports 7 years.
    assert covering_fact("8 years", [CFPB_RETENTION], "us_credit") is None


def test_a_different_facts_real_value_does_not_cover_the_wrong_link():
    # "10 years" is a REAL engraved us_credit value (bankruptcy retention, a
    # DIFFERENT fact/URL) -- must not cover the retention fact's own link.
    assert covering_fact("10 years", [CFPB_RETENTION], "us_credit") is None


def test_covered_bureau_count_matches_engraved_value():
    assert covering_fact("3 nationwide bureaus", [FTC_FREE], "us_credit") is not None


def test_uncovered_bureau_count_is_not_covered():
    assert covering_fact("4 nationwide bureaus", [FTC_FREE], "us_credit") is None


def test_bare_age_is_out_of_scope_not_a_claim_at_all():
    # "under 25" has no adjacent duration unit -- _NUM_RE never even extracts it
    # as a claim, so classify_claims produces no entry for it at all (not
    # "covered", simply invisible -- the documented PART 2 residue).
    text = f"An applicant under 25 needs a co-signer ([USA.gov]({USAGOV_FACTORS}))."
    assert classify_claims(text, "us_credit") == []
