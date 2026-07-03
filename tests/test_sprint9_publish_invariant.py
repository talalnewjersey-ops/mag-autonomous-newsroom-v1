"""Sprint 9 — publish invariant. Offline, no network, no API key.

THE TWO NON-NEGOTIABLE ASSERTIONS (control-run contract):
  1. an article that fails QA stays `candidate` -- never `published`
  2. a [QA-FAILED] draft cannot be promoted to `published` by the reconcile

Root cause fixed: the reconcile used to key on agent_11's wordpress_report.json
post_id, which is written BEFORE the QA (agent_12) / editor (agent_13) gates. It
now keys on the terminal marker PRODUCED.json, written by the workflow ONLY after
all blocking gates pass. Plus: pre-publish WP dedup (agent_11) and the QA-FAILED
title marker helper.
"""
import asyncio
import importlib.util
import json
import os
import sys
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ---------------------------------------------------------------- reconcile (agent_01)
from agents.agent_01_seo_research import SEOResearchAgent  # noqa: E402 (direct import, no aiohttp at top)


def _agent(reg):
    a = SEOResearchAgent(config={})
    a.registry_path = str(reg)
    return a


def _topic(tid, status="in_progress", **extra):
    base = {"id": tid, "title": tid, "keyword": tid, "market": "USA", "category": "banques",
            "monetization_score": 5, "traffic_score": 5, "status": status,
            "published_at": None, "post_id": None, "selected_at": "2026-07-02T00:00:00Z"}
    base.update(extra)
    return base


def _write_reg(tmp, *topics):
    p = tmp / "reg.json"
    p.write_text(json.dumps({"version": "t", "topics": list(topics)}), encoding="utf-8")
    return p


def _write_run(tmp, topic_id, produced_post_id=None, wp_report_post_id=None, qa_status=None):
    """Emulate a run's artifacts. PRODUCED.json is present ONLY on true success."""
    art = tmp / "output" / "article_1"
    (art / "agent_01").mkdir(parents=True, exist_ok=True)
    (art / "agent_01" / "topics.json").write_text(json.dumps({"topics": [{"id": topic_id}]}), encoding="utf-8")
    if wp_report_post_id is not None:  # agent_11 created a draft (BEFORE QA)
        (art / "agent_11").mkdir(parents=True, exist_ok=True)
        (art / "agent_11" / "wordpress_report.json").write_text(
            json.dumps({"status": "COMPLETE", "post_id": wp_report_post_id}), encoding="utf-8")
    if qa_status is not None:
        (art / "agent_12").mkdir(parents=True, exist_ok=True)
        (art / "agent_12" / "qa_report.json").write_text(json.dumps({"status": qa_status}), encoding="utf-8")
    if produced_post_id is not None:  # terminal success marker (AFTER all gates)
        (art / "PRODUCED.json").write_text(
            json.dumps({"post_id": produced_post_id, "produced": True}), encoding="utf-8")
    return str(tmp / "output")


def _status(reg, tid):
    return next(t for t in json.loads(open(reg).read())["topics"] if t["id"] == tid)


# ===== NON-NEGOTIABLE 1 =====
def test_qa_failed_run_stays_candidate(tmp_path):
    """Draft was created (wordpress_report has a post_id) but QA failed -> NO
    PRODUCED.json -> the topic must roll back to candidate, never published."""
    reg = _write_reg(tmp_path, _topic("t"))
    out = _write_run(tmp_path, "t", produced_post_id=None, wp_report_post_id=48418, qa_status="FAIL")
    _agent(reg).reconcile_registry(output_dir=out)
    t = _status(reg, "t")
    assert t["status"] == "candidate", "QA-failed article must NOT be published"
    assert t["post_id"] is None and t["published_at"] is None


# ===== NON-NEGOTIABLE 2 =====
def test_qa_failed_draft_cannot_be_promoted(tmp_path):
    """A [QA-FAILED] draft (post exists on WP, no PRODUCED marker) must never be
    promoted to published by the reconcile."""
    reg = _write_reg(tmp_path, _topic("t"))
    out = _write_run(tmp_path, "t", produced_post_id=None, wp_report_post_id=48418, qa_status="FAIL")
    res = _agent(reg).reconcile_registry(output_dir=out)
    assert res["published"] == []
    assert _status(reg, "t")["status"] == "candidate"


# ===== positive + old-bug regression =====
def test_truly_produced_run_marks_published(tmp_path):
    reg = _write_reg(tmp_path, _topic("t"))
    out = _write_run(tmp_path, "t", produced_post_id=48500, wp_report_post_id=48500, qa_status="PASS")
    _agent(reg).reconcile_registry(output_dir=out)
    t = _status(reg, "t")
    assert t["status"] == "published" and t["post_id"] == 48500 and t["published_at"]


def test_wordpress_postid_without_marker_never_publishes(tmp_path):
    """The exact old bug: a post_id in wordpress_report.json with NO PRODUCED.json
    (QA/editor not yet run or failed) must NOT promote the topic."""
    reg = _write_reg(tmp_path, _topic("t"))
    out = _write_run(tmp_path, "t", produced_post_id=None, wp_report_post_id=99999)
    _agent(reg).reconcile_registry(output_dir=out)
    assert _status(reg, "t")["status"] == "candidate"


# ---------------------------------------------------------------- dedup (agent_11)
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
_stub("services.llm_service", LLMService=object)
_stub("services.storage_service", StorageService=object)
_stub("services.wordpress_service", WordPressService=object)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


agent_11 = _load("agents/agent_11_wordpress_integration.py", "agent_11_s9")
mqf = _load("scripts/mark_qa_failed.py", "mark_qa_failed_s9")
WP = agent_11.WordPressIntegrationAgent


def test_dedup_detects_same_title_across_status():
    existing = [{"id": 48384, "status": "publish",
                 "title": {"raw": "Best High-Interest Savings Accounts For International Students"}}]
    dup = WP._duplicate_of(existing, "Best High-Interest Savings Accounts For International Students")
    assert dup and dup["id"] == 48384, "48384/48412-class duplicate must be caught"


def test_dedup_is_case_and_punctuation_insensitive():
    existing = [{"id": 2, "title": {"rendered": "best HIGH-interest  savings accounts!"}}]
    assert WP._duplicate_of(existing, "Best High Interest Savings Accounts")["id"] == 2


def test_dedup_ignores_distinct_titles():
    existing = [{"id": 1, "title": {"raw": "Car Insurance Guide"}}]
    assert WP._duplicate_of(existing, "Best Banks for Immigrants Without SSN") is None
    assert WP._duplicate_of([], "anything") is None


# ---------------------------------------------------------------- QA-FAILED marker
def test_qa_failed_title_is_idempotent():
    assert mqf.qa_failed_title("Car Insurance Guide") == "[QA-FAILED] Car Insurance Guide"
    assert mqf.qa_failed_title("[QA-FAILED] Car Insurance Guide") == "[QA-FAILED] Car Insurance Guide"
