"""Live, WordPress-REST-verified internal links (2026-07-05).

Replaces agent_04's static, hand-maintained INTERNAL_LINKS dict, which had
drifted to 18 of 21 (86%) dead links -- see the multi-vertical control run
diagnostic (memory: nexus14-next-session-backlog.md). The dict was written
once and never re-verified against the live site as content evolved; a static
list of this kind can only ever get staler, never self-correct.

STRICT RULE: a link is offered to the writer ONLY if its URL is confirmed
present in the LIVE WordPress REST API post list fetched at the START of this
run. Zero relevant real posts found -> zero internal links for that article --
an ACCEPTABLE outcome. NEVER invent, guess, or fall back to a hardcoded list.

FAILURE MODE (network error, non-200, timeout, malformed JSON, at any page):
returns [] and logs a clear warning identifying the failure -- the caller
(agent_04) then writes the article with NO internal links rather than
crashing or reverting to a stale dict. Same "skip + log, never crash, never
guess" philosophy as the Gemini quota / gov-domain-block fixes (points 1-2 of
this same lot).

No WP credentials needed or used: published posts are public via the REST
API, exactly like every other live-site read this project has done all
along (no authentication available in this pipeline for agent_04 anyway).
"""
import json
import logging
import re
import time
import urllib.error
import urllib.request

from agents._wp_challenge import (
    RETRY_DELAYS_SECONDS, INTER_CALL_SPACING_SECONDS,
    call_with_challenge_retry,
)

logger = logging.getLogger(__name__)

POSTS_ENDPOINT = "https://moneyabroadguide.com/wp-json/wp/v2/posts"
PAGES_ENDPOINT = "https://moneyabroadguide.com/wp-json/wp/v2/pages"
_TIMEOUT_SECONDS = 10
_PER_PAGE = 100
_MAX_PAGES = 5  # hard cap (<=500 posts): headroom for site growth, never unbounded
# 2026-07-10: the site's own published methodology pages (Fact-Checking
# Process, How We Test) -- confirmed live via the WP REST API at the time
# this was written. Only the SLUGS are fixed here (stable, foundational
# site pages, not rotating article content); the actual URL is still
# fetched LIVE at write time, never hardcoded -- same POINT-4 rule as
# fetch_real_posts() above, so a future slug/rename can never silently
# produce a dead link the way the old static INTERNAL_LINKS dict did.
_METHODOLOGY_SLUGS = ("fact-checking-process", "how-we-test")

# OBSERVABILITY (2026-07-11, PR express): a bare str(HTTPError) is just "HTTP
# Error 403: Forbidden" -- real finding, witness run 7, 3/3 articles hit this on
# BOTH endpoints with zero further detail, leaving it undiagnosable whether a
# WAF is blocking the runner's IP (Hostinger's hCDN fronts this site -- see
# wp_diag.py, which already captures this on its own diagnostic path) or
# WordPress itself is rejecting the request for some other reason. Same
# observability principle as agent_04's own HTTP-400 body logging (#77):
# capture what's available NOW so the NEXT occurrence is diagnosable directly
# from the logs, without needing to reproduce it.
_DIAGNOSTIC_HEADERS = ("x-hcdn-request-id", "cf-ray", "server")


def _describe_http_error(e, body_limit=500):
    """Best-effort diagnostic string for an HTTPError: request-id/ray-id
    headers (if the response carried any) plus a bounded body snippet -- so a
    WAF challenge page (HTML) is distinguishable from a clean WordPress JSON
    error at a glance. Never raises; a non-HTTPError (timeout, DNS, connection
    refused, ...) falls back to plain str(e), unchanged from before."""
    if not isinstance(e, urllib.error.HTTPError):
        return str(e)
    parts = [str(e)]
    headers = e.headers or {}
    for h in _DIAGNOSTIC_HEADERS:
        v = headers.get(h)
        if v:
            parts.append(f"{h}={v}")
    # 2026-07-11 (PR express, challenge retry): _urlopen_with_challenge_retry
    # already reads the body ONCE to check for the Hostinger challenge
    # signature -- HTTPError.read() is a stream, calling it again here would
    # return nothing. Use the cached copy if this exception went through that
    # path; otherwise fall back to reading it fresh (unchanged prior behavior
    # for any HTTPError NOT wrapped by that helper).
    cached_body = getattr(e, "_wp_challenge_body", None)
    if cached_body is not None:
        if cached_body:
            parts.append(f"body={cached_body[:body_limit]!r}")
        return " | ".join(parts)
    try:
        body = e.read()
        if body:
            parts.append(f"body={body[:body_limit].decode('utf-8', errors='replace')!r}")
    except Exception:
        pass  # reading the body is a bonus, never let it mask the original error
    return " | ".join(parts)


