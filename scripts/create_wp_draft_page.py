"""Write action: creates a NEW WordPress page with status='draft' (hardcoded,
never configurable -- this script can never publish). Used to build mirror/
test pages without touching any existing live post or page.

Part of the calculator-restoration workstream (2026-08-08): building a Draft
mirror of the recovered "New Expat Monthly Budget Simulator" widget to
verify visually and functionally before any live merge into posts 1641/1624.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request


def create_draft_page(wp_url, user, app_password, title, slug, content):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/pages"
    payload = {
        "title": title,
        "slug": slug,
        "content": content,
        "status": "draft",  # hardcoded -- this script can never publish
    }
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
    title = os.environ["PAGE_TITLE"]
    slug = os.environ["PAGE_SLUG"]
    content_path = os.environ["CONTENT_FILE"]

    with open(content_path, encoding="utf-8") as f:
        content = f.read()

    status_code, result = create_draft_page(wp_url, user, app_pw, title, slug, content)
    if status_code not in (200, 201):
        print(f"CREATE FAILED: HTTP {status_code}: {result}")
        sys.exit(1)

    print(f"SUCCESS: draft page created — id={result.get('id')} status={result.get('status')} "
          f"slug={result.get('slug')} link={result.get('link')}")
    if result.get("status") != "draft":
        print("ATTENTION: page status is not 'draft' -- verify manually before doing anything else.")
        sys.exit(1)


if __name__ == "__main__":
    main()
