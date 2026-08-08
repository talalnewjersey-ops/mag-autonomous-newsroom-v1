import base64, json, os, socket, urllib.request
_orig = socket.getaddrinfo
def _v4(h,p,f=0,t=0,pr=0,fl=0): return _orig(h,p,socket.AF_INET,t,pr,fl)
socket.getaddrinfo = _v4
wp_url = os.environ["WORDPRESS_URL"]
user = os.environ["WORDPRESS_USERNAME"]
app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
post_id = os.environ["POST_ID"]
auth = base64.b64encode(f"{user}:{app_pw}".encode()).decode()
url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}?context=edit"
req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode("utf-8"))
raw = data["content"]["raw"]
with open("fetched_content_exact.html", "w", encoding="utf-8") as f:
    f.write(raw)
with open("fetch_meta.json", "w") as f:
    json.dump({"len": len(raw), "modified": data.get("modified")}, f)
