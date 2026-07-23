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
