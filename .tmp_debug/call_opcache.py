import base64, json, os, urllib.request
wp_url = os.environ["WORDPRESS_URL"]
user = os.environ["WORDPRESS_USERNAME"]
app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
auth = base64.b64encode(f"{user}:{app_pw}".encode()).decode()
req = urllib.request.Request(
    f"{wp_url.rstrip('/')}/wp-json/mag/v1/opcache-reset",
    data=b"{}", method="POST",
    headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=30) as resp:
    d = json.loads(resp.read().decode("utf-8"))
print(json.dumps(d, indent=2))
