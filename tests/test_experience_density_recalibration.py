"""Experience score recalibration: absolute match count -> density per 1000
words (2026-07-11, follow-up to the agent_06/agent_12 EEAT unification).

`experience_score = min(100, experience_count * 5)` (needing 20 absolute
matches for 100/100) was pure scaffolding: `git log -S"experience_count * 5"`
shows exactly ONE commit ever touched it (8d844d2, the agent's original
"add QA agent" commit, no calibration rationale). None of the 5 subsequent
EEAT fixes (#67, #68, #74, #75, the unification) ever revisited it. It was
also structurally wrong for THIS pipeline specifically: this session moved
the per-tier word-count ceiling/target twice (#79, #81) -- every time that
budget moves, a fixed match-COUNT threshold silently gets easier or harder
to hit for reasons that have nothing to do with real experience-signal
density. A density stays comparable across OPPORTUNITY/STANDARD/PILLAR and
survives future word-budget recalibrations without a matching threshold
change.

Real benchmark (2026-07-11) -- see agents/_eeat_scoring.py's module
docstring for the full table and sourcing. 5 independent samples: 2 of our
own published, previously-audited articles (real HTML fetched live) and 3
Bankrate competitor articles (NerdWallet returned HTTP 403 to every fetch,
bot-blocked). 4 of 5 cluster well under a flat "20 matches" bar regardless
of length; the outlier is an atypically long listicle ~2x our own PILLAR
ceiling. Both of OUR OWN best-real-content samples independently converge
on ~4.0-4.1 matches per 1000 words -- the calibration anchor locked in here:
4.0 matches/1000w = 100/100, linear below that, capped (not rewarded beyond)
100 above it.

Offline: no network, no API key -- the benchmark numbers themselves are
hardcoded here from the real, already-completed fetch (see AUDIT-LOG.md and
agents/_eeat_scoring.py for the sourcing), not re-fetched by this test.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents._eeat_scoring import audit_eeat, EXPERIENCE_DENSITY_CALIBRATION_PER_1000_WORDS


def _content_with_n_experience_matches(n, total_words):
    """Synthetic content with EXACTLY n experience-pattern matches (using the
    cheapest, unambiguous pattern -- "example") padded to total_words with
    filler that matches none of the 5 experience_patterns groups."""
    matches_text = " ".join(["example"] * n)  # each "example" is its own match
    match_word_count = n
    filler_needed = max(0, total_words - match_word_count)
    filler = " ".join(["lorem"] * filler_needed)
    return f"{matches_text} {filler}"


# ---------------------------------------------------------------- calibration anchor

def test_calibration_constant_is_four_per_thousand_words():
    assert EXPERIENCE_DENSITY_CALIBRATION_PER_1000_WORDS == 4.0


def test_density_at_calibration_point_scores_exactly_100():
    # 4 matches per 1000 words, at various lengths -- density-based, so all
    # of these must score identically regardless of absolute word count.
    for words in (1000, 2000, 4200):
        n = round(4.0 * words / 1000)
        content = _content_with_n_experience_matches(n, words)
        checks = audit_eeat(content, word_count=words)
        assert checks["experience_score"] == 100.0, f"failed at words={words}, n={n}"


def test_density_above_calibration_point_is_capped_not_rewarded():
    content = _content_with_n_experience_matches(40, 2000)  # 20/1000w, 5x the anchor
    checks = audit_eeat(content, word_count=2000)
    assert checks["experience_score"] == 100.0  # capped, not >100


def test_density_at_half_calibration_scores_fifty():
    content = _content_with_n_experience_matches(8, 4000)  # 2.0/1000w = half of 4.0
    checks = audit_eeat(content, word_count=4000)
    assert checks["experience_score"] == 50.0


def test_zero_matches_scores_zero():
    checks = audit_eeat("lorem " * 500, word_count=500)
    assert checks["experience_signals"] == 0
    assert checks["experience_score"] == 0.0


# ---------------------------------------------------------------- word_count defaulting

def test_word_count_defaults_to_len_split_when_not_supplied():
    content = _content_with_n_experience_matches(4, 1000)
    with_explicit = audit_eeat(content, word_count=len(content.split()))
    without_explicit = audit_eeat(content)  # word_count=None -> derives len(content.split())
    assert with_explicit["experience_score"] == without_explicit["experience_score"]


# ---------------------------------------------------------------- the tier-independence this was built for

def test_density_gives_the_same_score_across_different_tier_word_budgets():
    # the whole point: an article hitting the SAME density scores identically
    # whether it's an OPPORTUNITY (~4000w) or PILLAR (~4500w) tier draft --
    # unlike the old absolute count, which needed 20 matches regardless of
    # the tier's own (different) word budget. Word counts chosen to divide
    # evenly by the 4.0/1000w anchor (integer match counts can't always hit
    # an arbitrary word count's exact density -- see the two isolated tests
    # above for that rounding-granularity edge case).
    opportunity_words, pillar_words = 4000, 4500
    opportunity_content = _content_with_n_experience_matches(
        round(4.0 * opportunity_words / 1000), opportunity_words)
    pillar_content = _content_with_n_experience_matches(
        round(4.0 * pillar_words / 1000), pillar_words)
    opp_score = audit_eeat(opportunity_content, word_count=opportunity_words)["experience_score"]
    pillar_score = audit_eeat(pillar_content, word_count=pillar_words)["experience_score"]
    assert opp_score == pillar_score == 100.0


# ---------------------------------------------------------------- real benchmark regression locks
# Hardcoded real counts from the actual 2026-07-11 fetch (see agents/_eeat_scoring.py
# module docstring for sourcing) -- proves the formula reproduces the exact scores
# reported to the user, not just a synthetic sanity check.

def test_real_benchmark_our_best_article_48384_scores_100():
    # 17 matches / 4146 words = 4.10/1000w
    content = _content_with_n_experience_matches(17, 4146)
    checks = audit_eeat(content, word_count=4146)
    assert checks["experience_density_per_1000w"] == 4.1
    assert checks["experience_score"] == 100.0


def test_real_benchmark_witness_run9_article1_scores_59():
    # 10 matches / 4235 words = 2.36/1000w -- the actual real-generation number
    # reported to the user (EEAT 83.5, overall 93.4 with this fix applied).
    content = _content_with_n_experience_matches(10, 4235)
    checks = audit_eeat(content, word_count=4235)
    assert checks["experience_density_per_1000w"] == 2.36
    assert checks["experience_score"] == 59.0


def test_real_benchmark_competitor_low_density_sample_scores_under_fifty():
    # Bankrate "undocumented immigrants credit cards": 5 matches / 2847 words = 1.76/1000w
    content = _content_with_n_experience_matches(5, 2847)
    checks = audit_eeat(content, word_count=2847)
    assert checks["experience_density_per_1000w"] == 1.76
    assert checks["experience_score"] == 43.9


def test_real_benchmark_competitor_listicle_normalizes_to_full_score():
    # Bankrate "best secured credit cards" listicle: 39 matches / 8847 words = 4.41/1000w
    # -- the one sample that looked like it needed "20 matches" under the old
    # absolute-count rule, but is really just an atypically long page; density
    # correctly recognizes it as equivalent-quality content, not needing MORE
    # signal just because it's longer.
    content = _content_with_n_experience_matches(39, 8847)
    checks = audit_eeat(content, word_count=8847)
    assert checks["experience_density_per_1000w"] == 4.41
    assert checks["experience_score"] == 100.0
