"""Read-only diagnostic: paginates through the Redirection plugin's own
404 log (`wp-json/redirection/v1/404`) and aggregates it by URL, so a
2000+ raw hit-log doesn't have to be read entry by entry.

Built 2026-07-26 for the pre-production 404 audit (Ahrefs found 180/393
crawled pages returning 404). The Redirection plugin logs every 404 the
live site actually served, including its referrer -- this is what lets a
"real internal broken link" (referrer = another moneyabroadguide.com page)
be told apart from bot-scanner noise (empty/junk referrer, garbage URL
shapes like "/-/-/-/-/-/") without guessing from the URL shape alone.

Never writes to WordPress -- GET only, same as every other *_log.py-style
diagnostic in this repo.
"""
import base64
import json
import os
import urllib.request
from collections import defaultdict


def _auth_header(user, app_password):
    return "Basic " + base64.b64encode(f"{user}:{app_password}".encode()).decode()


def fetch_page(wp_url, user, app_password, page, per_page=200):
    url = (f"{wp_url.rstrip('/')}/wp-json/redirection/v1/404"
           f"?per_page={per_page}&orderby=total&direction=desc&page={page}")
    req = urllib.request.Request(url, headers={"Authorization": _auth_header(user, app_password)})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]

    all_items = []
    seen_ids = set()
    page = 0
    total_reported = None
    max_pages = 40  # safety cap: 40 * 200 = 8000 entries

    while page < max_pages:
        data = fetch_page(wp_url, user, app_pw, page)
        total_reported = data.get("total", total_reported)
        items = data.get("items", [])
        if not items:
            break
        new_ids = [it["id"] for it in items if it["id"] not in seen_ids]
        if not new_ids:
            print(f"page {page}: no new ids, stopping (pagination not advancing or exhausted)")
            break
        for it in items:
            if it["id"] not in seen_ids:
                seen_ids.add(it["id"])
                all_items.append(it)
        print(f"page {page}: +{len(new_ids)} new (running total {len(all_items)})")
        if len(items) < 200:
            break
        page += 1

    print(f"\nReported total in API: {total_reported}")
    print(f"Fetched (deduped by id): {len(all_items)}")

    by_url = defaultdict(lambda: {"hits": 0, "referrers": set(), "agents": set(), "last_seen": None})
    for it in all_items:
        u = it.get("url", "")
        g = by_url[u]
        g["hits"] += 1
        ref = (it.get("referrer") or "").strip()
        if ref:
            g["referrers"].add(ref)
        agent = (it.get("agent") or "").strip()
        if agent:
            g["agents"].add(agent.split(";")[0])
        if g["last_seen"] is None:
            g["last_seen"] = it.get("created")

    domain_markers = ("moneyabroadguide.com",)

    def ref_class(refs):
        if not refs:
            return "no_referrer"
        if any(any(m in r for m in domain_markers) for r in refs):
            return "internal_referrer"
        return "external_referrer"

    rows = []
    for u, g in by_url.items():
        rows.append({
            "url": u,
            "hits": g["hits"],
            "referrer_class": ref_class(g["referrers"]),
            "sample_referrers": list(g["referrers"])[:3],
            "agents": list(g["agents"])[:3],
            "last_seen": g["last_seen"],
        })

    rows.sort(key=lambda r: (-r["hits"], r["url"]))

    print(f"\nUnique 404 URLs (deduped): {len(rows)}")

    by_class = defaultdict(int)
    for r in rows:
        by_class[r["referrer_class"]] += 1
    print("\nBy referrer class (unique URLs):")
    for k, v in by_class.items():
        print(f"  {k}: {v}")

    print("\n===== INTERNAL-REFERRER 404s (a live moneyabroadguide.com page links to this dead URL) =====")
    internal = [r for r in rows if r["referrer_class"] == "internal_referrer"]
    for r in internal:
        print(f"url={r['url']!r} hits={r['hits']} referrers={r['sample_referrers']} last_seen={r['last_seen']}")

    print(f"\n===== TOP 60 BY HIT COUNT (all referrer classes) =====")
    for r in rows[:60]:
        print(f"hits={r['hits']:>4} class={r['referrer_class']:<18} url={r['url']!r} "
              f"referrers={r['sample_referrers']} last_seen={r['last_seen']}")

    out_path = "redirection_404_aggregated.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False, default=list)
    print(f"\nSaved full aggregated list ({len(rows)} unique URLs) to {out_path}")


if __name__ == "__main__":
    main()
