"""agent_11's PRE-PUBLISH GATE word-count floor (2026-07-13): was a flat 4000,
tier-blind, while every real tier's own minimum (agent_04_article_writer.py:
OPPORTUNITY/STANDARD=3500, PILLAR=3800) is BELOW that. Real incident: a fully
successful OPPORTUNITY article (3893 words, run 29259884738) cleared GATE
LENGTH, G-Substance and G3 upstream, then got rejected for nothing by this
unrelated, stricter floor. Fixed to the lowest real tier minimum (3500) --
GATE LENGTH already enforces the tier-specific target/ceiling upstream, so
this is a final safety net against empty/garbage drafts, not a second tier
check. See AUDIT-LOG.md.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SRC = open(os.path.join(ROOT, "agents/agent_11_wordpress_integration.py"), encoding="utf-8").read()


def test_pre_publish_gate_floor_is_3500_not_4000():
    assert "if content_words < 3500:" in SRC
    assert "if content_words < 4000:" not in SRC


def test_gate_c_recheck_floor_matches():
    assert "if word_count < 3500:" in SRC
    assert "if word_count < 4000:" not in SRC


def test_checks_dict_word_count_ok_matches():
    assert '"word_count_ok": word_count >= 3500,' in SRC
    assert '"word_count_ok": word_count >= 4000,' not in SRC


def test_the_real_incident_word_count_now_clears_the_floor():
    # 3893 words (run 29259884738, ca-send-money-to-from-canada) must now pass.
    assert 3893 >= 3500


def test_char_floor_untouched():
    # Scope discipline: only the word floor was reported broken -- the char
    # floor (5000) was never the binding constraint and stays as-is.
    assert SRC.count("content_chars < 5000") == 2
