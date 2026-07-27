"""Read-only diagnostic: checks the handful of things AdSense review actually
looks for that a WordPress REST call can't answer on its own -- whether
ads.txt exists at the site root, and whether the live rendered homepage
(and one live article page, since the footer is theme-wide) actually link
to the key legal/about/contact pages. No auth needed (all public URLs).
Never writes anything.
"""
import os
import re
import urllib.error
import urllib.request

WP_URL = os.environ.get("WORDPRESS_URL", "https://moneyabroadguide.com").rstrip("/")


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; MAG-adsense-check/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, str(e)


def main():
    print("===== ads.txt =====")
    status, body = fetch(f"{WP_URL}/ads.txt")
    print(f"HTTP {status}, length={len(body)}")
    if status == 200:
        print(body[:500])

    # each canonical page checked under every real URL that reaches it
    # (its own slug, plus any known alias/old-slug that 301s to it)
    targets = {
        "privacy-policy": ["/privacy-policy/"],
        "legal-disclaimer": ["/legal-disclaimer/", "/disclaimer/"],
        "terms-and-conditions": ["/terms-and-conditions/"],
        "about": ["/about/", "/about-us/"],
        "contact": ["/contact/"],
    }

    for label, path in [("HOMEPAGE", "/"), ("ARTICLE PAGE", "/best-banks-newcomers-usa-2026/")]:
        print(f"\n===== {label} ({path}) — link check (whole page body) =====")
        status, body = fetch(f"{WP_URL}{path}")
        print(f"HTTP {status}, length={len(body)}")
        if status != 200:
            continue
        for name, paths in targets.items():
            found_via = [p for p in paths if p in body or p.rstrip("/") in body]
            print(f"  links to {name}: {bool(found_via)}  (via {found_via})" if found_via else f"  links to {name}: False")
        for tag in re.finditer(r"<footer[^>]*>.*?</footer>", body, re.DOTALL | re.IGNORECASE):
            links = re.findall(r'href="([^"]+)"', tag.group(0))
            print(f"  <footer> block ({len(tag.group(0))} chars): {len(links)} links")
            for l in links:
                print("    -", l)


if __name__ == "__main__":
    main()
