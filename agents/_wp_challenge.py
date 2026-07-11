"""Hostinger hCDN "please wait" challenge-403 detection + backoff retry
(2026-07-11, PR express). See docs/hostinger-403-ticket.md for the full
diagnosis: NOT a static IP/WAF block (hPanel confirms the CDN Security Level
is off with no IPs blocked, and a light diagnostic from an actual GitHub
Actions runner succeeded on every call) -- most likely a volume/pattern-based
automatic anti-abuse heuristic. The interstitial page tells you exactly what
to do: its own `<meta http-equiv="refresh" content="30">` means "wait 30s and
reload" -- so a short wait-and-retry is the mechanically correct response to
THIS specific signature, not a generic workaround.

CRITICAL: a genuine WordPress `rest_forbidden` JSON 403 (or any other site's
own unrelated 403, e.g. a .gov source bot-blocking automated fact-check
requests) must NEVER be retried this way -- it's either a real authorization
decision (app password revoked, permissions changed) or someone else's block
entirely unrelated to Hostinger's edge. is_challenge_403() is the ONLY
discriminator between the two: it matches ONLY the exact interstitial
signature, so it can safely be applied to every 403 in the codebase without
risking a pointless multi-minute retry on a hard failure.
"""
import re

CHALLENGE_SIGNATURE_RE = re.compile(
    r'<meta\s+http-equiv=["\']refresh["\']\s+content=["\']30["\']', re.IGNORECASE
)

# 3 retries, growing backoff -- matches the interstitial's own stated wait (30s),
# rounded up slightly for clock/network slack. Applied AFTER attempt 1 fails, so
# 4 attempts total: 1 initial + 3 retries.
RETRY_DELAYS_SECONDS = (35, 70, 140)

# Light, fixed spacing applied before EVERY WordPress request (read or write) --
# not a retry, just pacing normal traffic to stay under whatever volume/pattern
# threshold triggers the challenge in the first place (see the ticket).
INTER_CALL_SPACING_SECONDS = 2.5


def is_challenge_403(status_code, body_text):
    """True ONLY for the specific Hostinger hCDN "please wait" interstitial: an
    HTTP 403 whose body carries its own 30s meta-refresh tag. A hard 403 (a
    clean WordPress `rest_forbidden` JSON error, or any other site's own
    unrelated 403) returns False -- the caller must fail/classify it
    immediately, never retry."""
    if status_code != 403 or not body_text:
        return False
    return bool(CHALLENGE_SIGNATURE_RE.search(body_text))


def call_with_challenge_retry(make_attempt, sleep_fn, log_fn=None):
    """Synchronous retry loop. `make_attempt()` performs ONE request attempt and
    must return (status_code, body_text, result) -- it should NOT raise for an
    HTTP error response (catch that internally and return the status/body so
    this wrapper can inspect it); any OTHER exception (network failure, DNS,
    timeout, ...) should propagate out of make_attempt() uncaught, and this
    wrapper does not catch it either -- unchanged, un-retried fail-soft
    behavior for anything that isn't specifically this challenge signature.

    log_fn(attempt_number, delay_seconds), if given, is called before each
    sleep (for a log line at the call site) -- attempt_number is 1-based for
    the retry about to happen.

    Returns whatever the LAST make_attempt() call returned (either a non-
    challenge response, or the final exhausted-retries attempt)."""
    result = None
    for attempt in range(len(RETRY_DELAYS_SECONDS) + 1):
        result = make_attempt()
        status_code, body_text, _ = result
        if not is_challenge_403(status_code, body_text):
            return result
        if attempt < len(RETRY_DELAYS_SECONDS):
            delay = RETRY_DELAYS_SECONDS[attempt]
            if log_fn:
                log_fn(attempt + 1, delay)
            sleep_fn(delay)
    return result


async def call_with_challenge_retry_async(make_attempt, sleep_fn, log_fn=None):
    """Async twin of call_with_challenge_retry -- see its docstring. `make_attempt`
    is an async callable; `sleep_fn` is an async sleep (e.g. asyncio.sleep)."""
    result = None
    for attempt in range(len(RETRY_DELAYS_SECONDS) + 1):
        result = await make_attempt()
        status_code, body_text, _ = result
        if not is_challenge_403(status_code, body_text):
            return result
        if attempt < len(RETRY_DELAYS_SECONDS):
            delay = RETRY_DELAYS_SECONDS[attempt]
            if log_fn:
                log_fn(attempt + 1, delay)
            await sleep_fn(delay)
    return result
