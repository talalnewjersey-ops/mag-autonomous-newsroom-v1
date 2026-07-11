"""Direct unit tests for the shared Hostinger hCDN challenge-403 detection +
backoff retry logic (agents/_wp_challenge.py, 2026-07-11, PR express). Each
integration point (agents/_real_internal_links.py, agent_17_cannibalization.py,
services/wordpress_service.py, agent_10/11) is tested through its own client-
specific mock elsewhere; THIS file tests the shared abstraction in isolation,
independent of any HTTP library.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents._wp_challenge import (
    is_challenge_403, call_with_challenge_retry, call_with_challenge_retry_async,
    RETRY_DELAYS_SECONDS, INTER_CALL_SPACING_SECONDS,
)


CHALLENGE_BODY = (
    '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
    '<meta name="robots" content="noindex,nofollow">'
    '<meta http-equiv="refresh" content="30">'
    '<link rel="preconnect" href="https://fonts.googleapis.com"></head></html>'
)
HARD_403_BODY = '{"code":"rest_forbidden","message":"Sorry, you are not allowed to do that."}'


# ---------------------------------------------------------------- is_challenge_403

def test_challenge_signature_is_detected():
    assert is_challenge_403(403, CHALLENGE_BODY) is True


def test_challenge_signature_detection_is_case_insensitive():
    upper = CHALLENGE_BODY.replace("meta http-equiv", "META HTTP-EQUIV").replace('content="30"', 'CONTENT="30"')
    assert is_challenge_403(403, upper) is True


def test_hard_403_json_body_is_not_a_challenge():
    assert is_challenge_403(403, HARD_403_BODY) is False


def test_non_403_status_is_never_a_challenge_even_with_matching_body():
    # the signature alone is not enough -- status must ALSO be 403.
    assert is_challenge_403(200, CHALLENGE_BODY) is False
    assert is_challenge_403(503, CHALLENGE_BODY) is False


def test_empty_or_missing_body_is_not_a_challenge():
    assert is_challenge_403(403, "") is False
    assert is_challenge_403(403, None) is False


def test_other_meta_refresh_durations_do_not_match():
    # the signature is specifically the interstitial's OWN stated 30s wait --
    # a refresh tag with a different duration is a different (unrelated) page.
    other = CHALLENGE_BODY.replace('content="30"', 'content="5"')
    assert is_challenge_403(403, other) is False


def test_retry_delays_are_the_documented_35_70_140():
    assert RETRY_DELAYS_SECONDS == (35, 70, 140)


# ---------------------------------------------------------------- call_with_challenge_retry (sync)

def test_sync_retry_succeeds_after_two_challenges():
    attempts = []

    def make_attempt():
        attempts.append(1)
        if len(attempts) < 3:
            return 403, CHALLENGE_BODY, None
        return 200, "OK", "final-result"

    sleeps = []
    status, body, result = call_with_challenge_retry(make_attempt, sleep_fn=sleeps.append)
    assert (status, body, result) == (200, "OK", "final-result")
    assert len(attempts) == 3
    assert sleeps == [35, 70]


def test_sync_retry_never_fires_for_a_hard_403():
    attempts = []

    def make_attempt():
        attempts.append(1)
        return 403, HARD_403_BODY, None

    sleeps = []
    status, body, _ = call_with_challenge_retry(make_attempt, sleep_fn=sleeps.append)
    assert status == 403
    assert len(attempts) == 1
    assert sleeps == []


def test_sync_retry_exhausts_all_three_retries_then_gives_up():
    attempts = []

    def make_attempt():
        attempts.append(1)
        return 403, CHALLENGE_BODY, None

    sleeps = []
    status, _body, _ = call_with_challenge_retry(make_attempt, sleep_fn=sleeps.append)
    assert status == 403  # still a challenge -- caller decides what "gave up" means
    assert len(attempts) == 4  # 1 initial + 3 retries
    assert sleeps == [35, 70, 140]


def test_sync_retry_log_fn_called_with_1_based_attempt_number_and_delay():
    calls = []

    def make_attempt():
        return 403, CHALLENGE_BODY, None

    call_with_challenge_retry(make_attempt, sleep_fn=lambda s: None,
                               log_fn=lambda n, d: calls.append((n, d)))
    assert calls == [(1, 35), (2, 70), (3, 140)]


# ---------------------------------------------------------------- call_with_challenge_retry_async

def test_async_retry_succeeds_after_one_challenge():
    import asyncio
    attempts = []

    async def make_attempt():
        attempts.append(1)
        if len(attempts) < 2:
            return 403, CHALLENGE_BODY, None
        return 201, "created", {"id": 42}

    async def _fake_sleep(seconds):
        return None

    status, body, result = asyncio.run(call_with_challenge_retry_async(make_attempt, sleep_fn=_fake_sleep))
    assert (status, body, result) == (201, "created", {"id": 42})
    assert len(attempts) == 2


def test_async_retry_never_fires_for_a_hard_403():
    import asyncio
    attempts = []

    async def make_attempt():
        attempts.append(1)
        return 403, HARD_403_BODY, None

    sleeps = []
    async def _record_sleep(seconds):
        sleeps.append(seconds)

    status, _body, _ = asyncio.run(call_with_challenge_retry_async(make_attempt, sleep_fn=_record_sleep))
    assert status == 403
    assert len(attempts) == 1
    assert sleeps == []


def test_async_retry_exhausts_all_three_retries_then_gives_up():
    import asyncio
    attempts = []

    async def make_attempt():
        attempts.append(1)
        return 403, CHALLENGE_BODY, None

    sleeps = []
    async def _record_sleep(seconds):
        sleeps.append(seconds)

    status, _body, _ = asyncio.run(call_with_challenge_retry_async(make_attempt, sleep_fn=_record_sleep))
    assert status == 403
    assert len(attempts) == 4
    assert sleeps == [35, 70, 140]
