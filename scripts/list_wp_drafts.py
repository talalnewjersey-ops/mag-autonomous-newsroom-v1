"""Read-only diagnostic: lists every draft post on WordPress via the REST API
(status=publish,draft requires authentication for the draft half -- the
public API forbids status=draft unauthenticated). Never writes anything.

Used to identify residual drafts from prior control runs (e.g. dead-title
collisions like posts 48418/48466) before a manual wp-admin cleanup.
"""
import base64
import json
import os
import urllib.error
import urllib.request


def fetch_all_drafts(wp_url, user, app_password, per_page=100):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    drafts = []
    page = 1
    while True:
        url = (f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts?status=draft&per_page={per_page}"
               f"&page={page}&_fields=id,title,slug,date,modified,link")
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"ERROR fetching page {page}: {e}")
            break
        if not batch:
            break
        drafts.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return drafts


def _title_text(post):
    title = post.get("title", "")
    return title.get("rendered", "") if isinstance(title, dict) else title


def fetch_post_direct(wp_url, user, app_password, post_id):
    """Fetch ONE post by ID directly (context=edit shows the raw status field
    regardless of the list endpoint's status filter) -- used to check whether
    a post the list endpoint still returns has ACTUALLY changed status
    server-side, or whether the list endpoint itself is serving a stale/
    cached response."""
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}?context=edit&_fields=id,status,modified,title"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}",
                                                "Cache-Control": "no-cache, no-store, must-revalidate",
                                                "Pragma": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))
    except Exception as e:
        return None, {"error": str(e)}


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    diagnose_ids = os.environ.get("DIAGNOSE_IDS", "")

    drafts = fetch_all_drafts(wp_url, user, app_pw)
    drafts.sort(key=lambda d: d.get("date", ""), reverse=True)

    print(f"\n===== {len(drafts)} DRAFT POST(S) FOUND (list endpoint, status=draft) =====\n")
    for d in drafts:
        print(f"id={d.get('id')} | date={d.get('date')} | modified={d.get('modified')} | "
              f"slug={d.get('slug')} | title={_title_text(d)}")

    if diagnose_ids:
        print(f"\n===== DIRECT BY-ID CHECK (context=edit, cache-busting headers) =====\n")
        for pid in diagnose_ids.split(","):
            pid = pid.strip()
            if not pid:
                continue
            status_code, data = fetch_post_direct(wp_url, user, app_pw, pid)
            print(f"id={pid} | HTTP={status_code} | actual_status={data.get('status')} | "
                  f"modified={data.get('modified')} | error={data.get('message', data.get('error', ''))}")


if __name__ == "__main__":
    main()
