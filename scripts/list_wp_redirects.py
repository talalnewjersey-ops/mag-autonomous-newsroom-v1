"""Read-only diagnostic: lists all redirects registered in the Redirection
plugin via its REST API -- id, source url, target, status -- optionally
filtered to a single source path. Never writes anything.

Added 2026-07-28 to identify an existing redirect's exact id/target before
deciding whether it needs updating (create_redirects_batch.py can only
create or skip, never update an existing rule).
"""
import base64
import json
import os
import urllib.request


def fetch_all_redirects(wp_url, user, app_password, per_page=200):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    items = []
    page_num = 0
    while True:
        url = (f"{wp_url.rstrip('/')}/wp-json/redirection/v1/redirect"
               f"?per_page={per_page}&page={page_num}")
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        batch = data.get("items", [])
        if not batch:
            break
        items.extend(batch)
        if len(batch) < per_page:
            break
        page_num += 1
    return items


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    filter_source = os.environ.get("FILTER_SOURCE", "").strip()

    items = fetch_all_redirects(wp_url, user, app_pw)
    print(f"Total redirects: {len(items)}")

    for r in items:
        url = r.get("url", "")
        if filter_source and filter_source.strip("/").lower() not in url.strip("/").lower():
            continue
        target = r.get("action_data", {}).get("url", "")
        print(f"id={r.get('id')} enabled={r.get('enabled')} status={r.get('status')} "
              f"url={url!r} -> target={target!r} code={r.get('action_code')}")


if __name__ == "__main__":
    main()
