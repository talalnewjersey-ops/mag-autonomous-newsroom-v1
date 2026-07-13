import base64, json, os, urllib.request
wp_url = os.environ["WORDPRESS_URL"]
user = os.environ["WORDPRESS_USERNAME"]
app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
auth = base64.b64encode(f"{user}:{app_pw}".encode()).decode()
for sid in [75, 128]:
    url = f"{wp_url.rstrip('/')}/wp-json/code-snippets/v1/snippets/{sid}"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        d = json.loads(resp.read().decode("utf-8"))
    print(f"=== snippet {sid} ===")
    for k, v in d.items():
        if k == "code":
            v = f"<{len(v)} chars>"
        print(f"  {k} = {v!r}")
