"""IMAGE SUBJECT MISMATCH FIX (2026-07-06): user reported a real published-
bound draft (car insurance for foreign drivers/international students,
us_auto vertical) produced a featured image showing "a family gathered in
their living room" -- completely off-topic for a car insurance article.

Root cause: agent_09's featured/supporting image prompts picked a SUBJECT
from a hardcoded, 7-bucket "broad category" dict (topic_context/
topic_scenes, removed by this fix), keyed by simple keyword counting over
the WHOLE article body. A car insurance article and a health insurance
article both landed in the same "insurance" bucket, whose hardcoded visual
was "diverse family protected under symbolic umbrella" -- a health/life
insurance scene, wrongly reused for car insurance. Separately, an
"LLM enhancement" step existed to make prompts "more specific" using the
real title, but NEVER ran in production: main() never wired an
anthropic_api_key/llm_service into the agent's config, so `self.llm_service`
stayed None and the `if self.llm_service:` guard always skipped it --
confirmed dead code, removed entirely (not just left disabled), per the
user's explicit instruction.

Fix: inject the REAL article subject (agent_04's own article_metadata.json
`keyword` field -- exact, structured, no marketing boilerplate) directly
into the prompt, grounded toward a concrete, photographable scene. No LLM
call, no per-topic bucket list to maintain as new verticals are added.
Validated EMPIRICALLY (real Gemini calls, not just reasoned about) on 3
genuinely abstract topics before this landed -- savings, credit-building,
money transfer -- all three produced clearly on-topic, concrete images.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import importlib.util
_spec = importlib.util.spec_from_file_location("agent_09_test", os.path.join(ROOT, "agents/agent_09_image_prompt_generator.py"))
agent_09 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agent_09)

SRC = open(os.path.join(ROOT, "agents/agent_09_image_prompt_generator.py"), encoding="utf-8").read()


def _agent():
    return agent_09.ImagePromptGeneratorAgent({})


# ---------------------------------------------------------------- fallback chain (never empty)

def test_keyword_from_metadata_json_is_preferred():
    meta = {"title": "fallback title"}
    metadata_json = {"keyword": "car insurance for foreign drivers and international students",
                      "title": "Best Car Insurance for Foreign Drivers: Complete Guide for USA Immigrants (2026)"}
    assert agent_09._resolve_subject(meta, metadata_json) == "car insurance for foreign drivers and international students"


def test_falls_back_to_cleaned_metadata_title_when_keyword_missing():
    meta = {"title": "fallback title"}
    metadata_json = {"keyword": "", "title": "Best High-Interest Savings Accounts For International Students: Complete Guide for Canada Immigrants (2026)"}
    subject = agent_09._resolve_subject(meta, metadata_json)
    assert subject == "High-Interest Savings Accounts For International Students"
    assert "Best" not in subject
    assert "Complete Guide" not in subject
    assert "2026" not in subject


def test_falls_back_to_draft_text_title_when_no_metadata_file():
    meta = {"title": "Build Credit as a Newcomer"}
    assert agent_09._resolve_subject(meta, None) == "Build Credit as a Newcomer"


def test_never_returns_an_empty_subject_even_with_nothing_available():
    subject = agent_09._resolve_subject({"title": ""}, None)
    assert subject
    assert subject == "personal finance and banking services"


def test_metadata_json_with_no_keyword_and_no_title_falls_through_to_draft_title():
    meta = {"title": "Send Money Internationally Guide"}
    metadata_json = {"keyword": "", "title": ""}
    assert agent_09._resolve_subject(meta, metadata_json) == "Send Money Internationally Guide"


# ---------------------------------------------------------------- the reported real-world case

def test_car_insurance_prompt_no_longer_mentions_family_or_umbrella():
    # the exact hardcoded visual that caused the reported bug must be gone.
    agent = _agent()
    meta = {"title": "Best Car Insurance for Foreign Drivers", "market": "usa",
            "subject": "car insurance for foreign drivers and international students"}
    featured = agent._generate_featured_prompt(meta)
    supporting = agent._generate_supporting_graphic_prompt(meta)
    for prompt in (featured["prompt"], supporting["prompt"]):
        assert "family" not in prompt.lower()
        assert "umbrella" not in prompt.lower()
        assert "car insurance for foreign drivers and international students" in prompt


def test_car_insurance_and_health_insurance_no_longer_collide_on_the_same_bucket():
    # the ORIGINAL bug: both landed on the identical hardcoded "insurance"
    # visual. Now each gets its own real subject embedded verbatim.
    agent = _agent()
    car_meta = {"title": "x", "market": "usa", "subject": "car insurance for foreign drivers"}
    health_meta = {"title": "x", "market": "usa", "subject": "health insurance for international students"}
    car_prompt = agent._generate_featured_prompt(car_meta)["prompt"]
    health_prompt = agent._generate_featured_prompt(health_meta)["prompt"]
    assert car_prompt != health_prompt
    assert "car insurance for foreign drivers" in car_prompt
    assert "health insurance for international students" in health_prompt


# ---------------------------------------------------------------- content guardrail applies everywhere

def test_content_guardrail_present_in_featured_and_supporting_prompts():
    agent = _agent()
    meta = {"title": "x", "market": "both", "subject": "build credit as a newcomer"}
    for gen in (agent._generate_featured_prompt, agent._generate_supporting_graphic_prompt):
        prompt = gen(meta)["prompt"]
        assert "no text" in prompt.lower()
        assert "no logos" in prompt.lower()
        assert "no numbers" in prompt.lower()
        assert "identifiable real individuals" in prompt.lower()


def test_content_guardrail_constant_is_shared_not_duplicated():
    assert SRC.count("_CONTENT_GUARDRAIL = (") == 1


# ---------------------------------------------------------------- no more hardcoded per-topic buckets

def test_old_hardcoded_topic_buckets_are_gone():
    # scoped to actual dict definitions, not the code comment that
    # deliberately names them to explain what this fix removed and why.
    assert "topic_context = {" not in SRC
    assert "topic_scenes = {" not in SRC
    assert "diverse family protected under symbolic umbrella" not in SRC
    assert "def _infer_topic" not in SRC


def test_all_five_prompt_generators_use_the_real_subject():
    for fn_name in ["_generate_featured_prompt", "_generate_comparison_graphic_prompt",
                     "_generate_checklist_graphic_prompt", "_generate_process_graphic_prompt",
                     "_generate_supporting_graphic_prompt"]:
        fn_src = SRC[SRC.index(f"def {fn_name}("):]
        fn_src = fn_src[:fn_src.index("\n    def _", 10) if "\n    def _" in fn_src[10:] else len(fn_src)]
        assert 'meta["subject"]' in fn_src, f"{fn_name} must read the real subject"


# ---------------------------------------------------------------- dead code removed entirely

def test_llm_enhancement_dead_code_fully_removed():
    assert "llm_service" not in SRC
    assert "_llm_enhance_prompts" not in SRC


# ---------------------------------------------------------------- metadata wiring

def test_run_accepts_and_uses_article_metadata_path():
    assert "article_metadata_path" in SRC
    assert "_resolve_subject(meta, metadata_json)" in SRC


def test_cli_exposes_metadata_argument():
    assert '"--metadata"' in SRC


def test_production_workflow_passes_metadata_path():
    workflow = open(os.path.join(ROOT, ".github/workflows/production_v2.yml"), encoding="utf-8").read()
    assert "--metadata" in workflow
    assert "article_metadata.json" in workflow
