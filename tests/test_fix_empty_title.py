"""Mini-lot: fix the false GATE_C_FAIL:EMPTY_TITLE. Offline, no network/API.

agent_04 stopped emitting a `title:` frontmatter in Sprint 8, so main()'s pre-flight
regex left `title` empty and the post-run GATE C re-check raised a false EMPTY_TITLE
once Lot 1 let run() succeed (draft 48427 was created but the workflow counted it as
'not produced'). The re-check now uses the values the run report produced.
"""
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


if "aiohttp" not in sys.modules:
    aio = types.ModuleType("aiohttp")
    aio.ClientTimeout = lambda *a, **k: None
    aio.ClientSession = object
    aio.ClientError = Exception
    sys.modules["aiohttp"] = aio
_stub("agents.base_agent", BaseAgent=object)
_stub("services.llm_service", LLMService=object)
_stub("services.storage_service", StorageService=object)
_stub("services.wordpress_service", WordPressService=object)

_spec = importlib.util.spec_from_file_location(
    "agent_11_t", os.path.join(ROOT, "agents/agent_11_wordpress_integration.py"))
agent_11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agent_11)
recheck = agent_11._gate_c_recheck


def test_real_produced_article_passes():
    # The exact 48427 case that used to false-fail: real post_id + real title + long content.
    errors = recheck(48427, "Best Building Us Credit From Zero With Itin: Complete Guide", 32445, 4337)
    assert errors == []


def test_empty_title_is_flagged():
    assert recheck(1, "", 6000, 5000) == ["EMPTY_TITLE"]


def test_whitespace_title_is_flagged():
    assert recheck(1, "   ", 6000, 5000) == ["EMPTY_TITLE"]


def test_missing_post_id_is_flagged():
    assert "NO_POST_ID" in recheck(None, "Real Title", 6000, 5000)


def test_short_content_and_low_words_flagged():
    e = recheck(1, "Real Title", 3000, 2000)
    assert any("CONTENT_TOO_SHORT" in x for x in e) and any("WORD_COUNT_TOO_LOW" in x for x in e)


def test_featured_image_is_not_required():
    # Featured image absence must never appear as a GATE C error (decoupled, Lot 1).
    assert recheck(48427, "Real Title", 6000, 5000) == []
