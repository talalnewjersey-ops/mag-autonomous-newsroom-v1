"""meta_description/keyword bug (2026-07-11, found in witness run 9's wordpress_
report.json: `"meta_description": "Guide to  for expats."` -- missing keyword,
double space).

Root cause, verified against the real code path (not guessed): main()'s
pre-flight extraction (`agent_11_wordpress_integration.py`) reads `title`/
`keyword` from a `title:`/`primary_keyword:` YAML-style frontmatter regex
against the raw article markdown file. agent_04 stopped emitting that
frontmatter entirely in Sprint 8 (2026-07-05) -- confirmed separately for
`title` (see this file's own 2026-07-06 comment: "agent_04 no longer emits a
`title:` frontmatter"), and a matching fix was applied for `title`
(`title = result.get("title") or title`, pulling the real value from run()'s
own wp_report) -- but the SAME fix was never applied to `keyword`. `keyword`
stayed permanently "" from the dead regex, and the report's own hardcoded
`f"Guide to {keyword} for expats."` then baked that empty string in on
EVERY run, not just this one -- reproduced identically on run 10 bis's
article 1 (see AUDIT-LOG.md).

Note this bug was CONFINED to agent_11's own wordpress_report.json (the
artifact our tooling reads) -- the actual WordPress post's Rank Math/Yoast
meta fields are set separately, inside run()'s _set_seo_metadata(), from
article_data (which correctly loads meta_description/keyword from agent_03's
outline via _load_article_data()) and was never affected by this regex.

Offline: no network. WordPressIntegrationAgent.run() is replaced with a
deterministic stand-in returning the exact shape the real class already
returns (title/keyword/seo_title/meta_description sourced from
_load_article_data(), per that method's own real behavior) -- proving
main()'s report-building threads those fields through instead of
re-deriving keyword from the dead frontmatter regex.
"""
import asyncio
import importlib.util
import json
import os
import sys
import types
import unittest.mock as mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SRC_11 = open(os.path.join(ROOT, "agents/agent_11_wordpress_integration.py"), encoding="utf-8").read()


