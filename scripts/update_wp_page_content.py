"""Write action: updates a WordPress PAGE's content and, optionally, disables
Elementor's control over it by clearing the _elementor_edit_mode meta (falls
back to the theme's normal page template rendering post_content). Requires
the page to currently be 'publish' (guards against operating on the wrong
page) and requires CONFIRM=yes to actually write, as a deliberate safety gate
for this higher-stakes, page-level (not post-level) write.

Used for the Start Here redesign (2026-07-13) -- see backup_wp_page.py for
the pre-change snapshot this assumes has already been taken.
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


def update_page(wp_url, user, app_password, page_id, new_content, disable_elementor):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}"
    payload = {"content": new_content}
    if disable_elementor:
        payload["meta"] = {"_elementor_edit_mode": ""}
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
    disable_elementor = os.environ.get("DISABLE_ELEMENTOR", "false").lower() == "true"
    confirm = os.environ.get("CONFIRM", "").lower() == "yes"

    with open(content_path, encoding="utf-8") as f:
        new_content = f.read()

    before = get_page(wp_url, user, app_pw, page_id)
    current_status = before.get("status")
    current_edit_mode = before.get("meta", {}).get("_elementor_edit_mode")
    print(f"BEFORE: id={page_id} status={current_status} elementor_edit_mode={current_edit_mode!r} "
          f"content_length={len(before.get('content', {}).get('raw', ''))}")

    if current_status != "publish":
        print(f"REFUSING: page {page_id} is currently '{current_status}', not 'publish'. Aborting.")
        sys.exit(1)

    if not confirm:
        print("REFUSING: CONFIRM=yes not set. This is a deliberate safety gate for a live page edit. Aborting without writing.")
        sys.exit(1)

    status_code, result = update_page(wp_url, user, app_pw, page_id, new_content, disable_elementor)
    if status_code not in (200, 201):
        print(f"UPDATE FAILED: HTTP {status_code}: {result}")
        sys.exit(1)

    print(f"AFTER: id={result.get('id')} status={result.get('status')} "
          f"elementor_edit_mode={result.get('meta', {}).get('_elementor_edit_mode')!r} "
          f"content_length={len(result.get('content', {}).get('raw', ''))}")
    print(f"SUCCESS: page {page_id} content updated" + (", Elementor edit mode cleared" if disable_elementor else ""))


if __name__ == "__main__":
    main()
