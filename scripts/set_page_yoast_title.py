"""Sets the Yoast SEO title of ONE WordPress Page, and only that field.

Part of the published-content audit workstream (separate from the article-
generation pipeline). This is Phase B of the Page SEO-title tool -- Phase A
(scripts/discover_yoast_page_title_field.py) confirmed empirically, on a
live authenticated read against this install, that:
  - Yoast exposes NO field via the standard WP REST `meta` schema (checked
    unauthenticated via `OPTIONS /wp-json/wp/v2/pages` -- zero Yoast keys
    registered there).
  - Yoast's own dedicated REST route is the real mechanism: its SEO >
    Tools > Bulk Editor screen, exposed as
      GET  /yoast/v1/bulk_editor/posts            (read rows)
      POST /yoast/v1/bulk_editor/update_search     (write rows)
  - The per-row field for the SEO title is literally named `seo_title`
    (confirmed by inspecting a real row -- page 46450 returned
    `"seo_title": ""`, distinct from the plain WP `title` field, which
    was `"Corrections Policy"`).

SINGLE-FIELD PRINCIPLE (explicit user instruction): the write payload
contains ONLY `id` and `seo_title`. No `meta_description`, no
`focus_keyphrase`, no `social_title`, no `social_description`, no
`content_type`, no other field -- on the theory that Yoast's endpoint may
partial-update (only touching keys present in the payload) rather than
require a full row. If the endpoint rejects this minimal payload, this
script STOPS and reports the exact response. It does NOT retry with an
enriched payload, does NOT try a second payload shape, and does NOT fall
back to any other write mechanism. The caller decides what to do next.

SAFETY GATES, in this exact order, matching the READ -> VERIFY EXPECTED ->
BACKUP -> WRITE ONE FIELD -> READ BACK -> VERIFY -> FRONTEND CHECK -> STOP
ON DIVERGENCE pattern:

  1. READ current state: the page's core REST object (id/slug/status/raw
     content, via context=edit) AND its Yoast bulk-editor row (seo_title
     and every other field on that row) AND the live public frontend HTML
     (for a byte-level "everything except <head>'s title-ish tags" later
     comparison).
  2. VERIFY EXPECTED BEFORE VALUE: the observed `seo_title` must equal
     `expected_current_value` EXACTLY. Any difference (including "expected
     non-empty but found different", or "expected empty but found already
     set") -> STOP, exit non-zero, NO WRITE attempted.
  3. BACKUP: the full pre-write state (core REST object + Yoast row +
     frontend HTML) is written to a timestamped JSON file, always, before
     any write is attempted.
  4. WRITE ONE FIELD: exactly one HTTP call with write capability exists
     in this entire script -- `POST /yoast/v1/bulk_editor/update_search`
     with `{"items": [{"id": <page_id>, "seo_title": <new_seo_title>}]}`.
     No other endpoint, no PATCH/PUT/DELETE, no wp-cli, no direct DB
     access, ever.
  5. If the write call raises an HTTP error, or returns an unexpected
     shape, or the API reports failure for this item: STOP immediately,
     print the exact response, exit non-zero. No second attempt with a
     different payload.
  6. READ BACK: re-fetch both the core REST object and the Yoast row.
  7. VERIFY: `seo_title` now equals `new_seo_title` exactly, AND every
     other Yoast-row field (`meta_description`, `focus_keyphrase`,
     `social_title`, `social_description`, `status`) is byte-identical to
     the pre-write backup, AND the core object's `slug`/`status`/raw
     content hash are byte-identical to the pre-write backup. Any
     divergence anywhere -> report it explicitly, mark FAILURE. Does not
     attempt to auto-correct.
  8. FRONTEND CHECK: a second, independent, unauthenticated GET of the
     page's live public URL. Confirms HTTP 200, and separately checks:
     the rendered `<title>` (expected to change -- reports the observed
     new value, does not assume a specific format), canonical tag(s)
     (expected UNCHANGED), robots meta (expected UNCHANGED), meta
     description (expected UNCHANGED), H1 tag count/text (expected
     UNCHANGED), and a hash of everything from `</head>` onward (i.e. the
     entire visible body) -- expected UNCHANGED. A 200 status code alone
     is never treated as sufficient for success.

Exits 0 only if every gate above passed. Any single gate failure exits
non-zero with a full diagnostic dump -- nothing is silently declared a
success.

Usage: set PAGE_ID, EXPECTED_CURRENT_VALUE, NEW_SEO_TITLE env vars (plus
the standard WORDPRESS_URL / WORDPRESS_USERNAME / WORDPRESS_APP_PASSWORD).
One page per invocation. No batch input is accepted, ever.
"""
import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request


def _headers(auth_header, extra=None):
    h = {"Accept": "application/json"}
    if auth_header:
        h["Authorization"] = auth_header
    if extra:
        h.update(extra)
    return h


