"""Read-only diagnostic: fetches ONE WordPress post's full raw content
(title, content, excerpt -- unrendered, exactly as stored) via the REST API,
authenticated with context=edit so the raw fields are available.

Part of the published-content audit workstream (separate from the article-
generation pipeline). Never writes to WordPress. Used to inspect an
article's exact current text before proposing a one-article-at-a-time edit,
and to produce the pre-edit backup the user requires.
"""
import base64
import json
import os
import urllib.request


def fetch_post(wp_url, user, app_password, post_id):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}?context=edit"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    post_id = os.environ["POST_ID"]

    data = fetch_post(wp_url, user, app_pw, post_id)

    out_path = f"post_{post_id}_full.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved {out_path}")
    print("id:", data.get("id"))
    print("slug:", data.get("slug"))
    print("status:", data.get("status"))
    print("title:", data.get("title", {}).get("raw"))
    print("content length:", len(data.get("content", {}).get("raw", "")))
    print("excerpt raw:", data.get("excerpt", {}).get("raw", "")[:300])


if __name__ == "__main__":
    main()