def _urlopen_with_challenge_retry(url, timeout, agent_label):
    """urlopen() wrapped with the Hostinger hCDN challenge-403 backoff retry
    (2026-07-11, PR express -- see agents/_wp_challenge.py) plus a light,
    fixed pacing delay before every call. Returns (status, body_text) on any
    response the server actually sent (200 or otherwise); RE-RAISES the last
    urllib.error.HTTPError if it's a hard 403 (no challenge signature) or if
    challenge retries are exhausted -- callers keep their EXISTING
    except-Exception handling completely unchanged (including
    _describe_http_error(e), which still receives a real HTTPError)."""
    def _attempt():
        req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-14-agent04/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace"), None
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            e._wp_challenge_body = body  # cache: HTTPError.read() is a stream, consumed above
            return e.code, body, e

    time.sleep(INTER_CALL_SPACING_SECONDS)  # light preventive pacing before every WP call
    status, body, err = call_with_challenge_retry(
        _attempt, time.sleep,
        log_fn=lambda n, d: logger.warning(
            f"[AGENT-04] {agent_label}: WP challenge 403 detected, retry {n}/{len(RETRY_DELAYS_SECONDS)} in {d}s"),
    )
    if err is not None:
        raise err
    return status, body


_STOP = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "for", "on", "with",
    "as", "by", "is", "are", "be", "this", "that", "your", "you", "it", "at",
    "from", "will", "can", "their", "they", "we", "our", "best", "guide",
    "guides", "complete", "2026", "newcomers", "immigrants", "canada", "usa",
    "how", "what", "new",
}
_WORD_RE = re.compile(r"[a-z0-9]+")


def fetch_real_posts(endpoint=POSTS_ENDPOINT, timeout=_TIMEOUT_SECONDS, max_pages=_MAX_PAGES):
    """Return [{"title": str, "url": str}, ...] for every published post
    reachable via the public WP REST API, or [] on ANY failure. Never raises,
    never falls back to a hardcoded list (see module docstring)."""
    posts = []
    for page in range(1, max_pages + 1):
        url = f"{endpoint}?_fields=slug,link,title&per_page={_PER_PAGE}&page={page}"
        try:
            status, body = _urlopen_with_challenge_retry(url, timeout, "internal links")
            if status != 200:
                logger.warning(f"[AGENT-04] SKIP internal links: WP REST API returned "
                               f"{status} at page {page} ({url})")
                break
            batch = json.loads(body)
        except Exception as e:
            if page == 1:
                logger.warning(f"[AGENT-04] SKIP internal links: WP REST API unreachable "
                               f"({endpoint}): {_describe_http_error(e)}")
                return []
            logger.warning(f"[AGENT-04] internal links: stopped paginating at page {page} "
                           f"({_describe_http_error(e)})")
            break
        if not isinstance(batch, list) or not batch:
            break
        for item in batch:
            raw_title = item.get("title", "")
            title = raw_title.get("rendered", "") if isinstance(raw_title, dict) else raw_title
            link = item.get("link", "")
            if title and link:
                posts.append({"title": title, "url": link})
        if len(batch) < _PER_PAGE:
            break
    return posts


