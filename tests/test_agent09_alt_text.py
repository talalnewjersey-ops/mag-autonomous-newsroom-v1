"""Regression lock: agent_09's alt_text fields must read like natural image
descriptions, not internal prompt-generation labels ("Comparison guide: X
options for newcomers", "Featured: {title}") -- confirmed leaking into
WordPress media alt="" on at least 4/5 live published articles checked
(2026-07-23), even though the visible-figcaption version of this bug was
already fixed (Sprint 8/LEVIER C, 2026-07-05). Fixed at the source here;
agents/_placeholder_scan.py's scan_alt_texts() (GATE D) is the independent
safety net if this ever regresses.

Offline: no network, no API key.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.agent_09_image_prompt_generator import ImagePromptGeneratorAgent
from agents._placeholder_scan import scan_alt_texts


def _agent():
    return ImagePromptGeneratorAgent({"image_provider": "gemini"})


def _meta(subject, market="usa", title="Best Renters Insurance For Newcomers"):
    return {"title": title, "market": market, "subject": subject}


def test_none_of_the_five_alt_texts_trip_gate_d():
    a = _agent()
    meta = _meta("renters insurance")
    alt_texts = [
        a._generate_featured_prompt(meta)["alt_text"],
        a._generate_comparison_graphic_prompt(meta, "")["alt_text"],
        a._generate_checklist_graphic_prompt(meta, [])["alt_text"],
        a._generate_process_graphic_prompt(meta, [])["alt_text"],
        a._generate_supporting_graphic_prompt(meta)["alt_text"],
    ]
    assert not scan_alt_texts(alt_texts), alt_texts


def test_process_graphic_no_longer_duplicates_how_to():
    # Real bug (post 48870): subject already starting with "how to" produced
    # "How to how to rent an apartment...: step-by-step process for newcomers"
    # because the old alt_text unconditionally prefixed another "How to".
    a = _agent()
    meta = _meta("how to rent an apartment without SSN or credit")
    alt = a._generate_process_graphic_prompt(meta, [])["alt_text"]
    assert "how to how to" not in alt.lower()


def test_featured_alt_text_is_not_a_bare_title_prefix():
    a = _agent()
    meta = _meta("renters insurance", title="Best Renters Insurance: Complete Guide (2026)")
    alt = a._generate_featured_prompt(meta)["alt_text"]
    assert not alt.startswith("Featured:")


# ---------------- question-form subject phrasing (2026-07-23, post 48982) ----------------
# Real bug found reviewing post 48982's alt_text by eye: `subject` is a free-form
# keyword and can itself be a literal yes/no question ("does my home country
# credit score transfer"), which the OLD "Comparison chart of {subject} options
# for newcomers" template grammatically inserted as a preposition's object --
# "Comparison chart of does my home country credit score transfer options for
# newcomers" is broken English even though it's not a GATE D-detectable scar
# (no dropped word, just bad grammar). The em-dash caption format
# ("{subject} -- comparison chart for newcomers") sidesteps this for any
# subject shape, so these check the exact real subject strings from the two
# dry-run articles a human reviewed (posts 48972/48982), not just the
# GATE D pattern check above.

QUESTION_SUBJECT = "does my home country credit score transfer"
GERUND_SUBJECT = "getting a drivers license as a newcomer"


def test_question_form_subject_reads_naturally_as_a_caption():
    a = _agent()
    meta = _meta(QUESTION_SUBJECT, market="usa")
    alt = a._generate_comparison_graphic_prompt(meta, "")["alt_text"]
    assert alt == "Does my home country credit score transfer -- comparison chart for newcomers"
    # the broken shape must be gone, not just replaced by a different broken one
    assert "chart of does" not in alt.lower()


def test_all_five_alt_texts_use_the_subject_led_caption_format_for_both_real_subjects():
    a = _agent()
    for subject in (QUESTION_SUBJECT, GERUND_SUBJECT):
        meta = _meta(subject, market="usa")
        alt_texts = [
            a._generate_featured_prompt(meta)["alt_text"],
            a._generate_comparison_graphic_prompt(meta, "")["alt_text"],
            a._generate_checklist_graphic_prompt(meta, [])["alt_text"],
            a._generate_process_graphic_prompt(meta, [])["alt_text"],
            a._generate_supporting_graphic_prompt(meta)["alt_text"],
        ]
        expected_lead = subject[:1].upper() + subject[1:]
        for alt in alt_texts:
            assert alt.startswith(expected_lead + " -- "), alt
        assert not scan_alt_texts(alt_texts), alt_texts
