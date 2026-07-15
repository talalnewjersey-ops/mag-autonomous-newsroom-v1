"""Read-only action: performs an authenticated GET against an arbitrary
WordPress REST route and prints the JSON response. Generic diagnostic
utility -- never writes anything.
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
    route = os.environ["ROUTE"]

    auth = base64.b64encode(f"{user}:{app_pw}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/{route.lstrip('/')}"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            print(f"HTTP {resp.status}")
            print(json.dumps(json.loads(body), indent=2))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}")
        print(e.read().decode("utf-8"))


if __name__ == "__main__":
    main()
