"""One-off: create a NEW WordPress post from a checked-in spec, ALWAYS as
status=draft. Part of the manual/audit content workstream -- separate from
the automated pipeline (agent_11_wordpress_integration.py), used when a
post is authored directly (e.g. via a validated research+draft mission)
rather than through the full agent pipeline.

Fix-file shape (JSON): {"title": str, "slug": str, "content_file": str,
"category_id": int, "yoast_title": str, "yoast_metadesc": str,
"yoast_focuskw": str}

Safety: hardcodes status="draft" in the create payload -- there is no way
to pass a different status through this script's fix-file schema, so it
cannot publish by construction, not just by convention.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request


def create_post(wp_url, user, app_password, payload):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
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
    fix_path = os.environ["FIX_FILE"]

    with open(fix_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    with open(spec["content_file"], "r", encoding="utf-8") as f:
        content = f.read()

    payload = {
        "title": spec["title"],
        "slug": spec["slug"],
        "content": content,
        "status": "draft",  # hardcoded -- this script cannot publish
        "categories": [spec["category_id"]] if spec.get("category_id") else [],
        "meta": {
            "_yoast_wpseo_title": spec["yoast_title"],
            "_yoast_wpseo_metadesc": spec["yoast_metadesc"],
            "_yoast_wpseo_focuskw": spec["yoast_focuskw"],
        },
    }

    status_code, result = create_post(wp_url, user, app_pw, payload)
    if status_code not in (200, 201):
        print(f"CREATE FAILED: HTTP {status_code}: {result}")
        sys.exit(1)

    print(f"CREATED: id={result.get('id')} status={result.get('status')!r} "
          f"title={result.get('title', {}).get('raw', '')!r} slug={result.get('slug', '')!r} "
          f"link={result.get('link', '')!r}")

    if result.get("status") != "draft":
        print(f"CRITICAL: created post status is {result.get('status')!r}, NOT 'draft' -- investigate immediately.")
        sys.exit(1)

    print("SUCCESS: new post created as draft. NOT published.")

    with open(f"post_{result.get('id')}_created.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
