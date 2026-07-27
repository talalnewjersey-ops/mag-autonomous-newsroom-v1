"""Read-only diagnostic: fetches a few live URLs and prints their cache-
related response headers (LiteSpeed's own cache status, Hostinger's hCDN
edge status, and any Cache-Control/Age) -- so a cache purge can be verified
against the real edge response, not just trusted from the purge call's own
"success" reply. No auth needed (public pages). Never writes anything.
"""
import os
import urllib.request

WP_URL = os.environ.get("WORDPRESS_URL", "https://moneyabroadguide.com").rstrip("/")
URLS = [p.strip() for p in os.environ.get("CHECK_URLS", "/").split(",") if p.strip()]

HEADERS_OF_INTEREST = (
    "x-litespeed-cache", "x-lscache", "x-hcdn-cache-status", "x-hcdn-request-id",
    "cache-control", "age", "cf-cache-status", "server",
)


def main():
    for path in URLS:
        url = f"{WP_URL}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; MAG-cache-check/1.0)"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                print(f"\n=== {url} -> HTTP {resp.status}, body length={len(body)} ===")
                for h in HEADERS_OF_INTEREST:
                    v = resp.headers.get(h)
                    if v:
                        print(f"  {h}: {v}")
                print(f"  date: {resp.headers.get('date')}")
                if os.environ.get("SHOW_BODY_PREVIEW") == "true":
                    import re as _re
                    text_only = _re.sub(r"<[^>]+>", " ", body)
                    text_only = _re.sub(r"\s+", " ", text_only).strip()
                    print(f"  body text preview ({len(text_only.split())} words): {text_only[:500]}")
        except Exception as e:
            print(f"\n=== {url} -> ERROR: {e} ===")


if __name__ == "__main__":
    main()
