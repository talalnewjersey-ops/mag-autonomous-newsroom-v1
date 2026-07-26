"""Read-only diagnostic: fetches the site's sitemap index and every
sub-sitemap it references, extracts every listed URL, then checks each
one's live HTTP status.

Built 2026-07-26 for the pre-production 404 audit. A URL that is 404 but
was only ever reached via an old backlink or bookmark is a much smaller
problem than a URL the sitemap ITSELF is currently telling Google to
crawl -- the latter actively wastes crawl budget on dead pages and is the
first thing to fix. Never writes to WordPress.
"""
import json
import os
import re
import urllib.request

WP_URL = os.environ.get("WORDPRESS_URL", "https://moneyabroadguide.com").rstrip("/")


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; MAG-404-audit/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)


def check_status(url, timeout=15):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 (compatible; MAG-404-audit/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.geturl()
    except urllib.error.HTTPError as e:
        return e.code, url
    except Exception as e:
        return None, str(e)


def main():
    status, body = fetch(f"{WP_URL}/sitemap_index.xml")
    if status != 200:
        status, body = fetch(f"{WP_URL}/sitemap.xml")
    print(f"Sitemap index HTTP {status}, length={len(body)}")

    sub_sitemaps = re.findall(r"<loc>(.*?)</loc>", body)
    print(f"Sub-sitemaps found: {len(sub_sitemaps)}")
    for s in sub_sitemaps:
        print(" -", s)

    all_urls = []
    for sm in sub_sitemaps:
        st, b = fetch(sm)
        urls = re.findall(r"<loc>(.*?)</loc>", b)
        print(f"{sm}: HTTP {st}, {len(urls)} URLs")
        all_urls.extend(urls)

    if not sub_sitemaps and body:
        all_urls = re.findall(r"<loc>(.*?)</loc>", body)
        print(f"(no sub-sitemaps, treating index as flat sitemap: {len(all_urls)} URLs)")

    all_urls = sorted(set(all_urls))
    print(f"\nTotal unique URLs across all sitemaps: {len(all_urls)}")

    import urllib.error
    results = {}
    for u in all_urls:
        code, final = check_status(u)
        results[u] = {"code": code, "final_url": final}

    by_code = {}
    for u, r in results.items():
        by_code.setdefault(r["code"], []).append(u)

    print("\n===== STATUS CODE BREAKDOWN =====")
    for code in sorted(by_code, key=lambda c: (c is None, c)):
        print(f"  {code}: {len(by_code[code])} URLs")

    print("\n===== NON-200 URLs IN SITEMAP (these are actively advertised to Google as crawlable) =====")
    for code, urls in by_code.items():
        if code == 200:
            continue
        for u in urls:
            print(f"  code={code} url={u} final={results[u]['final_url']}")

    with open("sitemap_health.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved full results to sitemap_health.json")


if __name__ == "__main__":
    main()
