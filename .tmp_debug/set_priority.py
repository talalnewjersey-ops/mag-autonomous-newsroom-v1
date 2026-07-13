import base64, json, os, urllib.request
wp_url = os.environ["WORDPRESS_URL"]
user = os.environ["WORDPRESS_USERNAME"]
app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
auth = base64.b64encode(f"{user}:{app_pw}".encode()).decode()
url = f"{wp_url.rstrip('/')}/wp-json/code-snippets/v1/snippets/128"
payload = json.dumps({"priority": 20}).encode("utf-8")
req = urllib.request.Request(url, data=payload, method="POST", headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as resp:
    d = json.loads(resp.read().decode("utf-8"))
print("priority now:", d.get("priority"))
