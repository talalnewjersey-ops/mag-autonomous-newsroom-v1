"""DESTRUCTIVE (but reversible by default): deletes ONE WordPress page via
the REST API. Moves to trash by default (recoverable from wp-admin);
FORCE=true bypasses trash. Mirrors delete_wp_post.py's fat-finger guard
(CONFIRM_PAGE_ID must equal PAGE_ID) but targets wp/v2/pages, not
wp/v2/posts, and refuses unless the page's current status is 'draft' --
this script is only meant for cleaning up test/mirror drafts that never
had a public URL, never a published page (no redirect logic needed or
provided).
"""
import base64
import json
import os
import socket
import sys
import urllib.error
import urllib.request

_orig_getaddrinfo = socket.getaddrinfo
def _force_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _force_ipv4


def _auth_header(user, app_password):
    return "Basic " + base64.b64encode(f"{user}:{app_password}".encode()).decode()


def get_page(wp_url, user, app_password, page_id):
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}?context=edit"
    req = urllib.request.Request(url, headers={"Authorization": _auth_header(user, app_password)})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def delete_page(wp_url, user, app_password, page_id, force=False):
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}"
    if force:
        url += "?force=true"
    req = urllib.request.Request(url, headers={"Authorization": _auth_header(user, app_password)}, method="DELETE")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    page_id = os.environ["PAGE_ID"].strip()
    confirm_page_id = os.environ.get("CONFIRM_PAGE_ID", "").strip()
    force = os.environ.get("FORCE", "false").strip().lower() == "true"

    if not page_id or confirm_page_id != page_id:
        print(f"ABORT: CONFIRM_PAGE_ID ('{confirm_page_id}') does not match PAGE_ID ('{page_id}')")
        sys.exit(1)

    before = get_page(wp_url, user, app_pw, page_id)
    status = before.get("status")
    slug = before.get("slug", "")
    print(f"BEFORE: id={page_id} status={status} slug={slug!r} title={before.get('title', {}).get('rendered')!r}")

    if status != "draft":
        print(f"REFUSING: page {page_id} status is {status!r}, not 'draft'. "
              f"This script has no redirect logic and is only for cleaning up test drafts. Aborting.")
        sys.exit(1)

    result = delete_page(wp_url, user, app_pw, page_id, force=force)
    after_status = result.get("status")
    print(f"AFTER: id={page_id} status={after_status}")
    print(f"SUCCESS: page {page_id} {'permanently deleted' if force else 'moved to trash'}")


if __name__ == "__main__":
    main()
