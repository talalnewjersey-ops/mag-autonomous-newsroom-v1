"""POINT 1 (2026-07-05): client-side Gemini rate limiter. Offline, no network,
no real sleeps (clock/sleep are injected).

Proves: calls under the RPM limit never wait; the (limit+1)th call within the
same 60s window waits until the oldest call ages out; state is a shared file
(simulating separate agent_10 subprocess invocations across a batch's article
loop, since each article is a fresh `python -m agents.agent_10...` process);
run_total() accumulates across "separate processes" sharing one state file.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import asyncio

from agents import _gemini_rate_limiter as rl


def _fake_clock(start=1000.0):
    state = {"t": start}
    def clock():
        return state["t"]
    def advance(seconds):
        state["t"] += seconds
    return clock, advance


async def _instant_sleep_recording(calls):
    async def sleep(seconds):
        calls.append(seconds)
    return sleep


def test_calls_under_limit_never_wait(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_RATE_LIMIT_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("GEMINI_RPM_LIMIT", "10")
    clock, advance = _fake_clock()
    sleeps = []
    async def sleep(s):
        sleeps.append(s)

    async def run():
        for _ in range(10):
            await rl.wait_for_slot(clock=clock, sleep=sleep)
    asyncio.run(run())
    assert sleeps == []                 # never had to wait, under the limit
    assert rl.run_total() == 10


def test_call_over_limit_waits_for_the_window_to_clear(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_RATE_LIMIT_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("GEMINI_RPM_LIMIT", "3")
    clock, advance = _fake_clock()
    sleeps = []

    async def sleep(s):
        sleeps.append(s)
        advance(s)   # simulate time passing during the wait

    async def run():
        for _ in range(3):
            await rl.wait_for_slot(clock=clock, sleep=sleep)   # fills the window, no wait
        await rl.wait_for_slot(clock=clock, sleep=sleep)        # 4th call must wait
    asyncio.run(run())
    assert len(sleeps) == 1
    assert sleeps[0] > 59.9             # waited (near) a full minute for the oldest to age out
    assert rl.run_total() == 4


def test_state_shared_across_separate_calls_like_separate_subprocesses(tmp_path, monkeypatch):
    # Simulates 3 articles' agent_10 subprocesses each making 1 call, sharing
    # ONE state file -- exactly the production_v2.yml batch-loop shape.
    state_file = tmp_path / "state.json"
    monkeypatch.setenv("GEMINI_RATE_LIMIT_STATE", str(state_file))
    monkeypatch.setenv("GEMINI_RPM_LIMIT", "10")
    clock, _ = _fake_clock()

    async def sleep(s):
        pass

    for _article in range(3):
        asyncio.run(rl.wait_for_slot(clock=clock, sleep=sleep))
    assert rl.run_total() == 3          # accumulated across "3 processes"


def test_default_rpm_limit_is_conservative_for_free_tier():
    assert rl.DEFAULT_RPM_LIMIT == 10   # see module docstring: confirm your project's real limit in AI Studio
