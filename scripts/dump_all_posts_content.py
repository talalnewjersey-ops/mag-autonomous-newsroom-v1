"""Read-only diagnostic: dumps id/slug/content for every published post as a
single JSON file, uploaded as a workflow artifact (not printed to logs --
GH Actions log streaming mangles very large multi-line JSON blobs). Built
for a one-off manual similarity check that doesn't need the full
low_value_content_audit.py machinery (which also computes trust-page and
E-E-A-T signals this doesn't need, and whose git-commit step has a known
race-condition flakiness when other report-committing workflows run
concurrently -- this script sidesteps that entirely by not touching git).
"""
import json
import os
import socket
import urllib.request

_orig_getaddrinfo = socket.getaddrinfo
def _force_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _force_ipv4


def fetch_all(wp_url):
    posts = []
    page = 1
    while True:
        url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts?status=publish&per_page=50&page={page}&_fields=id,slug,content"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                batch = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 400:
                break
            raise
        if not batch:
            break
        posts.extend(batch)
        page += 1
    return posts


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    posts = fetch_all(wp_url)
    out = [{"id": p["id"], "slug": p["slug"], "content": p["content"]["rendered"]} for p in posts]
    with open("all_posts_content.json", "w", encoding="utf-8") as f:
        json.dump(out, f)
    print(f"Dumped {len(out)} posts to all_posts_content.json")


if __name__ == "__main__":
    main()
