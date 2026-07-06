"""Client-side rate limiter for Gemini image-generation calls (agent_10).

IMPORTANT DISTINCTION (2026-07-05 control run): the actual failure observed in
production was "Your project has exceeded its monthly spending cap" -- a
Google AI Studio SPENDING CAP ($ ceiling), NOT a request-rate limit. This
limiter does NOT fix a spending cap (raising it requires a billing decision at
https://ai.studio/spend, deferred by the user until cron reopening). What it
DOES do: proactively space out requests to respect the free tier's per-minute
REQUEST rate, so that whenever the spend cap is raised (or on any project that
is genuinely on the free tier), the pipeline does not ALSO trip a request-rate
429 on top of / instead of the spend-cap one.

Google's own rate-limits page (ai.google.dev/gemini-api/docs/rate-limits)
states limits vary by project/usage tier and must be checked in AI Studio
directly (https://aistudio.google.com/rate-limit) -- there is no single
published number safe to hardcode for every project. GEMINI_RPM_LIMIT
defaults to a conservative published estimate for a free-tier flash-image
model (10 requests/minute); override it via the environment once the actual
project limit is confirmed in AI Studio.

State is a small JSON file (a sliding window of call timestamps + a run-total
counter) SHARED across a whole workflow's article loop: each article's
agent_10 invocation is a SEPARATE subprocess (production_v2.yml calls
`python -m agents.agent_10_image_production` once per article), so in-memory
state alone would never see other articles' calls within the same batch run.
The file naturally resets between workflow runs (GitHub Actions runners are
ephemeral -- a fresh checkout never has a leftover state file).
"""
import asyncio
import json
import os
import time
from pathlib import Path

DEFAULT_RPM_LIMIT = 10
DEFAULT_STATE_PATH = "output/.gemini_rate_limit_state.json"


def _state_path() -> Path:
    return Path(os.environ.get("GEMINI_RATE_LIMIT_STATE", DEFAULT_STATE_PATH))


def _rpm_limit() -> int:
    return int(os.environ.get("GEMINI_RPM_LIMIT", DEFAULT_RPM_LIMIT))


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"calls": [], "run_total": 0}


def _save(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")


async def wait_for_slot(clock=time.time, sleep=asyncio.sleep) -> int:
    """Block (async sleep) until a call is safe to make under the configured
    RPM limit, then record it in the shared state file. Returns the run's
    total call count so far (for consumption logging). `clock`/`sleep` are
    injectable for offline, instant tests."""
    path = _state_path()
    limit = _rpm_limit()
    state = _load(path)
    now = clock()
    calls = [t for t in state.get("calls", []) if now - t < 60]
    while len(calls) >= limit:
        wait_s = max(0.0, 60 - (now - min(calls))) + 0.05
        await sleep(wait_s)
        now = clock()
        calls = [t for t in calls if now - t < 60]
    calls.append(now)
    state["calls"] = calls
    state["run_total"] = state.get("run_total", 0) + 1
    _save(path, state)
    return state["run_total"]


def run_total() -> int:
    """Total Gemini calls made so far in this run (for the consumption log)."""
    return _load(_state_path()).get("run_total", 0)
