"""Read-only diagnostic: discovers the REAL field shape Yoast SEO uses for
its REST Bulk Editor mechanism, for ONE WordPress Page.

Part of the published-content audit workstream (separate from the article-
generation pipeline). This script performs ONLY HTTP GET requests -- it
contains no POST/PUT/PATCH/DELETE call of any kind, to WordPress or to
Yoast, and cannot write, modify, or delete anything.

Why this exists: the standard WP REST `meta` field does not expose any
Yoast field on this install (confirmed separately, unauthenticated, via
`OPTIONS /wp-json/wp/v2/pages`). Yoast instead exposes its own dedicated
REST route pair used by its SEO > Tools > Bulk Editor screen:
  - GET  /yoast/v1/bulk_editor/posts   (read current title/description rows)
  - POST /yoast/v1/bulk_editor/update_search  (write them -- NOT used here)
This script calls ONLY the GET route, to observe the exact JSON shape of
one page's row (field names, current stored value, any additional
identifiers Yoast requires) before any write tool is designed or built.
That write tool (Phase B) is a separate, not-yet-built script -- this file
does not attempt it and never will.

Usage: set PAGE_ID env var to the target WordPress page ID.
"""
import base64
import json
import os
import urllib.request
import urllib.parse


def get_json(url, auth_header=None):
    headers = {"Accept": "application/json"}
    if auth_header:
        headers["Authorization"] = auth_header
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        status = resp.status
        content_type = resp.headers.get("Content-Type", "")
        body = resp.read().decode("utf-8")
    return status, content_type, body


def main():
    wp_url = os.environ["WORDPRESS_URL"].rstrip("/")
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    page_id = int(os.environ["PAGE_ID"])

    auth = base64.b64encode(f"{user}:{app_pw}".encode()).decode()
    auth_header = f"Basic {auth}"

    report = {"page_id": page_id}

    # Step 1: confirm the page's own identity via the standard, already-used
    # REST endpoint (read-only GET, context=edit for the raw title field).
    core_url = f"{wp_url}/wp-json/wp/v2/pages/{page_id}?context=edit"
    status, ctype, body = get_json(core_url, auth_header)
    core_data = json.loads(body)
    report["core_page_get"] = {
        "endpoint": core_url,
        "http_status": status,
        "content_type": ctype,
        "id": core_data.get("id"),
        "slug": core_data.get("slug"),
        "status_field": core_data.get("status"),
        "title_raw": core_data.get("title", {}).get("raw"),
        "modified": core_data.get("modified"),
    }

    # Step 2: fetch ALL pages from Yoast's bulk-editor GET route (there are
    # only ~21 published pages on this site, well under one page of
    # results at per_page=100) and locate our target page_id's row inside
    # it -- avoids relying on the `search` param's unknown matching
    # behaviour (title text vs slug is not documented in the route schema).
    bulk_url = (
        f"{wp_url}/wp-json/yoast/v1/bulk_editor/posts"
        f"?content_type=page&per_page=100&page=1"
    )
    status2, ctype2, body2 = get_json(bulk_url, auth_header)
    report["bulk_editor_get"] = {
        "endpoint": bulk_url,
        "http_status": status2,
        "content_type": ctype2,
    }

    try:
        bulk_data = json.loads(body2)
    except json.JSONDecodeError:
        bulk_data = None
        report["bulk_editor_get"]["raw_body_unparsed"] = body2[:2000]

    report["bulk_editor_get"]["top_level_type"] = type(bulk_data).__name__
    if isinstance(bulk_data, dict):
        report["bulk_editor_get"]["top_level_keys"] = list(bulk_data.keys())
        # Common Yoast shapes: {"posts": [...], "total": N} or similar.
        list_candidate = None
        for k, v in bulk_data.items():
            if isinstance(v, list):
                list_candidate = (k, v)
                break
        if list_candidate:
            key, items = list_candidate
            report["bulk_editor_get"]["list_field_name"] = key
            report["bulk_editor_get"]["list_length"] = len(items)
            if items:
                report["bulk_editor_get"]["one_item_keys"] = list(items[0].keys())
            match = None
            for item in items:
                item_id = item.get("id") or item.get("ID") or item.get("post_id")
                if item_id == page_id:
                    match = item
                    break
            report["bulk_editor_get"]["target_page_found"] = match is not None
            report["bulk_editor_get"]["target_page_row"] = match
    elif isinstance(bulk_data, list):
        report["bulk_editor_get"]["list_length"] = len(bulk_data)
        if bulk_data:
            report["bulk_editor_get"]["one_item_keys"] = list(bulk_data[0].keys())
        match = None
        for item in bulk_data:
            item_id = item.get("id") or item.get("ID") or item.get("post_id")
            if item_id == page_id:
                match = item
                break
        report["bulk_editor_get"]["target_page_found"] = match is not None
        report["bulk_editor_get"]["target_page_row"] = match

    out_path = f"yoast_discovery_page_{page_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Saved {out_path}")
    print("core page GET status:", status)
    print("bulk editor GET status:", status2)
    print("bulk editor top-level type:", report["bulk_editor_get"]["top_level_type"])
    print("bulk editor top-level keys:", report["bulk_editor_get"].get("top_level_keys"))
    print("target page found in bulk editor list:", report["bulk_editor_get"].get("target_page_found"))
    print("target page row:", json.dumps(report["bulk_editor_get"].get("target_page_row"), indent=2))


if __name__ == "__main__":
    main()
