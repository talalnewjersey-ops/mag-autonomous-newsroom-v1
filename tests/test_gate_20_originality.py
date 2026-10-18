#!/usr/bin/env python3
"""Unit tests for Gate 20 — originality & anti-thin-content validation.

Run: python -m pytest tests/test_gate_20_originality.py -q
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import gate_20_originality as g20  # noqa: E402


def _rich_article(n_paras: int = 8) -> str:
    """Build a long, varied, substantive HTML article that should PASS."""
    topics = [
        "Opening a checking account requires two forms of ID and proof of address in 2024.",
        "Wire transfers to Canada typically cost between 15 and 45 dollars depending on the bank.",
        "Credit scores in the USA range from 300 to 850 and lenders weigh payment history at 35 percent.",
        "Health insurance premiums vary by state; a benchmark silver plan averaged 477 dollars monthly.",
        "Filing taxes as a newcomer may require an ITIN if you are not yet eligible for an SSN.",
        "A secured credit card needs a refundable deposit, often 200 dollars, to establish history.",
        "Driver license rules differ: New Jersey requires a 6-point ID verification process.",
        "Remittance apps settle in 1 to 3 business days and disclose the exchange-rate margin.",
    ]
    paras = []
    for i in range(n_paras):
        t = topics[i % len(topics)]
        paras.append(
            "<h2>Section {0}</h2><p>{1} For example, applicants should compare at least "
            "three providers and review the fee schedule carefully before deciding.</p>"
            "<ul><li>Point A for section {0}</li><li>Point B for section {0}</li></ul>"
            "<p><a href='https://example.gov/{0}'>Official source {0}</a></p>".format(i, t)
        )
    return "".join(paras)


def _thin_article() -> str:
    return "<p>Banking is good. Open an account. It is easy. Banking is good.</p>"


def _repetitive_article() -> str:
    sentence = ("You should open a bank account today because opening a bank account "
                "today is the smart move for opening a bank account today. ")
    return "<p>" + (sentence * 30) + "</p>"


# ---------------------------------------------------------------------------
# Utility-level tests
# ---------------------------------------------------------------------------
def test_strip_html_removes_tags():
    assert g20.strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_effective_word_count_strips_boilerplate():
    text = "<p>Real content here about banking fees.</p> Advertisement Subscribe to our newsletter"
    assert g20.effective_word_count(text) == 6


def test_lexical_diversity_bounds():
    assert g20.lexical_diversity([]) == 1.0
    assert 0.0 < g20.lexical_diversity(["a", "b", "a", "c"]) <= 1.0


def test_internal_repetition_detects_dupes():
    toks = g20.words("the cat sat on the mat " * 5)
    rep = g20.internal_repetition(toks, 4)
    assert rep > 0.0


# ---------------------------------------------------------------------------
# Gate-level behavior tests
# ---------------------------------------------------------------------------
def test_rich_article_passes_block_mode():
    report = g20.evaluate(_rich_article(), mode="block")
    assert report["verdict_raw"] == "PASS", report["failed_checks"]
    assert report["blocks_publication"] is False


def test_thin_article_fails_raw_but_warn_mode_does_not_block():
    report = g20.evaluate(_thin_article(), mode="warn")
    assert report["verdict_raw"] == "FAIL"
    assert report["status_effective"] == "WARN"
    assert report["blocks_publication"] is False


def test_thin_article_blocks_in_block_mode():
    report = g20.evaluate(_thin_article(), mode="block")
    assert report["verdict_raw"] == "FAIL"
    assert report["blocks_publication"] is True


def test_repetitive_article_flags_repetition_or_diversity():
    report = g20.evaluate(_repetitive_article(), mode="warn")
    failed = set(report["failed_checks"])
    assert ("internal_repetition" in failed) or ("lexical_diversity" in failed)


def test_corpus_duplication_detects_near_duplicate():
    original = _rich_article()
    report = g20.evaluate(original, corpus=[original], mode="warn")
    assert report["checks"]["corpus_duplication"]["value"] > \
        g20.THRESHOLDS["max_corpus_duplication"]
    assert "corpus_duplication" in report["failed_checks"]


def test_unique_article_low_corpus_duplication():
    art = _rich_article()
    other = "<p>Completely unrelated text about gardening tomatoes in spring soil beds.</p>" * 5
    report = g20.evaluate(art, corpus=[other], mode="block")
    assert report["checks"]["corpus_duplication"]["pass"] is True


def test_deterministic_repeatable():
    a = g20.evaluate(_rich_article(), mode="warn")
    b = g20.evaluate(_rich_article(), mode="warn")
    assert a == b


def test_warn_is_default_mode():
    report = g20.evaluate(_thin_article())
    assert report["mode"] == "warn"
    assert report["blocks_publication"] is False


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
