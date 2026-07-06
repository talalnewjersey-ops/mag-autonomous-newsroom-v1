"""PROXIMITY WINDOW 100 -> 150 (2026-07-06): a real false positive on the final
3-vertical control run (us_auto, run 28764042930) -- a sentence citing several
dollar figures before ONE trailing citation had its FIRST figure(s) fall
outside a 100-char window while later figures (closer to the link) stayed
covered, even though the VALUES exactly match engraved Couche 1 facts and the
citation is the correct one.

Two properties are proven here, not just asserted:
  1. 150 is empirically justified: the two real false-positive figures sat
     119 and 134 chars from their own correct citation (measured on the real
     article); 140 was the minimal sufficient value, 150 gives 16 chars of
     margin. Boundary tests cover both sides of the OLD (100) and confirm the
     NEW (150) constant actually in the source.
  2. Widening the window CANNOT launder a divergent/fabricated value: the
     window only controls whether the correct source_url is found nearby --
     `covering_fact` separately and unconditionally requires the claim's own
     numeric token to exactly equal one of that fact's engraved tokens. A
     wrong value next to the right link stays uncovered at ANY window size.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents._fact_coverage import (
    PROXIMITY_WINDOW_CHARS, classify_claims, _NUM_RE, _default_url_finder, covering_fact,
)

CFPB_RETENTION = "https://www.consumerfinance.gov/ask-cfpb/how-long-does-negative-information-remain-on-my-credit-report-en-323/"


def _classify_with_window(text, vertical, window):
    """Same algorithm as classify_claims, with an injectable window -- used
    only to demonstrate the property across window sizes; production code
    always uses the single PROXIMITY_WINDOW_CHARS constant."""
    url_finder = _default_url_finder(text)
    out = []
    for m in _NUM_RE.finditer(text):
        lo, hi = max(0, m.start() - window), min(len(text), m.end() + window)
        out.append({"start": m.start(), "end": m.end(),
                     "fact": covering_fact(m.group(0), url_finder(lo, hi), vertical)})
    return out


def test_constant_is_150_not_100():
    assert PROXIMITY_WINDOW_CHARS == 150


# ---------------- real false-positive case: multi-figure sentence, one trailing citation ----------------

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


def test_real_case_uncovered_at_old_100_window():
    claims = _classify_with_window(TEXAS_LINE, "us_auto", 100)
    residual = [TEXAS_LINE[c["start"]:c["end"]] for c in claims if c["fact"] is None]
    assert "$30,000" in residual, "the real false positive must reproduce at the OLD window"


def test_real_case_covered_at_new_150_window():
    claims = classify_claims(TEXAS_LINE, "us_auto")  # uses the real PROXIMITY_WINDOW_CHARS
    residual = [TEXAS_LINE[c["start"]:c["end"]] for c in claims if c["fact"] is None]
    assert residual == [], f"Texas $30,000 must now be covered at the real (150) window, still uncovered: {residual}"


def test_real_case_new_york_covered_at_150():
    # NB: in ISOLATION (this one line only, no preceding article context), NY's
    # own $25,000 sits far enough from ITS OWN citation to stay uncovered even
    # at 150 -- that specific figure was only covered in the real run via a
    # DIFFERENT, earlier occurrence elsewhere in the full article. The actual
    # false positive this fix targets is $10,000 -- that is what must clear.
    claims = classify_claims(NY_LINE, "us_auto")  # uses the real PROXIMITY_WINDOW_CHARS
    residual = [NY_LINE[c["start"]:c["end"]] for c in claims if c["fact"] is None]
    assert "$10,000" not in residual, f"NY $10,000 must now be covered at the real (150) window: {residual}"


def test_140_is_the_minimal_sufficient_value_measured_on_real_data():
    # documents the exact empirical minimum this session established for the
    # real false-positive figure ($10,000 -- see note above re: $25,000)
    claims_130 = _classify_with_window(NY_LINE, "us_auto", 130)
    claims_140 = _classify_with_window(NY_LINE, "us_auto", 140)
    residual_130 = [NY_LINE[c["start"]:c["end"]] for c in claims_130 if c["fact"] is None]
    residual_140 = [NY_LINE[c["start"]:c["end"]] for c in claims_140 if c["fact"] is None]
    assert "$10,000" in residual_130, "130 must NOT yet be sufficient (documents the real boundary)"
    assert "$10,000" not in residual_140, "140 must already be sufficient (the real empirical minimum)"


# ---------------- synthetic boundary tests: exactly at the 150-char edge ----------------

def _text_with_exact_gap(target_distance):
    """Build "$500" + filler + "[FTC](url)" so the distance from the number's
    own end position to the BARE URL's own start position (what _URL_IN
    actually matches -- just the "https://..." substring, NOT the enclosing
    "[FTC](" markdown prefix) is EXACTLY `target_distance` -- computed
    programmatically so the boundary tests land precisely on the intended
    edge, not on a guessed offset."""
    number = "$500"
    link_prefix = "[FTC]("  # _URL_IN matches only the bare URL after this
    filler = "x" * (target_distance - len(link_prefix))
    text = number + filler + link_prefix + _FTC_URL() + ")"
    url_start = len(number) + len(filler) + len(link_prefix)
    return text, len(number), url_start


def test_synthetic_boundary_just_inside_150_is_covered():
    # distance from the number's end to the bare URL's start is exactly 149 < 150.
    text, num_end, url_start = _text_with_exact_gap(149)
    assert url_start - num_end == 149
    claims = classify_claims(text, "_test_boundary_vertical")
    residual = [text[c["start"]:c["end"]] for c in claims if c["fact"] is None]
    assert "$500" not in residual


def test_synthetic_boundary_just_outside_150_is_not_covered():
    # distance from the number's end to the bare URL's start is exactly 151 > 150.
    text, num_end, url_start = _text_with_exact_gap(151)
    assert url_start - num_end == 151
    claims = classify_claims(text, "_test_boundary_vertical")
    residual = [text[c["start"]:c["end"]] for c in claims if c["fact"] is None]
    assert "$500" in residual


def _FTC_URL():
    return "https://www.ftc.gov/test-boundary-fact"


# monkeypatch-free fixture vertical: inject a throwaway fact via VERTICAL_FACTS
# for the boundary tests above (isolated key, never collides with real verticals).
import agents._fact_coverage as _fc  # noqa: E402
_fc.VERTICAL_FACTS["_test_boundary_vertical"] = [
    {"claim": "test boundary fact", "value": "$500", "source_url": _FTC_URL(), "status": "STABLE"},
]


# ---------------- adversarial: window size can NEVER launder a divergent value ----------------

def test_divergent_value_next_to_correct_link_stays_uncovered_at_150():
    # "10 years" IS a real engraved us_credit value (a DIFFERENT fact/URL) --
    # sitting next to the RETENTION link (whose own value is only 7/45) must
    # still be rejected at the NEW window, exactly as at the old one.
    text = f"Negative information can stay on file for 10 years ([CFPB]({CFPB_RETENTION}))."
    claims = classify_claims(text, "us_credit")
    residual = [c for c in claims if c["fact"] is None]
    assert len(residual) == 1, "the divergent value must still be caught, window widening changes nothing here"


def test_divergent_value_stays_uncovered_at_absurdly_large_window():
    # Proves the property STRUCTURALLY, not just at 150: covering_fact requires
    # exact numeric-token equality to the SPECIFIC fact tied to that URL --
    # independent of how wide the window is.
    text = f"Negative information can stay on file for 10 years ([CFPB]({CFPB_RETENTION}))."
    claims = _classify_with_window(text, "us_credit", 999999)
    residual = [c for c in claims if c["fact"] is None]
    assert len(residual) == 1
