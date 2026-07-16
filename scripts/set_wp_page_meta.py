"""Write action: sets one or more meta fields on a WordPress PAGE via the
standard REST meta update mechanism (same POST {"meta": {...}} pattern
update_wp_page_content.py uses for _elementor_edit_mode). Requires the page
to currently be 'publish' and CONFIRM=yes, as a deliberate safety gate for
a live page edit. Prints BEFORE/AFTER values for every key touched so a
silently-ignored (non-REST-writable) key is obvious in the log.
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


def update_meta(wp_url, user, app_password, page_id, meta):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}"
    data = json.dumps({"meta": meta}).encode("utf-8")
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
    meta = json.loads(os.environ["META_JSON"])
    confirm = os.environ.get("CONFIRM", "").lower() == "yes"

    before = get_page(wp_url, user, app_pw, page_id)
    current_status = before.get("status")
    print(f"BEFORE: id={page_id} status={current_status}")
    for k in meta:
        print(f"  {k} = {before.get('meta', {}).get(k)!r}")

    if current_status != "publish":
        print(f"REFUSING: page {page_id} is currently '{current_status}', not 'publish'. Aborting.")
        sys.exit(1)

    if not confirm:
        print("REFUSING: CONFIRM=yes not set. This is a deliberate safety gate for a live page edit. Aborting without writing.")
        sys.exit(1)

    status_code, result = update_meta(wp_url, user, app_pw, page_id, meta)
    if status_code not in (200, 201):
        print(f"UPDATE FAILED: HTTP {status_code}: {result}")
        sys.exit(1)

    print(f"AFTER: id={result.get('id')} status={result.get('status')}")
    for k in meta:
        after_val = result.get("meta", {}).get(k)
        ok = after_val == meta[k]
        print(f"  {k} = {after_val!r} {'OK' if ok else 'MISMATCH -- key may not be REST-writable'}")
    print("SUCCESS: meta update request completed")


if __name__ == "__main__":
    main()
