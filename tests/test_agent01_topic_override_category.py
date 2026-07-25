"""2026-07-25: manual --topic override never set "category", so downstream
resolve_gate_vertical(market, category) always fell through to "us_default"
(no engraved facts) -- confirmed on a real dry-run: two CASE-5-validation
topics both failed G-Substance ("0 STABLE facts cited") purely because the
override bypassed the registry's category->vertical routing, burning real
API cost for nothing. Optional "keyword||category" syntax restores it.

Offline: no network, no API key (SEOResearchAgent.run's override branch
returns before any live/DB/LLM call).
"""
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.agent_01_seo_research import SEOResearchAgent  # noqa: E402
from agents._source_pool import resolve_gate_vertical  # noqa: E402


def _run_override(topic_override, tmp_path):
    agent = SEOResearchAgent()
    out_path = tmp_path / "topics.json"
    out = asyncio.run(agent.run(max_topics=1, output_path=str(out_path),
                                 topic_override=topic_override))
    return out, json.loads(out_path.read_text(encoding="utf-8"))


def test_override_without_category_suffix_defaults_to_empty_category(tmp_path):
    out, _ = _run_override("how to open a us bank account without an ssn", tmp_path)
    topic = out["topics"][0]
    assert topic["keyword"] == "how to open a us bank account without an ssn"
    assert topic.get("category", "") == ""
    # the historical bug: empty category -> us_default -> no engraved facts
    assert resolve_gate_vertical(topic["market"], topic.get("category", "")) == "us_default"


def test_override_with_category_suffix_routes_the_real_vertical(tmp_path):
    out, written = _run_override(
        "how to open a us bank account without an ssn||banques", tmp_path)
    topic = out["topics"][0]
    assert topic["keyword"] == "how to open a us bank account without an ssn"
    assert topic["category"] == "banques"
    assert resolve_gate_vertical(topic["market"], topic["category"]) == "us_banking"
    # survives the on-disk round trip agent_02/production_batch_loop.sh reads from
    assert written["topics"][0]["category"] == "banques"


def test_override_with_category_suffix_credit_vertical(tmp_path):
    out, _ = _run_override(
        "does applying for a credit card hurt your score as a new immigrant||credit",
        tmp_path)
    topic = out["topics"][0]
    assert topic["category"] == "credit"
    assert resolve_gate_vertical(topic["market"], topic["category"]) == "us_credit"


def test_override_category_whitespace_is_trimmed(tmp_path):
    out, _ = _run_override("some keyword ||  credit  ", tmp_path)
    topic = out["topics"][0]
    assert topic["keyword"] == "some keyword"
    assert topic["category"] == "credit"
