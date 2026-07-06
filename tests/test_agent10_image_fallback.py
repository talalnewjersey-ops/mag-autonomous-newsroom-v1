"""POINT 1 (2026-07-05): agent_10 never crashes on a Gemini quota/429 failure --
retries (existing) then SKIPS to a decorative placeholder (re-enabled; V3.8 had
disabled this and returned FAILED instead, forcing the whole article to reject).
Offline: aiohttp is stubbed (not installed in this environment, same pattern as
tests/test_sprint2_quality.py), no real network, no real sleeps.
"""
import asyncio
import importlib.util
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

if "aiohttp" not in sys.modules:
    _aio = types.ModuleType("aiohttp")
    class _ClientTimeout:
        def __init__(self, *a, **k):
            pass
    class _ClientSession:
        pass
    class _ClientError(Exception):
        pass
    _aio.ClientTimeout = _ClientTimeout
    _aio.ClientSession = _ClientSession
    _aio.ClientError = _ClientError
    sys.modules["aiohttp"] = _aio


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


agent_10 = _load("agents/agent_10_image_production.py", "agent_10_image_production")
rl = sys.modules.get("agents._gemini_rate_limiter") or _load("agents/_gemini_rate_limiter.py", "agents._gemini_rate_limiter")
agent_10._gemini_rate_limiter = rl  # ensure the module-under-test uses OUR loaded instance


class _FakeResp:
    def __init__(self, status, text="forbidden-or-quota"):
        self.status = status
        self._text = text
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        return False
    async def text(self):
        return self._text
    async def json(self):
        return {}


class _AlwaysQuotaExceededSession:
    """Every Gemini call returns 429 -- simulates the real spending-cap failure."""
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        return False
    def post(self, url, **k):
        return _FakeResp(429, "monthly spending cap exceeded")


def _agent(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    monkeypatch.setenv("GEMINI_RATE_LIMIT_STATE", str(tmp_path / "rl_state.json"))
    monkeypatch.setenv("GEMINI_RPM_LIMIT", "1000")  # don't let the limiter slow this test down
    a = agent_10.ImageProductionAgent.__new__(agent_10.ImageProductionAgent)
    a.config = {}
    a.gemini_api_key = "fake-key-for-test"
    a.nano_banana_key = ""
    a.openai_key = ""
    a.preferred_api = "gemini_imagen"
    a._wp_auth = ""
    a.wp_media_endpoint = ""
    a._session = _AlwaysQuotaExceededSession()
    return a


def test_create_placeholder_returns_success_not_failed(tmp_path, monkeypatch):
    a = _agent(tmp_path, monkeypatch)
    out_dir = tmp_path / "images"
    out_dir.mkdir()
    result = a._create_placeholder({"alt_text": "x", "caption": "y"}, out_dir, "featured", "429 quota exceeded")
    assert result["status"] == "SUCCESS"
    assert result["is_placeholder"] is True
    assert result["filepath"] and os.path.exists(result["filepath"])
    assert result["file_size_bytes"] > 0


def test_generate_with_retry_never_raises_falls_back_to_placeholder(tmp_path, monkeypatch, caplog):
    import logging
    a = _agent(tmp_path, monkeypatch)
    out_dir = tmp_path / "images"
    out_dir.mkdir()
    _real_sleep = asyncio.sleep
    monkeypatch.setattr(agent_10.asyncio, "sleep", lambda *_a, **_k: _real_sleep(0))
    with caplog.at_level(logging.WARNING):
        result = asyncio.run(a._generate_with_retry(
            {"prompt": "a photo", "alt_text": "x", "caption": "y"}, out_dir, "comparison_graphic"))
    assert result["status"] == "SUCCESS"
    assert result["is_placeholder"] is True
    assert any("SKIP" in r.getMessage() and "comparison_graphic" in r.getMessage() for r in caplog.records)


def test_rate_limiter_is_consulted_on_every_gemini_attempt(tmp_path, monkeypatch):
    a = _agent(tmp_path, monkeypatch)
    out_dir = tmp_path / "images"
    out_dir.mkdir()
    _real_sleep = asyncio.sleep
    monkeypatch.setattr(agent_10.asyncio, "sleep", lambda *_a, **_k: _real_sleep(0))
    calls = []
    real_wait = rl.wait_for_slot
    async def counting_wait(*a_, **k_):
        calls.append(1)
        return await real_wait(*a_, **k_)
    monkeypatch.setattr(rl, "wait_for_slot", counting_wait)
    asyncio.run(a._generate_with_retry({"prompt": "p", "alt_text": "x", "caption": "y"}, out_dir, "featured"))
    # gemini_imagen (3 retries) + gemini_imagen_v1 (2 retries) = 5 Gemini HTTP attempts
    assert len(calls) == 5


def test_pipeline_never_crashes_end_to_end_on_total_quota_outage(tmp_path, monkeypatch):
    # Simulates the real incident: EVERY image call 429s. run() must complete
    # without raising, and the report must show placeholders + gemini_usage.
    a = _agent(tmp_path, monkeypatch)
    # run() opens its OWN aiohttp.ClientSession (not self._session) -- swap the
    # class so it also always-429s. Also skip real retry-backoff sleeps (this
    # test only cares about correctness/never-crashing, not timing).
    monkeypatch.setattr(agent_10.aiohttp, "ClientSession", _AlwaysQuotaExceededSession)
    _real_sleep = asyncio.sleep
    monkeypatch.setattr(agent_10.asyncio, "sleep", lambda *_a, **_k: _real_sleep(0))
    prompts_path = tmp_path / "image_prompts.json"
    prompts_path.write_text(
        '{"prompts": {"featured_image": {"prompt": "p", "alt_text": "a", "caption": "c"}, '
        '"supporting_graphic": {"prompt": "p2", "alt_text": "a2", "caption": "c2"}}}',
        encoding="utf-8",
    )
    output_dir = tmp_path / "agent_10_out"
    report = asyncio.run(a.run(str(prompts_path), output_dir=str(output_dir)))
    assert report["verdict"] in ("PASS", "FAIL")   # completed, did not raise
    assert "gemini_usage" in report
    assert report["gemini_usage"]["run_total_calls"] > 0
    all_imgs = a._collect_all(report["results"])
    assert all(img.get("is_placeholder") for img in all_imgs)
    assert all(img.get("status") == "SUCCESS" for img in all_imgs)
