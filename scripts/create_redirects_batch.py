"""Write action: creates multiple 301 redirects via the Redirection plugin's
REST API in one run, from a checked-in JSON spec (audit/pending_redirects/
<name>.json: [{"source": "/old-slug/", "target": "/new-slug/"}, ...]).

Part of the pre-production 404 audit cleanup. Same house convention as
apply_single_post_fix.py: the exact list to create is versioned in git
(auditable), not passed as a raw CLI arg. Skips (does not fail the whole
batch) any source that already has an enabled redirect -- idempotent to
re-run.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

REDIRECTION_GROUP_ID = 1  # matches all 95 pre-existing redirects on this site


def _auth_header(user, app_password):
    return "Basic " + base64.b64encode(f"{user}:{app_password}".encode()).decode()


def get_existing_redirects(wp_url, user, app_password):
    url = f"{wp_url.rstrip('/')}/wp-json/redirection/v1/redirect?per_page=200"
    req = urllib.request.Request(url, headers={"Authorization": _auth_header(user, app_password)})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return {r["url"].strip("/").lower() for r in data.get("items", []) if r.get("enabled")}


def create_redirect(wp_url, user, app_password, source_path, target_url):
    url = f"{wp_url.rstrip('/')}/wp-json/redirection/v1/redirect"
    payload = json.dumps({
        "url": source_path, "match_type": "url", "action_type": "url",
        "action_code": 301, "action_data": {"url": target_url},
        "group_id": REDIRECTION_GROUP_ID,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST",
        headers={"Authorization": _auth_header(user, app_password), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    spec_path = os.environ["SPEC_FILE"]

    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    existing = get_existing_redirects(wp_url, user, app_pw)
    created, skipped, failed = [], [], []

    for entry in spec:
        source = entry["source"].strip("/").lower()
        target = entry["target"]
        if source in existing:
            print(f"SKIP (already exists): {entry['source']}")
            skipped.append(entry)
            continue
        try:
            result = create_redirect(wp_url, user, app_pw, entry["source"], target)
            print(f"CREATED: {entry['source']} -> {target} (id={result.get('id')})")
            created.append(entry)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"FAILED: {entry['source']} -> {target} (HTTP {e.code}): {body}")
            failed.append(entry)

    print(f"\nSUMMARY: created={len(created)} skipped={len(skipped)} failed={len(failed)} total={len(spec)}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
