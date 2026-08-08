"""Write action: creates a temporary Code Snippet that registers a REST
route purging LiteSpeed cache for ONE specific post ID only (via
do_action('litespeed_purge_post', $post_id) -- LiteSpeed's own targeted
purge hook, not a site-wide purge-all). Calls it once, then deletes the
temporary snippet again. Mirrors the safety pattern of
purge_litespeed_cache.py (minimize standing PHP-execution surface) but
targeted instead of global, per explicit user instruction not to purge
site-wide for a single-page test. Requires CONFIRM=yes.
"""
import base64
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request

_orig_getaddrinfo = socket.getaddrinfo
def _force_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _force_ipv4


def _auth_header(user, app_password):
    return "Basic " + base64.b64encode(f"{user}:{app_password}".encode()).decode()


def create_snippet(wp_url, user, app_password, post_id):
    code = f"""<?php
add_action('rest_api_init', function() {{
    register_rest_route('mag/v1', '/purge-post-{post_id}', [
        'methods' => 'POST',
        'callback' => function() {{
            do_action('litespeed_purge_post', {post_id});
            return ['status' => 'purged', 'post_id' => {post_id}, 'time' => time()];
        }},
        'permission_callback' => function() {{ return current_user_can('manage_options'); }}
    ]);
}});
"""
    url = f"{wp_url.rstrip('/')}/wp-json/code-snippets/v1/snippets"
    payload = json.dumps({
        "name": f"TEMP purge-post-{post_id} (delete after use)",
        "desc": "One-off targeted LiteSpeed purge, created and deleted by purge_litespeed_cache_by_post.py",
        "code": code,
        "scope": "global",
        "active": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Authorization": _auth_header(user, app_password), "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def call_purge(wp_url, user, app_password, post_id):
    url = f"{wp_url.rstrip('/')}/wp-json/mag/v1/purge-post-{post_id}"
    req = urllib.request.Request(
        url, data=b"{}", method="POST",
        headers={"Authorization": _auth_header(user, app_password), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"raw": body[:500]}


def delete_snippet(wp_url, user, app_password, snippet_id):
    url = f"{wp_url.rstrip('/')}/wp-json/code-snippets/v1/snippets/{snippet_id}"
    req = urllib.request.Request(url, method="DELETE", headers={"Authorization": _auth_header(user, app_password)})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    post_id = os.environ["POST_ID"]
    confirm = os.environ.get("CONFIRM", "").lower() == "yes"

    if not confirm:
        print("REFUSING: CONFIRM=yes not set. Aborting without writing.")
        sys.exit(1)

    print(f"Creating temporary targeted-purge snippet for post {post_id}...")
    snippet = create_snippet(wp_url, user, app_pw, post_id)
    snippet_id = snippet.get("id")
    print(f"  created id={snippet_id} active={snippet.get('active')}")

    time.sleep(2)

    print(f"Calling purge-post-{post_id}...")
    status, body = call_purge(wp_url, user, app_pw, post_id)
    print(f"  HTTP {status}: {body}")

    print(f"Deleting temporary snippet {snippet_id}...")
    del_status = delete_snippet(wp_url, user, app_pw, snippet_id)
    print(f"  delete HTTP {del_status}")

    if status not in (200, 201):
        print("PURGE CALL FAILED (temp snippet deleted regardless -- see status above)")
        sys.exit(1)

    print(f"SUCCESS: targeted purge triggered for post {post_id}, temporary snippet removed")


if __name__ == "__main__":
    main()
