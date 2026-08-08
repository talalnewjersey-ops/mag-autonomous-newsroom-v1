"""Write action: updates an EXISTING WordPress page's content, but only if
its current status is already 'draft' -- refuses otherwise. Symmetric
safety gate to create_wp_draft_page.py (which hardcodes status=draft on
create); this one hardcodes a status CHECK on update, so it can never be
pointed at a live page by mistake.

Part of the calculator-restoration workstream (2026-08-08).
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request


def get_page(wp_url, user, app_password, page_id):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}?context=edit"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def update_page_content(wp_url, user, app_password, page_id, new_content):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}"
    payload = {"content": new_content, "status": "draft"}  # re-assert draft on every write
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    page_id = os.environ["PAGE_ID"]
    content_path = os.environ["CONTENT_FILE"]

    with open(content_path, encoding="utf-8") as f:
        new_content = f.read()

    before = get_page(wp_url, user, app_pw, page_id)
    current_status = before.get("status")
    print(f"BEFORE: id={page_id} status={current_status} content_length={len(before.get('content', {}).get('raw', ''))}")

    if current_status != "draft":
        print(f"REFUSING: page {page_id} is currently '{current_status}', not 'draft'. Aborting.")
        sys.exit(1)

    status_code, result = update_page_content(wp_url, user, app_pw, page_id, new_content)
    if status_code not in (200, 201):
        print(f"UPDATE FAILED: HTTP {status_code}: {result}")
        sys.exit(1)

    print(f"AFTER: id={result.get('id')} status={result.get('status')} content_length={len(result.get('content', {}).get('raw', ''))}")
    if result.get("status") != "draft":
        print("ATTENTION: page status is not 'draft' after update -- verify manually.")
        sys.exit(1)
    print(f"SUCCESS: page {page_id} content updated, status remains draft")


if __name__ == "__main__":
    main()
