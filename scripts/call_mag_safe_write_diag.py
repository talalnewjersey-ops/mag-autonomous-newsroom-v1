"""One-off diagnostic caller for the temporary mag-diag/v1/safe-write-plugin-file
route (see scratchpad-diag-write-temp.php). Hash-checked write against a
single named plugin file; refuses if the live content doesn't match the
expected before-hash. Delete this script alongside the snippet once the
mag-perf-fixes.php edit is confirmed.
"""
import base64
import json
import os
import urllib.error
import urllib.request


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    expected_before_hash = os.environ["EXPECTED_BEFORE_HASH"]
    new_content_file = os.environ["NEW_CONTENT_FILE"]

    with open(new_content_file, "rb") as f:
        new_content_b64 = base64.b64encode(f.read()).decode()

    auth = base64.b64encode(f"{user}:{app_pw}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/mag-diag/v1/safe-write-plugin-file"
    payload = json.dumps({
        "expected_before_hash": expected_before_hash,
        "new_content_b64": new_content_b64,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"HTTP {resp.status}")
            print(json.dumps(json.loads(resp.read().decode("utf-8")), indent=2))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}")
        print(e.read().decode("utf-8"))


if __name__ == "__main__":
    main()
