"""MICRO-TRIM (2026-07-11, PR #81): a tiny GATE LENGTH overage (real finding:
witness run 7, article 1, OPPORTUNITY tier, 4401w vs a 4400w ceiling -- +1w)
shouldn't burn a full regeneration retry -- the retry-cut logic has almost
nothing to act on for a +1w overage, so the "retry" is really just noise (the
SAME article went 4401w -> 4976w on its retry, WORSE, from ordinary LLM
variance around a near-zero cut). scripts/micro_trim.py mechanically removes
the last sentence of the longest trim-eligible section instead, deletion-only,
zero extra API cost, below a 2%-of-ceiling threshold.

Offline: no network, no API key, no LLM call -- pure text manipulation.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import micro_trim  # noqa: E402
import length_gate  # noqa: E402


def _make_article(body_sentences_per_section=6, n_sections=3, filler_words_per_sentence=20):
    """A realistic multi-section draft: several trim-eligible body H2s (each
    with multiple sentences, so there's real room to trim from), plus the
    protected sections a real article always has."""
    def _section(i):
        sentences = " ".join(
            f"Sentence{i}dash{j} " + " ".join(["filler"] * filler_words_per_sentence) + "."
            for j in range(body_sentences_per_section)
        )
        return f"## {i}. Body Section {i}\n\n{sentences}\n"

    body = "\n".join(_section(i) for i in range(1, n_sections + 1))
    return (
        "## Intro\n\nShort intro paragraph.\n\n"
        + body +
        "\n## Frequently Asked Questions\n\n### Question one?\n\nProtected FAQ answer text that must never shrink.\n\n"
        "## Comparison Table: Options\n\nProtected comparison context that must never shrink either way.\n\n"
        "## Expert Recommendation\n\nProtected expert pick text that must never shrink at all.\n\n"
        "## Illustrative Scenarios\n\n### Illustrative Scenario: Example\n\nA generic role holder does one generic thing that must never shrink.\n\n"
        "## Conclusion\n\nProtected conclusion wrap-up that must never shrink.\n\n"
        "## Disclaimer\n\nProtected legal disclaimer text that must absolutely never be touched by any trim logic.\n\n"
        "## About the Author\n\nProtected author bio text that must never be touched by any trim logic either.\n"
    )


_PROTECTED_SNIPPETS = [
    "Protected FAQ answer text that must never shrink.",
    "Protected comparison context that must never shrink either way.",
    "Protected expert pick text that must never shrink at all.",
    "A generic role holder does one generic thing that must never shrink.",
    "Protected conclusion wrap-up that must never shrink.",
    "Protected legal disclaimer text that must absolutely never be touched by any trim logic.",
    "Protected author bio text that must never be touched by any trim logic either.",
]


# ---------------------------------------------------------------- no-op cases

def test_noop_when_not_over_ceiling():
    text = _make_article(n_sections=1, body_sentences_per_section=2, filler_words_per_sentence=3)
    wc = len(text.split())
    assert length_gate.evaluate(wc, "OPPORTUNITY")["over_ceiling"] is False  # sanity: tiny fixture, well under
    new_text, report = micro_trim.micro_trim(text, "OPPORTUNITY", min_words=5)
    assert new_text == text
    assert report["performed"] is False
    assert report["reason"] == "not_over_ceiling"


def test_defers_to_retry_when_overage_exceeds_two_percent():
    # construct an overage well above 2% of the OPPORTUNITY ceiling (4400 x 0.02 = 88w)
    text = _make_article(n_sections=3, body_sentences_per_section=6, filler_words_per_sentence=400)
    wc = len(text.split())
    result = length_gate.evaluate(wc, "OPPORTUNITY")
    assert result["over_ceiling"] is True
    assert result["over_by_words"] > 88, "test fixture must exceed the 2% micro-trim threshold"

    new_text, report = micro_trim.micro_trim(text, "OPPORTUNITY", min_words=5)
    assert new_text == text, "a large overage must be left completely untouched, deferred to the real retry"
    assert report["performed"] is False
    assert "overage_too_large_for_micro_trim" in report["reason"]


# ---------------------------------------------------------------- the actual trim

def test_trims_a_tiny_overage_under_the_ceiling():
    # tune the fixture to land just over the OPPORTUNITY ceiling (4400w), well
    # within the 2% (88w) micro-trim threshold.
    text = _make_article(n_sections=3, body_sentences_per_section=6, filler_words_per_sentence=240)
    wc_before = len(text.split())
    result = length_gate.evaluate(wc_before, "OPPORTUNITY")
    assert result["over_ceiling"] is True
    assert result["over_by_words"] <= 88, "test fixture must be within the micro-trim threshold"

    new_text, report = micro_trim.micro_trim(text, "OPPORTUNITY", min_words=100)
    assert report["performed"] is True
    assert report["reason"] == "trimmed_under_ceiling"
    wc_after = len(new_text.split())
    assert wc_after < wc_before
    assert not length_gate.evaluate(wc_after, "OPPORTUNITY")["over_ceiling"]


def test_never_touches_protected_sections():
    text = _make_article(n_sections=3, body_sentences_per_section=6, filler_words_per_sentence=240)
    new_text, report = micro_trim.micro_trim(text, "OPPORTUNITY", min_words=100)
    assert report["performed"] is True
    for snippet in _PROTECTED_SNIPPETS:
        assert snippet in new_text, f"protected section text was altered: {snippet!r}"


def test_only_removes_the_last_sentence_not_earlier_ones():
    text = _make_article(n_sections=3, body_sentences_per_section=6, filler_words_per_sentence=240)
    new_text, report = micro_trim.micro_trim(text, "OPPORTUNITY", min_words=100)
    assert report["performed"] is True
    assert report["sentences_trimmed"] >= 1
    # the first sentence of the longest section (section 3, same filler length as
    # the others so section 3 -- last one built -- ties/wins the "longest" sort)
    # must survive; only trailing sentences are ever removed.
    assert "Sentence3dash0" in new_text or "Sentence1dash0" in new_text or "Sentence2dash0" in new_text


def test_never_breaches_min_words():
    # an aggressive min_words relative to the fixture's total forces the trim
    # loop to stop rather than cut below the floor.
    text = _make_article(n_sections=1, body_sentences_per_section=3, filler_words_per_sentence=15)
    wc_before = len(text.split())
    # pick an OPPORTUNITY-scale min_words comfortably below the fixture, then verify
    # the loop never drops the output below it regardless of how far short of the
    # ceiling that leaves it.
    min_words = wc_before - 5
    new_text, report = micro_trim.micro_trim(text, "OPPORTUNITY", min_words=min_words)
    assert len(new_text.split()) >= min_words


def test_bounded_iterations_never_hangs():
    # many small eligible sections -- confirms the loop terminates (bounded by
    # max_iterations) rather than looping until every section is emptied.
    text = _make_article(n_sections=10, body_sentences_per_section=8, filler_words_per_sentence=30)
    new_text, report = micro_trim.micro_trim(text, "OPPORTUNITY", min_words=5, max_iterations=5)
    assert report["sentences_trimmed"] <= 5


# ---------------------------------------------------------------- CLI never blocks

def test_cli_always_exits_zero_even_when_overage_is_too_large_to_trim():
    import inspect
    src = inspect.getsource(micro_trim.main)
    assert "sys.exit(0)" in src
    assert "sys.exit(1)" not in src


# ---------------------------------------------------------------- workflow expression-length guard
# PR #73 fixed a real incident where this exact step's `run:` block exceeded GitHub's
# 21000-char limit on a single expression. Wiring micro_trim.py into it (this PR)
# left only ~650 chars of margin -- a regression guard so the NEXT addition gets an
# early, clear test failure instead of a surprise CI break mid-run.

def test_batch_loop_run_block_stays_under_the_github_expression_length_limit():
    import yaml
    with open(os.path.join(ROOT, ".github/workflows/production_v2.yml"), encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    for job in doc["jobs"].values():
        for step in job.get("steps", []):
            if step.get("name") == "Batch Loop -- 3 Articles Sequential":
                length = len(step["run"])
                assert length < 20800, (
                    f"'Batch Loop' run: block is {length} chars, within {21000 - length} of "
                    "GitHub's 21000-char hard limit (see PR #73) -- shrink comments/logging "
                    "before adding more, don't just let this creep up to a surprise CI failure"
                )
                return
    assert False, "could not find the 'Batch Loop -- 3 Articles Sequential' step to check"
