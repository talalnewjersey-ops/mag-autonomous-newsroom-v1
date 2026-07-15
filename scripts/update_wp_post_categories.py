"""Write action: replaces ONE published post's categories via the REST API.
Narrowly scoped -- touches only the `categories` field, never content or
status. Requires CONFIRM=yes. Prints the before/after category names (not
just IDs) so a misconfigured category ID is caught before/after the write,
not silently applied.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request


def _auth_header(user, app_password):
    return "Basic " + base64.b64encode(f"{user}:{app_password}".encode()).decode()


def get_post(wp_url, user, app_password, post_id):
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}?context=edit"
    req = urllib.request.Request(url, headers={"Authorization": _auth_header(user, app_password)})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_categories(wp_url, user, app_password):
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/categories?per_page=100"
    req = urllib.request.Request(url, headers={"Authorization": _auth_header(user, app_password)})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return {c["id"]: c["name"] for c in json.loads(resp.read().decode("utf-8"))}


def update_categories(wp_url, user, app_password, post_id, new_category_ids):
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    payload = json.dumps({"categories": new_category_ids}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Authorization": _auth_header(user, app_password), "Content-Type": "application/json"},
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
    post_id = os.environ["POST_ID"]
    new_category_ids = [int(x) for x in os.environ["NEW_CATEGORY_IDS"].split(",") if x.strip()]
    confirm = os.environ.get("CONFIRM", "").lower() == "yes"

    cat_names = get_categories(wp_url, user, app_pw)
    before = get_post(wp_url, user, app_pw, post_id)
    before_cats = before.get("categories", [])
    print(f"BEFORE: id={post_id} title={before.get('title', {}).get('rendered')!r} "
          f"status={before.get('status')} categories={before_cats} -> {[cat_names.get(c) for c in before_cats]}")
    print(f"REQUESTED: categories={new_category_ids} -> {[cat_names.get(c) for c in new_category_ids]}")

    if before.get("status") != "publish":
        print(f"REFUSING: post {post_id} is currently '{before.get('status')}', not 'publish'. Aborting.")
        sys.exit(1)

    if not confirm:
        print("REFUSING: CONFIRM=yes not set. Aborting without writing.")
        sys.exit(1)

    status_code, result = update_categories(wp_url, user, app_pw, post_id, new_category_ids)
    if status_code not in (200, 201):
        print(f"UPDATE FAILED: HTTP {status_code}: {result}")
        sys.exit(1)

    after_cats = result.get("categories", [])
    print(f"AFTER: id={result.get('id')} categories={after_cats} -> {[cat_names.get(c) for c in after_cats]}")
    print(f"SUCCESS: post {post_id} categories updated")


if __name__ == "__main__":
    main()
