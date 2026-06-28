"""
NEXUS-14 Sprint 2 regression tests.

Covers the four sprint guarantees:
  1. G3 anti-repetition gate: PASS on a clean article, FAIL on duplicated
     phrases and on near-identical sections.
  2. DRI metric: detects diffuse trigram repetition; clean text scores ~0.
  3. Writer model: agent_04 sends "claude-sonnet-4-6" by default (RCA-003)
     and remains env-overridable.
  4. Digest: _build_digest is bounded (<= cap) and is actually injected into
     the section prompt, surfacing entities AND figures (RCA-004).

All tests are deterministic and require no network / no API key.
"""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g3 = _load("scripts/g3_repetition_gate.py", "g3_repetition_gate")
dri = _load("scripts/dri_metric.py", "dri_metric")
agent_04 = _load("agents/agent_04_article_writer.py", "agent_04_article_writer")


# ---------------------------------------------------------------- G3 gate

_CLEAN_ARTICLE = """---
title: "x"
---
# Title

## Opening Your First Account
Newcomers should visit a branch within their first week. Bring a passport and a
secondary document. Direct deposit lets employers pay your salary electronically.

## Building a Credit History
A strong credit score takes time. Use a secured card responsibly and pay the
balance in full each month to demonstrate reliability to lenders over time.

## Avoiding Common Fees
Monthly maintenance charges add up. Compare providers and pick a plan that waives
fees for the first year, then reassess once the promotional window closes.
"""

_DUP_ARTICLE = """---
title: "x"
---
# Title

## Section One
You must present two pieces of identification to open a basic chequing account
quickly and without unnecessary delays at any major branch location nationwide.

## Section Two
You must present two pieces of identification to open a basic chequing account
quickly and without unnecessary delays at any major branch location nationwide.
"""


def test_g3_passes_clean_article():
    res = g3.evaluate(_CLEAN_ARTICLE)
    assert res["passed"] is True
    assert res["decision"] == "PASS"
    assert res["max_pairwise_cosine"] < g3.COSINE_THRESHOLD


def test_g3_blocks_duplicate_phrases():
    res = g3.evaluate(_DUP_ARTICLE)
    assert res["passed"] is False
    assert res["decision"] == "FAIL"
    # Either the duplicate-phrase check or the cosine check (or both) must fire.
    assert res["duplicate_phrases"] or res["over_threshold_pairs"]


def test_g3_thresholds_are_frozen():
    # Calibration-frozen values must not drift.
    assert g3.COSINE_THRESHOLD == 0.80
    assert g3.MIN_DUP_WORDS == 8


# ---------------------------------------------------------------- DRI metric

def test_dri_zero_on_varied_text():
    res = dri.compute_dri(_CLEAN_ARTICLE)
    assert res["dri"] == 0
    assert res["excess_dispersion"] == 0


def test_dri_detects_diffuse_repetition():
    # Same content trigram planted in three distinct sections.
    phrase = "provincial health authority"
    md = "---\ntitle: x\n---\n# T\n"
    for i in range(3):
        md += "\n## Section %d\nRegister with the %s promptly after arrival to " \
              "secure coverage details and timelines.\n" % (i, phrase)
    res = dri.compute_dri(md)
    assert res["dri"] >= 1
    assert any("provincial health authority" in t["trigram"]
               for t in res["top_diffuse_trigrams"])


def test_dri_metric_params_default():
    assert dri.MIN_SECTIONS == 3
    assert dri.NGRAM == 3


# --------------------------------------------------------------- writer model

def test_writer_default_model_is_sonnet_4_6(monkeypatch):
    # No explicit model + no env override -> the frozen Sonnet version.
    monkeypatch.delenv("ARTICLE_WRITER_MODEL", raising=False)
    captured = {}

    async def fake_urlopen(*args, **kwargs):  # pragma: no cover - not reached
        raise AssertionError("network must not be called")

    # Inspect the source-level default rather than making a request.
    import inspect
    src = inspect.getsource(agent_04._call_claude)
    assert "claude-sonnet-4-6" in src
    assert "ARTICLE_WRITER_MODEL" in src
    # Must NOT silently fall back to haiku for the writer.
    assert "claude-haiku" not in src


def test_writer_model_env_overridable(monkeypatch):
    import inspect
    src = inspect.getsource(agent_04._call_claude)
    # The default is read from the environment variable, allowing override.
    assert 'os.getenv("ARTICLE_WRITER_MODEL"' in src


# ------------------------------------------------------------------- digest

_S1 = "## Opening an Account\nThe Financial Consumer Agency of Canada confirms " \
      "you may open an account with 2 pieces of ID within 5 business days. RBC " \
      "and Scotiabank offer free packages for 12 months."
_S2 = "## Required Documents\nA Permanent Resident Card works as primary ID. " \
      "The Financial Consumer Agency of Canada notes a SIN is optional."


def test_digest_lists_entities_and_numbers():
    d = agent_04._build_digest([_S1, _S2])
    # Entities present.
    assert "Financial Consumer Agency" in d or "RBC" in d
    # Figures present (not just titles).
    assert "5 business days" in d or "12 months" in d or "2 pieces of id" in d.lower()


def test_digest_is_bounded():
    big = "## S%d\nThe Financial Consumer Agency of Canada cited 5 business days " \
          "and 12 months at RBC, Scotiabank, and TD Bank repeatedly. "
    sections = [big % i for i in range(40)]
    d = agent_04._build_digest(sections)
    assert len(d) <= agent_04._DIGEST_MAX_TOTAL_CHARS


def test_digest_empty_when_no_sections():
    assert agent_04._build_digest([]) == ""


def test_digest_injected_into_section_prompt():
    # The section loop must build the digest from intro + prior sections and
    # append it to the section prompt.
    import inspect
    src = inspect.getsource(agent_04._write_article_standalone)
    assert "_build_digest([intro] + written_sections)" in src
    assert "digest_block" in src


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
