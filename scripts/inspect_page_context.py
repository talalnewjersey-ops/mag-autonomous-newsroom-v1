"""Read-only diagnostic: fetches a live URL, saves the raw HTML as an
artifact, and prints surrounding context (before/after) for each requested
search string -- so the actual enclosing element (widget/template/footer)
can be identified before proposing a source-code edit. No auth needed.
Never writes anything.
"""
import os
import urllib.request

WP_URL = os.environ.get("WORDPRESS_URL", "https://moneyabroadguide.com").rstrip("/")
PATH = os.environ.get("CHECK_PATH", "/")
NEEDLES = [n.strip() for n in os.environ.get("NEEDLES", "").split("|") if n.strip()]
CONTEXT = int(os.environ.get("CONTEXT_CHARS", "400"))


def main():
    url = f"{WP_URL}{PATH}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; MAG-inspect/1.0)"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="replace")

    print(f"HTTP {resp.status}, length={len(body)}")
    with open("page_body.html", "w", encoding="utf-8") as f:
        f.write(body)
    print("Saved full body to page_body.html")

    for needle in NEEDLES:
        idx = 0
        count = 0
        print(f"\n===== occurrences of {needle!r} =====")
        while True:
            i = body.find(needle, idx)
            if i == -1:
                break
            count += 1
            print(f"--- match {count} at offset {i} ---")
            print(body[max(0, i - CONTEXT):i + len(needle) + CONTEXT])
            idx = i + len(needle)
        if count == 0:
            print("  NOT FOUND")


if __name__ == "__main__":
    main()
