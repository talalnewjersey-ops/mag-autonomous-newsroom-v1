"""2026-07-11 fix: agent_12's word_count silently used a STALE value from
article_metadata.json instead of the actual content being scored.

Found on a real, fully-passing witness run (draft 48640, run 29137518698):
content_details.word_count (freshly recomputed) was 4350 -- correctly within
the tier's word-count tolerance, content_check.score=100 -- but
seo_details.word_count was 4526, taken from article_metadata.json (written
ONCE by agent_04 right after the initial LLM generation, never refreshed by
the soften/polish/normalize/scenario steps that run afterward and change the
draft's real length). The stale 4526 wrongly failed word_count_ok, capping
seo_score at 85 instead of 100 -- overall_score landed at 90.5 instead of
~96.5, entirely due to this one stale field.

Root cause, precisely: _load_article_data used to (1) set word_count fresh
from content via data.setdefault(...), THEN (2) call data.update(metadata),
which silently overwrote the fresh value with metadata's stale one -- last
write wins, and metadata was written last.

Fix: word_count is now recomputed from `content` LAST, after every merge,
unconditionally overriding anything metadata/WP-report/caller set. The
content being scored is the single source of truth for its own word count --
this closes the whole CLASS of "stale metadata word_count" bugs, not just
this one instance (metadata.word_count itself is left untouched -- other
code may still read it for other purposes; only agent_12's own audit no
longer trusts it over the real content).

Offline, no network, no API key -- same harness pattern as
tests/test_sprint10_anti_hallucination.py.
"""
import asyncio
import importlib.util
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _stub(name, **attrs):
    if name not in sys.modules:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m


_stub("services.llm_service", LLMService=object)
_stub("services.storage_service", StorageService=object)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


agent_12_mod = _load("agents/agent_12_quality_assurance.py", "agent_12_fresh_wc")
Agent = agent_12_mod.QualityAssuranceAgent


def _agent():
    return Agent.__new__(Agent)


def _run(coro):
    return asyncio.run(coro)


def test_word_count_is_recomputed_fresh_when_context_supplies_a_stale_one():
    # exact real-run shape: caller (main()'s CLI) already put a stale
    # metadata-sourced word_count in the context BEFORE _load_article_data
    # even runs -- must not survive.
    content = "word " * 4350  # 4350 real words
    data = _run(_agent()._load_article_data({
        "article_content": content,
        "word_count": 4526,  # stale value the old code would have kept
    }))
    assert data["word_count"] == 4350


def test_word_count_survives_a_metadata_json_overwrite_attempt(tmp_path, monkeypatch):
    # simulates the SECOND staleness source: _load_article_data's own
    # metadata.json read/merge, which used to clobber the fresh value too.
    monkeypatch.chdir(tmp_path)
    os.makedirs("output/agent_04", exist_ok=True)
    import json
    with open("output/agent_04/article_metadata.json", "w") as f:
        json.dump({"word_count": 9999, "tier": "OPPORTUNITY"}, f)

    content = "word " * 4350
    data = _run(_agent()._load_article_data({"article_content": content}))
    assert data["word_count"] == 4350  # not 9999
    assert data["tier"] == "OPPORTUNITY"  # other metadata fields still merge normally


def test_real_48640_shaped_case_seo_score_reaches_100_not_85():
    # Reproduces the real numbers: fixed costs aside, only word_count_ok
    # differs between the stale (4526, fails) and fresh (4350, passes) reads.
    a = _agent()
    sections = "".join(f"\n## Section {i}\n\n### Sub {i}.1\n\n### Sub {i}.2\nword " for i in range(1, 6))
    links = "".join(f"[Link {i}](https://example.com/{i}) " for i in range(1, 4))
    table = "\n".join(f"| Row {i} | Val {i} |" for i in range(1, 7))
    filler_words_needed = 3888  # brings the total to ~4000, inside tier tolerance
    content = ("## Overview\nkeyword phrase in title text. " + links + "\n\n" + sections +
               "\n\n" + table + "\n\n## Frequently Asked Questions\n\n### Q?\n\nA.\n\n" +
               "word " * filler_words_needed)
    stale_ctx = {"article_content": content, "word_count": 4526,
                 "title": "keyword phrase", "keyword": "keyword phrase",
                 "meta_description": "desc", "article_type": "OPPORTUNITY"}
    data = _run(a._load_article_data(stale_ctx))
    seo_check = _run(a._audit_seo(data))
    assert data["word_count"] != 4526
    assert seo_check["word_count_ok"] is True
    assert a._calculate_seo_score(seo_check) == 100


def test_no_content_leaves_any_caller_supplied_word_count_untouched():
    # when there's genuinely no content to recompute from, don't invent one --
    # whatever the caller/metadata supplied is all there is.
    data = _run(_agent()._load_article_data({"word_count": 4526}))
    assert data["word_count"] == 4526