def _load_agent11():
    spec = importlib.util.spec_from_file_location(
        "agent_11_meta_fix_test", os.path.join(ROOT, "agents/agent_11_wordpress_integration.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_services_modules():
    # Other test files' module-level sys.modules stubs for these services
    # (order-dependent under the full suite) can leak in and replace the real
    # classes with bare stand-ins that reject constructor args -- same class
    # of collision documented in test_wordpress_service_challenge_retry.py.
    # main() only ever CONSTRUCTS these (never calls them, since run() itself
    # is mocked below), so a permissive no-op stand-in is enough here.
    wp_mod = types.ModuleType("services.wordpress_service")
    class _FakeWordPressService:
        def __init__(self, *a, **k): pass
    wp_mod.WordPressService = _FakeWordPressService

    llm_mod = types.ModuleType("services.llm_service")
    class _FakeLLMService:
        def __init__(self, *a, **k): pass
    llm_mod.LLMService = _FakeLLMService

    storage_mod = types.ModuleType("services.storage_service")
    class _FakeStorageService:
        def __init__(self, *a, **k): pass
    storage_mod.StorageService = _FakeStorageService

    return {
        "services.wordpress_service": wp_mod,
        "services.llm_service": llm_mod,
        "services.storage_service": storage_mod,
    }


# ---------------------------------------------------------------- source-level wiring

def test_main_pulls_keyword_from_run_result_not_only_title():
    assert 'keyword = result.get("keyword") or keyword' in SRC_11


def test_main_uses_real_meta_description_from_run_result():
    assert 'meta_description = result.get("meta_description") or' in SRC_11
    # The report dict must use the threaded variable, not re-derive inline.
    assert '"meta_description": meta_description,' in SRC_11
    assert '"meta_description": f"Guide to {keyword} for expats.",' not in SRC_11


def test_seo_title_also_threaded_from_run_result():
    assert 'seo_title = result.get("seo_title") or title' in SRC_11
    assert '"seo_title": seo_title,' in SRC_11


# ---------------------------------------------------------------- end-to-end: the real bug scenario

def test_report_never_contains_the_broken_meta_description_end_to_end(tmp_path):
    agent_11 = _load_agent11()

    # Real Sprint-8 shape: no title:/primary_keyword: frontmatter at all.
    article_path = tmp_path / "article_draft.md"
    article_path.write_text("## Best Car Insurance For Foreign Drivers\n\nBody text.\n", encoding="utf-8")

    output_path = tmp_path / "wordpress_report.json"

    # Exactly what the REAL WordPressIntegrationAgent.run() returns (see its
    # own wp_report dict): keyword/meta_description sourced from the outline,
    # never empty in the real success path.
    real_shaped_result = {
        "title": "Best Car Insurance For Foreign Drivers And International Students",
        "keyword": "car insurance for foreign drivers and international students",
        "post_id": 48682,
        "post_url": "https://moneyabroadguide.com/?p=48682",
        "post_status": "draft",
        "uploaded_images": [],
        "image_count": 0,
        "featured_image_id": None,
        "word_count": 4318,
        "content_chars": 31553,
        "seo_title": "Best Car Insurance For Foreign Drivers And International Students",
        "meta_description": (
            "Complete guide to car insurance for foreign drivers and international "
            "students for USA immigrants in 2026. Compare top options, fees, and requirements."
        ),
        "hardcoded_fallback_used": False,
    }

    async def fake_run(self, context=None):
        return real_shaped_result

    with mock.patch.object(agent_11.WordPressIntegrationAgent, "run", fake_run), \
         mock.patch.dict(sys.modules, _fake_services_modules()), \
         mock.patch.object(sys, "argv", [
             "agent_11_wordpress_integration.py",
             "--article", str(article_path),
             "--images", str(tmp_path / "images"),
             "--output", str(output_path),
         ]), \
         mock.patch.dict(os.environ, {
             "WORDPRESS_URL": "https://moneyabroadguide.com",
             "WORDPRESS_USERNAME": "fake",
             "WORDPRESS_APP_PASSWORD": "fake",
             "ANTHROPIC_API_KEY": "fake",
         }):
        try:
            agent_11.main()
        except SystemExit as e:
            assert e.code == 0

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["keyword"] == real_shaped_result["keyword"]
    assert report["meta_description"] == real_shaped_result["meta_description"]
    assert report["meta_description"] != "Guide to  for expats."
    assert "  " not in report["meta_description"]  # no double-space artifact


def test_fallback_still_avoids_double_space_if_meta_description_somehow_missing(tmp_path):
    # Defensive case: even if run() returned no meta_description at all (should
    # not happen in practice -- _load_article_data() always has the outline's
    # fallback template, see agent_03_content_planner.py), the OLD bug (a
    # guaranteed double space from an empty keyword) must not resurface.
    agent_11 = _load_agent11()
    article_path = tmp_path / "article_draft.md"
    article_path.write_text("## Some Title\n\nBody text.\n", encoding="utf-8")
    output_path = tmp_path / "wordpress_report.json"

    result_no_meta_desc = {
        "title": "Some Title", "keyword": "", "post_id": 1, "post_url": "https://x/?p=1",
        "post_status": "draft", "uploaded_images": [], "image_count": 0, "featured_image_id": None,
        "word_count": 4200, "content_chars": 30000, "seo_title": "Some Title",
        "meta_description": "", "hardcoded_fallback_used": False,
    }

    async def fake_run(self, context=None):
        return result_no_meta_desc

    with mock.patch.object(agent_11.WordPressIntegrationAgent, "run", fake_run), \
         mock.patch.dict(sys.modules, _fake_services_modules()), \
         mock.patch.object(sys, "argv", [
             "agent_11_wordpress_integration.py",
             "--article", str(article_path),
             "--images", str(tmp_path / "images"),
             "--output", str(output_path),
         ]), \
         mock.patch.dict(os.environ, {
             "WORDPRESS_URL": "https://moneyabroadguide.com",
             "WORDPRESS_USERNAME": "fake",
             "WORDPRESS_APP_PASSWORD": "fake",
             "ANTHROPIC_API_KEY": "fake",
         }):
        try:
            agent_11.main()
        except SystemExit as e:
            assert e.code == 0

    report = json.loads(output_path.read_text(encoding="utf-8"))
    # keyword empty (nothing to fall back to) -> falls back to the title, never
    # the old "Guide to  for expats." double-space shape.
    assert report["meta_description"] == "Some Title"
