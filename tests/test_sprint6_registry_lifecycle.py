"""Sprint 6 — topic registry lifecycle (agent_01 reconcile). No network, no API key.

Guarantees the anti-burn rule:
- FAILED run (no valid post_id / missing report) -> selected topic rolls back to
  candidate, never stuck in_progress (a failed run never burns its topic).
- SUCCESSFUL run (agent_11 wrote a real post_id) -> topic becomes published, with
  post_id + published_at recorded.
- An already-published topic is never touched by a later run.
- `in_progress` is transient and must NEVER survive reconciliation.
"""
import json
from pathlib import Path

from agents.agent_01_seo_research import SEOResearchAgent


# ---------- helpers ----------

def _agent(registry_path):
    a = SEOResearchAgent(config={})
    a.registry_path = str(registry_path)
    return a


def _registry(*topics) -> dict:
    return {"version": "test", "topics": list(topics)}


def _topic(tid, status="candidate", **extra):
    base = {
        "id": tid, "title": tid.replace("-", " ").title(), "keyword": tid,
        "market": "Canada", "category": "banques",
        "monetization_score": 5, "traffic_score": 5,
        "status": status, "published_at": None, "post_id": None, "selected_at": None,
    }
    base.update(extra)
    return base


def _write_registry(tmp_path, registry) -> Path:
    p = tmp_path / "reg.json"
    p.write_text(json.dumps(registry), encoding="utf-8")
    return p


def _write_artifacts(tmp_path, topic_id, post_id):
    """Emulate a run's artifacts: agent_01 topics.json (always) + agent_11
    wordpress_report.json (only when post_id is not None)."""
    art = tmp_path / "output" / "article_1"
    (art / "agent_01").mkdir(parents=True, exist_ok=True)
    (art / "agent_01" / "topics.json").write_text(
        json.dumps({"topics": [{"id": topic_id}]}), encoding="utf-8")
    (art / "agent_11").mkdir(parents=True, exist_ok=True)
    if post_id is None:
        # failure: agent_11 writes a FAILED report with post_id null (like the real one)
        (art / "agent_11" / "wordpress_report.json").write_text(
            json.dumps({"status": "FAILED", "post_id": None, "draft_created": False}),
            encoding="utf-8")
    else:
        (art / "agent_11" / "wordpress_report.json").write_text(
            json.dumps({"status": "COMPLETE", "post_id": post_id, "draft_created": True}),
            encoding="utf-8")
        # Sprint 9 contract: reconcile promotes on the terminal PRODUCED.json marker
        # (written only after QA+editor+production_gate pass), not on agent_11's
        # pre-QA post_id. A success case therefore carries PRODUCED.json.
        (art / "PRODUCED.json").write_text(
            json.dumps({"post_id": post_id, "produced": True}), encoding="utf-8")
    return str(tmp_path / "output")


def _status(reg_path, tid):
    topics = json.loads(Path(reg_path).read_text(encoding="utf-8"))["topics"]
    return next(t for t in topics if t["id"] == tid)


# ---------- FAILED run -> candidate ----------

def test_failed_run_rolls_back_to_candidate(tmp_path):
    """Topic was claimed in_progress, but the run failed (report has no post_id).
    Reconcile must return it to candidate so it is re-pickable — never burned."""
    reg = _write_registry(tmp_path, _registry(_topic("t-fail", status="in_progress",
                                                      selected_at="2026-07-01T00:00:00Z")))
    out = _write_artifacts(tmp_path, "t-fail", post_id=None)

    _agent(reg).reconcile_registry(output_dir=out)

    t = _status(reg, "t-fail")
    assert t["status"] == "candidate", "failed run must roll the topic back to candidate"
    assert t["selected_at"] is None
    assert t["post_id"] is None
    assert t["published_at"] is None


def test_missing_report_also_rolls_back(tmp_path):
    """Even if agent_11 never ran (no report file at all), the in_progress topic
    must not stay stuck."""
    reg = _write_registry(tmp_path, _registry(_topic("t-crash", status="in_progress")))
    # artifacts with topics.json but delete the report to emulate an upstream crash
    out = _write_artifacts(tmp_path, "t-crash", post_id=None)
    (Path(out) / "article_1" / "agent_11" / "wordpress_report.json").unlink()

    _agent(reg).reconcile_registry(output_dir=out)

    assert _status(reg, "t-crash")["status"] == "candidate"


# ---------- SUCCESSFUL run -> published ----------

def test_successful_run_marks_published(tmp_path):
    """A run that produced a real post_id promotes the topic to published, recording
    post_id and a non-null published_at."""
    reg = _write_registry(tmp_path, _registry(_topic("t-ok", status="in_progress")))
    out = _write_artifacts(tmp_path, "t-ok", post_id=48403)

    res = _agent(reg).reconcile_registry(output_dir=out)

    t = _status(reg, "t-ok")
    assert t["status"] == "published"
    assert t["post_id"] == 48403
    assert t["published_at"] is not None
    assert res["published"] == ["t-ok"]


# ---------- published is immutable across runs ----------

def test_existing_published_is_never_touched(tmp_path):
    """A topic already published in a previous run stays published untouched, even
    though it is not part of the current run's artifacts."""
    reg = _write_registry(tmp_path, _registry(
        _topic("t-seed", status="published", post_id=100, published_at="2026-06-01T00:00:00Z"),
        _topic("t-new", status="in_progress"),
    ))
    out = _write_artifacts(tmp_path, "t-new", post_id=200)

    _agent(reg).reconcile_registry(output_dir=out)

    seed = _status(reg, "t-seed")
    assert seed["status"] == "published"
    assert seed["post_id"] == 100, "prior post_id must be preserved"
    assert seed["published_at"] == "2026-06-01T00:00:00Z"
    assert _status(reg, "t-new")["status"] == "published"


# ---------- invariant: no in_progress ever survives ----------

def test_no_in_progress_survives_reconcile(tmp_path):
    """Whatever the mix of outcomes, reconcile must leave zero in_progress topics."""
    reg = _write_registry(tmp_path, _registry(
        _topic("t-ok", status="in_progress"),
        _topic("t-fail", status="in_progress"),
        _topic("t-untouched", status="candidate"),
    ))
    # only t-ok succeeds
    out = _write_artifacts(tmp_path, "t-ok", post_id=999)
    # add a second failed article for t-fail
    art2 = tmp_path / "output" / "article_2"
    (art2 / "agent_01").mkdir(parents=True, exist_ok=True)
    (art2 / "agent_01" / "topics.json").write_text(json.dumps({"topics": [{"id": "t-fail"}]}),
                                                   encoding="utf-8")

    _agent(reg).reconcile_registry(output_dir=out)

    topics = json.loads(Path(reg).read_text(encoding="utf-8"))["topics"]
    assert not any(t["status"] == "in_progress" for t in topics)
    assert _status(reg, "t-ok")["status"] == "published"
    assert _status(reg, "t-fail")["status"] == "candidate"
    assert _status(reg, "t-untouched")["status"] == "candidate"


# ---------- manual override (non-registry topic) is a no-op ----------

def test_manual_override_topic_is_ignored(tmp_path):
    """A run using --topic (id not in the registry) must not crash or mutate."""
    reg = _write_registry(tmp_path, _registry(_topic("t-real", status="candidate")))
    out = _write_artifacts(tmp_path, "manual-adhoc-topic", post_id=777)

    res = _agent(reg).reconcile_registry(output_dir=out)

    assert res["published"] == []
    assert _status(reg, "t-real")["status"] == "candidate"
