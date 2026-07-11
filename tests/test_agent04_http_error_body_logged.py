"""2026-07-11: real-run finding (witness run 5, article 3, us-best-credit-cards-no-ssn,
PILLAR tier) -- agent_04's Claude call failed with "HTTP Error 400: Bad Request" on
both the original attempt and the retry, and that bare urllib.error.HTTPError string
is ALL that ever reached the logs (main()'s except Exception just does f"...: {e}").
The actual Anthropic response body -- which would say WHY (bad param, prompt/context
too long, content policy, ...) -- was silently discarded by urlopen's exception path.

Same observability principle as the per-gate attempt0 report preservation in
production_v2.yml (see tests/test_retry_safety.py): don't lose the one artifact that
would have made the failure diagnosable on the first occurrence.

Offline, no network, no API key.
"""
import asyncio
import importlib.util
import inspect
import io
import os
import sys
import unittest.mock as mock
import urllib.error
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


agent_04 = _load("agents/agent_04_article_writer.py", "agent_04_http_body_test")


def _make_http_error(code, body_bytes):
    return urllib.error.HTTPError(
        url="https://api.anthropic.com/v1/messages",
        code=code,
        msg="Bad Request",
        hdrs=None,
        fp=io.BytesIO(body_bytes),
    )


def test_call_claude_reads_and_surfaces_the_response_body_on_http_error():
    # _call_claude does `import urllib.request` locally, which just re-binds the
    # same sys.modules singleton -- patching the real urllib.request.urlopen
    # affects it regardless of where the import statement lives.
    real_body = b'{"type":"error","error":{"type":"invalid_request_error","message":"max_tokens: 1200 is too large for this model given the prompt length"}}'

    def _fake_urlopen(req, timeout=300):
        raise _make_http_error(400, real_body)

    with mock.patch.object(urllib.request, "urlopen", side_effect=_fake_urlopen):
        with pytest.raises(RuntimeError) as excinfo:
            asyncio.run(agent_04._call_claude("fake-key", "prompt", max_tokens=1200))

    msg = str(excinfo.value)
    assert "max_tokens: 1200 is too large for this model" in msg
    assert "400" in msg


def test_call_claude_error_message_includes_model_and_max_tokens_for_triage():
    src = inspect.getsource(agent_04._call_claude)
    assert "model={model}" in src
    assert "max_tokens={max_tokens}" in src


def test_call_claude_truncates_body_so_a_huge_error_page_cant_flood_logs():
    huge_body = b"x" * 10_000

    def _fake_urlopen(req, timeout=300):
        raise _make_http_error(413, huge_body)

    with mock.patch.object(urllib.request, "urlopen", side_effect=_fake_urlopen):
        with pytest.raises(RuntimeError) as excinfo:
            asyncio.run(agent_04._call_claude("fake-key", "prompt"))

    assert len(str(excinfo.value)) < 2200


def test_top_level_error_handler_still_catches_the_enriched_message():
    # main()'s except Exception just does f"Article writing failed: {e}" -- confirm
    # that wrapper is unchanged and will still surface whatever _call_claude raises.
    src = open(os.path.join(ROOT, "agents/agent_04_article_writer.py"), encoding="utf-8").read()
    assert 'logger.error(f"Article writing failed: {e}")' in src
