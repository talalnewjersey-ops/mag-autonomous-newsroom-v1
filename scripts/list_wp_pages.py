"""Read-only diagnostic: lists every WordPress PAGE (not post) via the REST
API -- id/slug/title/link/status -- plus a direct by-ID check for specific
pages. Never writes anything.

Used to verify, ahead of the AdSense review, whether Privacy Policy/Contact/
About pages actually exist on the site (2026-07-13, AUDIT-LOG.md Bloc 3).
"""
import base64
import json
import os
import urllib.error
import urllib.request


def fetch_all_pages(wp_url, user, app_password, per_page=100):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    pages = []
    page_num = 1
    while True:
        url = (f"{wp_url.rstrip('/')}/wp-json/wp/v2/pages?status=publish,draft,private"
               f"&per_page={per_page}&page={page_num}&_fields=id,title,slug,status,link,parent")
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"ERROR fetching page {page_num}: {e}")
            break
        if not batch:
            break
        pages.extend(batch)
        if len(batch) < per_page:
            break
        page_num += 1
    return pages


def _title_text(entry):
    title = entry.get("title", "")
    return title.get("rendered", "") if isinstance(title, dict) else title


def fetch_page_direct(wp_url, user, app_password, page_id):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}?context=edit&_fields=id,status,title,link,content"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
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

    pages = fetch_all_pages(wp_url, user, app_pw)
    pages.sort(key=lambda p: _title_text(p).lower())

    print(f"\n===== {len(pages)} PAGE(S) FOUND =====\n")
    for p in pages:
        print(f"id={p.get('id')} | status={p.get('status')} | slug={p.get('slug')} | "
              f"parent={p.get('parent')} | link={p.get('link')} | title={_title_text(p)}")

    keywords = ["privacy", "contact", "about", "cookie", "terms", "disclosure", "disclaimer"]
    print(f"\n===== MATCHES for {keywords} (title or slug) =====\n")
    for p in pages:
        t = _title_text(p).lower()
        s = (p.get("slug") or "").lower()
        if any(k in t or k in s for k in keywords):
            print(f"id={p.get('id')} | status={p.get('status')} | slug={p.get('slug')} | "
                  f"link={p.get('link')} | title={_title_text(p)}")

    if diagnose_ids:
        print(f"\n===== DIRECT BY-ID CHECK =====\n")
        for pid in diagnose_ids.split(","):
            pid = pid.strip()
            if not pid:
                continue
            status_code, data = fetch_page_direct(wp_url, user, app_pw, pid)
            content = data.get("content", {})
            content_text = content.get("rendered", "") if isinstance(content, dict) else ""
            print(f"id={pid} | HTTP={status_code} | status={data.get('status')} | "
                  f"link={data.get('link')} | title={_title_text(data)} | "
                  f"content_length={len(content_text)} | error={data.get('message', data.get('error', ''))}")


if __name__ == "__main__":
    main()
