"""PROXIMITY CHECK REDESIGN (2026-07-06): replaced the fixed character window
(100, then 150 -- see git history) with a SENTENCE boundary, after a THIRD
real false positive beat the 150-char window: a citation sat 203 chars from
its number in a real sentence ("...students must wait at least 10 days after
U.S. arrival and at least 2 government business days after their SEVIS
record is marked Active before applying for a state driver's license --
[DHS link]."). A fixed window will always eventually lose to a longer real
sentence; a same-sentence check has no such ceiling.

Three properties proven here, not just asserted:
  1. All THREE real false-positive cases found across this project's control
     runs (Texas $30,000 @119 chars, NY $10,000 @134 chars, SEVIS "10 days"
     @203 chars) are now covered -- including the abbreviation trap ("U.S.")
     that a naive sentence-splitter would trip on.
  2. The redesign is STILL safe by construction: a divergent/fabricated value
     next to the right citation stays uncovered regardless of sentence length
     (same guarantee as the old window, now sentence-scoped instead of
     char-scoped).
  3. NEW safety property this redesign specifically had to add: a markdown
     TABLE ROW's own commercial figure must never "borrow" a citation from
     unrelated PROSE that follows the table (rows rarely contain a period,
     so a naive "nearest .!?" search would otherwise reach past the whole
     table into the next paragraph) -- caught during this redesign, not a
     hypothetical.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents._fact_coverage import classify_claims, _sentence_span, _block_span

CFPB_RETENTION = "https://www.consumerfinance.gov/ask-cfpb/how-long-does-negative-information-remain-on-my-credit-report-en-323/"


# ---------------------------------------------------------------- the 3 real false positives

TEXAS_LINE = (
    "- **Texas** requires 30/60/25 liability: $30,000 bodily injury per person, "
    "$60,000 per accident, and $25,000 property damage — "
    "[per the Texas Department of Insurance](https://www.tdi.texas.gov/pubs/consumer/cb020.html)."
)
NY_LINE = (
    "- **New York** mandates 25/50/10 liability —$25,000 per accident, $10,000 property damage "
    "(rising to $100,000 if two or more people die), plus mandatory no-fault PIP —"
    "[per New York DFS minimum requirements](https://www.dfs.ny.gov/consumers/auto_insurance/minimum_auto_insurance_requirements)."
)
SEVIS_SENTENCE = (
    "F and M visa holders face a sequencing requirement before they can legally drive independently. "
    "As confirmed by DHS Study in the States, students must wait at least 10 days after U.S. arrival and "
    "at least 2 government business days after their SEVIS record is marked Active before applying for a "
    "state driver's license — [as detailed by the DHS Study in the States resource]"
    "(https://studyinthestates.dhs.gov/students/study/driving-in-the-united-states)."
)


def test_texas_case_now_covered():
    claims = classify_claims(TEXAS_LINE, "us_auto")
    residual = [TEXAS_LINE[c["start"]:c["end"]] for c in claims if c["fact"] is None]
    assert residual == []


def test_ny_case_now_covered():
    claims = classify_claims(NY_LINE, "us_auto")
    residual = [NY_LINE[c["start"]:c["end"]] for c in claims if c["fact"] is None]
    assert residual == []


def test_sevis_case_203_chars_now_covered():
    # this is the case that beat the 150-char window -- the whole point of
    # the redesign. Also exercises the "U.S." abbreviation trap.
    claims = classify_claims(SEVIS_SENTENCE, "us_auto")
    residual = [SEVIS_SENTENCE[c["start"]:c["end"]] for c in claims if c["fact"] is None]
    assert residual == [], f"the 203-char real case must now be covered: {residual}"


def test_abbreviation_us_does_not_prematurely_end_the_sentence():
    # isolates the exact bug found while building this fix: "U.S." was being
    # treated as ending the sentence right after "U.", cutting the sentence
    # short before the actual citation later in the same real sentence.
    idx = SEVIS_SENTENCE.find("10 days")
    url_start = SEVIS_SENTENCE.index("https://studyinthestates")
    url_end = SEVIS_SENTENCE.index(")", url_start)
    lo, hi = _sentence_span(SEVIS_SENTENCE, idx, idx + len("10 days"))
    assert hi > url_end, "the sentence span must reach past the full citation URL"


def test_domain_shaped_link_display_text_does_not_prematurely_end_the_sentence():
    # A THIRD real bug found on the run immediately after this fix first
    # landed: a markdown link whose DISPLAY TEXT is itself a domain-shaped
    # string -- "[studyinthestates.dhs.gov](https://studyinthestates.dhs.gov/
    # ...)" -- has its own dots in the display text (which comes BEFORE the
    # real URL). Those dots were being treated as sentence-enders, cutting
    # the span short before the actual https:// URL even started. A period
    # anywhere inside a markdown link's span (display text OR url) must
    # never end a sentence -- the whole link is one atomic unit.
    sentence = (
        'The DHS study guide specifies applicants must wait 10 days after U.S. arrival '
        '*and* at least 2 government business days after the SEVIS record shows "Active" '
        'before applying for a state license ([studyinthestates.dhs.gov]'
        '(https://studyinthestates.dhs.gov/students/study/driving-in-the-united-states)).'
    )
    claims = classify_claims(sentence, "us_auto")
    residual = [sentence[c["start"]:c["end"]] for c in claims if c["fact"] is None]
    assert residual == [], f"real run-6 case must be covered: {residual}"


# ---------------------------------------------------------------- adversarial: still safe

def test_divergent_value_next_to_correct_link_stays_uncovered():
    # "10 years" IS a real engraved us_credit value (a DIFFERENT fact/URL) --
    # sitting next to the RETENTION link (whose own value is only 7/45) must
    # still be rejected, regardless of how the proximity check is implemented.
    text = f"Negative information can stay on file for 10 years ([CFPB]({CFPB_RETENTION}))."
    claims = classify_claims(text, "us_credit")
    residual = [c for c in claims if c["fact"] is None]
    assert len(residual) == 1


def test_divergent_value_stays_uncovered_even_in_an_extremely_long_sentence():
    # Proves the property structurally: padding the SAME sentence with a lot
    # of filler text (no period) between the claim and the citation still
    # must not launder a divergent value -- covering_fact's exact-token
    # requirement is what protects this, not sentence length.
    filler = " ".join(["this sentence has a lot of extra words in the middle"] * 10)
    text = f"Negative information can stay on file for 10 years, {filler} ([CFPB]({CFPB_RETENTION}))."
    claims = classify_claims(text, "us_credit")
    residual = [c for c in claims if c["fact"] is None]
    assert len(residual) == 1


# ---------------------------------------------------------------- table-row / paragraph safety

def test_table_row_commercial_figure_does_not_borrow_a_citation_from_the_next_paragraph():
    # A real near-miss found while building this fix: a comparison table's
    # last row has no period before the following prose paragraph's citation.
    table_text = (
        "| Tangerine/EQ Bank | $0 permanently | Ongoing | No (fee applies) | "
        "No-fee digital alternative; no waiver expiry |\n"
        "\n"
        "Under the [FCAC no-cost account commitment]"
        "(https://www.canada.ca/en/financial-consumer-agency/services/industry/laws-regulations/low-cost-no-cost-accounts.html), "
        "eligible newcomers can access $0/month accounts at participating institutions — a protection worth verifying."
    )
    claims = classify_claims(table_text, "canada_newcomer")
    # the table row's OWN "$0" must stay uncovered (it's a commercial claim
    # about ONE specific bank, not verified by the general FCAC eligibility
    # fact) -- the SEPARATE "$0" inside the FCAC sentence itself may be covered.
    table_row_zero_dollar = table_text.index("$0 permanently")
    row_claim = next(c for c in claims if c["start"] == table_row_zero_dollar)
    assert row_claim["fact"] is None, "a table row must never borrow a citation from prose that follows the table"


def test_soften_and_direct_classify_claims_agree_on_the_table_row_case():
    # POINT (b) FOLLOW-UP (2026-07-06): root-caused and closed by this SAME
    # redesign, not a separate fix. Real bug: scripts/soften_claims.py masks
    # each markdown link down to a short placeholder (\x0e0\x0f) BEFORE
    # running its own _find_unsourced check -- with the OLD fixed-char
    # window, this artificially SHRANK the distance from a table cell's
    # figure to its "citation" (a long .gov URL collapses to ~4 chars),
    # so soften's OWN masked-text check saw the FCAC citation as "nearby"
    # and treated the Tangerine/EQ row's "$0 permanently" as covered (never
    # qualified) -- while a later, SEPARATE classify_claims call on the
    # final UNMASKED text (mirroring G-Substance's real re-check) used the
    # full, un-shrunk distance and correctly saw it as uncovered. Real
    # run-5 case: this exact mismatch caused canada_newcomer's retry
    # attempt to fail G-Substance ("1 unsourced figure survived soften")
    # for a claim soften itself had already silently let through.
    # Sentence/block boundaries don't care about character distance at
    # all, so masking can no longer create this mismatch -- verified here
    # by checking BOTH paths agree BEFORE any softening happens.
    import scripts.soften_claims as soften_claims

    table_text = (
        "| Tangerine/EQ Bank | $0 permanently | Ongoing | No (fee applies) | "
        "No-fee digital alternative; no waiver expiry |\n"
        "\n"
        "Under the [FCAC no-cost account commitment]"
        "(https://www.canada.ca/en/financial-consumer-agency/services/industry/laws-regulations/low-cost-no-cost-accounts.html), "
        "eligible newcomers can access $0/month accounts at participating institutions — a protection worth verifying."
    )
    direct = classify_claims(table_text, "canada_newcomer")
    direct_residual_starts = {c["start"] for c in direct if c["fact"] is None}

    masked, originals, _official = soften_claims._mask_links(table_text)
    masked_spans = soften_claims._find_unsourced(masked, originals, "canada_newcomer")
    masked_residual_starts = {s for (s, _e, _a) in masked_spans}

    table_row_zero_dollar = table_text.index("$0 permanently")
    assert table_row_zero_dollar in direct_residual_starts
    assert table_row_zero_dollar in masked_residual_starts, (
        "soften's own masked-text check must agree with a direct check on the "
        "unmasked text -- masking must never shrink a citation into false coverage"
    )


def test_block_span_never_crosses_a_table_row_boundary():
    text = "| A | $500 | B |\n| C | $600 | D |\n"
    pos = text.index("$500")
    lo, hi = _block_span(text, pos)
    assert "$600" not in text[lo:hi]
    assert "$500" in text[lo:hi]


def test_block_span_never_crosses_a_paragraph_boundary():
    text = "First paragraph mentions $100 here without a period\n\nSecond paragraph mentions $200 here."
    pos = text.index("$100")
    lo, hi = _block_span(text, pos)
    assert "$200" not in text[lo:hi]


# ---------------------------------------------------------------- sentence span mechanics

def test_sentence_span_stops_at_a_real_period():
    text = "First sentence ends here. Second sentence has $50 in it."
    idx = text.index("$50")
    lo, hi = _sentence_span(text, idx, idx + 3)
    assert "First sentence" not in text[lo:hi]
    assert "$50" in text[lo:hi]