def fetch_methodology_links(endpoint=PAGES_ENDPOINT, slugs=_METHODOLOGY_SLUGS, timeout=_TIMEOUT_SECONDS):
    """Return [{"title": str, "url": str}, ...] for the site's own published
    methodology pages, confirmed LIVE via the WP REST API right now -- or []
    on ANY failure (unreachable, non-200, malformed JSON, a slug no longer
    published). Never invents a URL, never falls back to a hardcoded link
    (same rule as fetch_real_posts): a genuinely missing/renamed page simply
    means zero methodology links for this run, not a stale guess."""
    slug_param = ",".join(slugs)
    url = f"{endpoint}?slug={slug_param}&_fields=slug,link,title&status=publish"
    try:
        status, body = _urlopen_with_challenge_retry(url, timeout, "methodology links")
        if status != 200:
            logger.warning(f"[AGENT-04] SKIP methodology links: WP REST API returned "
                           f"{status} ({url})")
            return []
        batch = json.loads(body)
    except Exception as e:
        logger.warning(f"[AGENT-04] SKIP methodology links: WP REST API unreachable ({endpoint}): "
                       f"{_describe_http_error(e)}")
        return []
    if not isinstance(batch, list):
        return []
    links = []
    for item in batch:
        raw_title = item.get("title", "")
        title = raw_title.get("rendered", "") if isinstance(raw_title, dict) else raw_title
        link = item.get("link", "")
        if title and link:
            links.append({"title": title, "url": link})
    return links


def _tokens(text):
    return {w for w in _WORD_RE.findall((text or "").lower()) if w not in _STOP and len(w) > 2}


def diagnose_relevance(article_title, real_posts, min_overlap=2, min_ratio=0.5, top_n=3):
    """Diagnostic companion to select_relevant_links: reports what was fetched
    and -- for visibility when the selected count comes up short of a tier's
    target -- the best-ratio REJECTED candidates (posts that shared some
    words but didn't clear both floors). Read-only, never affects selection."""
    query_tokens = _tokens(article_title)
    scored = []
    for post in real_posts:
        overlap = len(query_tokens & _tokens(post.get("title", "")))
        ratio = (overlap / len(query_tokens)) if query_tokens else 0.0
        scored.append((overlap, ratio, post))
    scored.sort(key=lambda t: t[1], reverse=True)
    rejected = [
        {"title": post["title"], "overlap": overlap, "ratio": round(ratio, 2)}
        for overlap, ratio, post in scored
        if not (overlap >= min_overlap and ratio >= min_ratio)
    ]
    return {
        "real_posts_fetched": len(real_posts),
        "min_overlap": min_overlap,
        "min_ratio": min_ratio,
        "top_rejected": rejected[:top_n],
    }


def select_relevant_links(article_title, real_posts, n=3, min_overlap=2, min_ratio=0.5):
    """Deterministic keyword-overlap match: score each real post by how many
    significant words it shares with the article's own title/keyword, keep
    only posts meeting BOTH min_overlap (absolute floor) AND min_ratio
    (RELATIVE floor: overlap / len(query_tokens)) -- an absolute count alone
    lets a rich-vocabulary query (e.g. "car insurance foreign drivers
    international students", 6 distinctive words) "match" on just 2
    incidental shared words ("international", "students") while sharing
    NONE of its actual topic ("car"/"insurance"/"drivers"/"foreign") --
    exactly the hair-splitting match the ratio floor rejects (real control-run
    case: ratio 0.33, below the 0.5 floor -> correctly zero links). Returns
    the top `n` as [{"title","url"}]. Zero posts clearing BOTH bars -> [] --
    no forced or tenuously-related link is ever inserted just to fill a
    quota."""
    query_tokens = _tokens(article_title)
    if not query_tokens:
        return []
    scored = []
    for post in real_posts:
        overlap = len(query_tokens & _tokens(post.get("title", "")))
        ratio = overlap / len(query_tokens)
        if overlap >= min_overlap and ratio >= min_ratio:
            scored.append((overlap, post))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [post for _score, post in scored[:n]]