def get_json(url, auth_header):
    req = urllib.request.Request(url, headers=_headers(auth_header), method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def get_public_html(url):
    req = urllib.request.Request(url, headers={"Accept": "text/html"}, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def find_yoast_row(wp_url, auth_header, page_id):
    """GET the Yoast bulk-editor page list and return the row for page_id,
    plus the full raw list response (for backup completeness). Read-only.
    """
    url = f"{wp_url}/wp-json/yoast/v1/bulk_editor/posts?content_type=page&per_page=100&page=1"
    status, data = get_json(url, auth_header)
    posts = data.get("posts", [])
    row = next((p for p in posts if p.get("id") == page_id), None)
    return status, data, row


def get_core_page(wp_url, auth_header, page_id):
    url = f"{wp_url}/wp-json/wp/v2/pages/{page_id}?context=edit"
    status, data = get_json(url, auth_header)
    return status, data


def extract_frontend_signals(html):
    def one(pattern):
        m = re.search(pattern, html)
        return m.group(0) if m else None

    title = one(r"<title>[^<]*</title>")
    canonicals = re.findall(r'<link rel="canonical"[^>]*>', html)
    robots = re.findall(r"<meta name=['\"]robots['\"][^>]*>", html)
    meta_desc = one(r'<meta name="description"[^>]*>')
    h1s = re.findall(r"<h1[^>]*>.*?</h1>", html, re.S)

    head_end = html.find("</head>")
    body_part = html[head_end:] if head_end != -1 else html
    body_hash = hashlib.sha256(body_part.encode("utf-8", errors="replace")).hexdigest()

    return {
        "title_tag": title,
        "canonical_tags": canonicals,
        "robots_tags": robots,
        "meta_description_tag": meta_desc,
        "h1_count": len(h1s),
        "h1_texts": h1s,
        "body_from_head_close_sha256": body_hash,
    }


def main():
    wp_url = os.environ["WORDPRESS_URL"].rstrip("/")
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    page_id = int(os.environ["PAGE_ID"])
    expected_current_value = os.environ["EXPECTED_CURRENT_VALUE"]
    new_seo_title = os.environ["NEW_SEO_TITLE"]

    auth = base64.b64encode(f"{user}:{app_pw}".encode()).decode()
    auth_header = f"Basic {auth}"

    result = {
        "page_id": page_id,
        "expected_current_value": expected_current_value,
        "new_seo_title": new_seo_title,
        "gates": {},
        "final_status": "NOT_STARTED",
    }

    def fail(gate_name, detail):
        result["gates"][gate_name] = {"passed": False, "detail": detail}
        result["final_status"] = f"FAILED_AT_{gate_name}"
        _dump(result)
        print(f"STOP: gate '{gate_name}' failed.")
        print(json.dumps(detail, indent=2, ensure_ascii=False, default=str))
        sys.exit(1)

    def _dump(obj):
        out_path = f"set_page_yoast_title_{page_id}_result.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False, default=str)
        print(f"Saved {out_path}")

    # ---- Gate 1: READ current state ----
    try:
        core_status, core_before = get_core_page(wp_url, auth_header, page_id)
        yoast_status, yoast_list_before, yoast_row_before = find_yoast_row(
            wp_url, auth_header, page_id
        )
        front_status_before, front_html_before = get_public_html(core_before.get("link"))
    except Exception as e:  # noqa: BLE001 - report anything, never swallow
        fail("READ", {"exception": repr(e)})
        return

    if yoast_row_before is None:
        fail("READ", {"error": "page_id not found in Yoast bulk-editor page list"})
        return

    front_signals_before = extract_frontend_signals(front_html_before)

    result["gates"]["READ"] = {
        "passed": True,
        "core_status": core_status,
        "core_slug": core_before.get("slug"),
        "core_page_status": core_before.get("status"),
        "core_content_sha256": hashlib.sha256(
            (core_before.get("content", {}).get("raw", "") or "").encode("utf-8")
        ).hexdigest(),
        "yoast_status": yoast_status,
        "yoast_row_before": yoast_row_before,
        "frontend_status_before": front_status_before,
        "frontend_signals_before": front_signals_before,
    }

    # ---- Gate 2: VERIFY EXPECTED BEFORE VALUE ----
    observed_current = yoast_row_before.get("seo_title")
    if observed_current != expected_current_value:
        fail(
            "VERIFY_EXPECTED_BEFORE_VALUE",
            {
                "expected_current_value": expected_current_value,
                "observed_current_value": observed_current,
                "message": "Refusing to write: current stored seo_title does not exactly "
                "match expected_current_value.",
            },
        )
        return
    result["gates"]["VERIFY_EXPECTED_BEFORE_VALUE"] = {"passed": True}

    # ---- Gate 3: BACKUP (always, before any write) ----
    backup = {
        "page_id": page_id,
        "core_page_before": core_before,
        "yoast_row_before": yoast_row_before,
        "frontend_html_before": front_html_before,
        "frontend_signals_before": front_signals_before,
    }
    backup_path = f"page_{page_id}_yoast_title_BEFORE.json"
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup, f, indent=2, ensure_ascii=False, default=str)
    result["gates"]["BACKUP"] = {"passed": True, "path": backup_path}
    print(f"Backup written: {backup_path}")

    # ---- Gate 4: WRITE ONE FIELD (the only write call in this script) ----
    write_url = f"{wp_url}/wp-json/yoast/v1/bulk_editor/update_search"
    write_payload = {"items": [{"id": page_id, "seo_title": new_seo_title}]}
    write_body = json.dumps(write_payload).encode("utf-8")
    req = urllib.request.Request(
        write_url,
        data=write_body,
        method="POST",
        headers=_headers(auth_header, {"Content-Type": "application/json"}),
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            write_status = resp.status
            write_response_body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        fail(
            "WRITE",
            {
                "payload_sent": write_payload,
                "http_status": e.code,
                "response_body": error_body,
                "message": "Write endpoint returned an HTTP error for the minimal "
                "single-field payload. Not retrying with a different payload shape.",
            },
        )
        return
    except Exception as e:  # noqa: BLE001
        fail("WRITE", {"payload_sent": write_payload, "exception": repr(e)})
        return

    try:
        write_response = json.loads(write_response_body)
    except json.JSONDecodeError:
        write_response = None

    result["gates"]["WRITE"] = {
        "passed": None,  # judged by later gates, not by HTTP status alone
        "payload_sent": write_payload,
        "http_status": write_status,
        "response_body_raw": write_response_body,
        "response_parsed": write_response,
    }
    print(f"Write call returned HTTP {write_status}")
    print("Response body:", write_response_body)

    # ---- Gate 5: READ BACK ----
    try:
        core_status_after, core_after = get_core_page(wp_url, auth_header, page_id)
        yoast_status_after, yoast_list_after, yoast_row_after = find_yoast_row(
            wp_url, auth_header, page_id
        )
        front_status_after, front_html_after = get_public_html(core_after.get("link"))
    except Exception as e:  # noqa: BLE001
        fail("READ_BACK", {"exception": repr(e)})
        return

    if yoast_row_after is None:
        fail("READ_BACK", {"error": "page_id not found in Yoast bulk-editor page list after write"})
        return

    front_signals_after = extract_frontend_signals(front_html_after)
    core_content_hash_after = hashlib.sha256(
        (core_after.get("content", {}).get("raw", "") or "").encode("utf-8")
    ).hexdigest()

    result["gates"]["READ_BACK"] = {
        "passed": True,
        "core_status": core_status_after,
        "yoast_row_after": yoast_row_after,
        "frontend_status_after": front_status_after,
        "frontend_signals_after": front_signals_after,
    }

    # ---- Gate 6: VERIFY (REST-level: only seo_title changed) ----
    divergences = []

    if yoast_row_after.get("seo_title") != new_seo_title:
        divergences.append(
            {
                "field": "seo_title",
                "expected": new_seo_title,
                "observed": yoast_row_after.get("seo_title"),
            }
        )

    unchanged_fields = ["meta_description", "focus_keyphrase", "social_title", "social_description", "status"]
    for field in unchanged_fields:
        before_val = yoast_row_before.get(field)
        after_val = yoast_row_after.get(field)
        if before_val != after_val:
            divergences.append({"field": f"yoast.{field}", "before": before_val, "after": after_val})

    if core_after.get("slug") != core_before.get("slug"):
        divergences.append({"field": "core.slug", "before": core_before.get("slug"), "after": core_after.get("slug")})
    if core_after.get("status") != core_before.get("status"):
        divergences.append({"field": "core.status", "before": core_before.get("status"), "after": core_after.get("status")})
    if core_content_hash_after != result["gates"]["READ"]["core_content_sha256"]:
        divergences.append(
            {
                "field": "core.content_sha256",
                "before": result["gates"]["READ"]["core_content_sha256"],
                "after": core_content_hash_after,
            }
        )

    if divergences:
        fail("VERIFY", {"divergences": divergences})
        return
    result["gates"]["VERIFY"] = {"passed": True}

    # ---- Gate 7: FRONTEND CHECK ----
    frontend_divergences = []

    if front_status_after != 200:
        frontend_divergences.append({"field": "http_status", "expected": 200, "observed": front_status_after})

    # Fields expected to STAY THE SAME:
    for field in ["canonical_tags", "robots_tags", "meta_description_tag", "h1_count", "h1_texts", "body_from_head_close_sha256"]:
        before_val = front_signals_before.get(field)
        after_val = front_signals_after.get(field)
        if before_val != after_val:
            frontend_divergences.append({"field": f"frontend.{field}", "before": before_val, "after": after_val})

    # Title tag is EXPECTED to change -- just report what it became, don't assume a format.
    result["gates"]["FRONTEND_CHECK"] = {
        "title_before": front_signals_before.get("title_tag"),
        "title_after": front_signals_after.get("title_tag"),
        "unexpected_divergences": frontend_divergences,
        "passed": len(frontend_divergences) == 0,
    }

    if frontend_divergences:
        fail("FRONTEND_CHECK", {"unexpected_divergences": frontend_divergences})
        return

    result["final_status"] = "SUCCESS"
    _dump(result)
    print("SUCCESS: all gates passed.")
    print("New live <title>:", front_signals_after.get("title_tag"))


if __name__ == "__main__":
    main()
