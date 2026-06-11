#!/usr/bin/env python3
"""WordPress Diagnostic Script - Tests all connection methods"""
import os
import json
import base64
import requests

WP_URL = os.environ.get("WORDPRESS_URL", "https://moneyabroadguide.com").rstrip("/")
WP_USER = os.environ.get("WORDPRESS_USERNAME", "")
WP_PASS = os.environ.get("WORDPRESS_PASSWORD", "")

print("=" * 60)
print("WORDPRESS DIAGNOSTIC v1")
print("=" * 60)
print("WP_URL:", WP_URL)
print("WP_USER:", WP_USER)
print("WP_PASS length:", len(WP_PASS), "chars")
print()

creds = base64.b64encode((WP_USER + ":" + WP_PASS).encode()).decode()

headers_list = [
    {
        "Authorization": "Basic " + creds,
        "Content-Type": "application/json",
        "User-Agent": "WordPress/6.4; https://moneyabroadguide.com",
        "Accept": "application/json",
    },
    {
        "Authorization": "Basic " + creds,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Accept": "application/json",
    },
    {
        "Authorization": "Basic " + creds,
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
]

print("[TEST 1] GET /wp-json/ - API root accessibility")
for i, h in enumerate(headers_list):
    try:
        r = requests.get(WP_URL + "/wp-json/", headers=h, timeout=15)
        ct = r.headers.get("Content-Type", "")
        print("  variant#" + str(i) + ": " + str(r.status_code) + " | " + ct[:50])
        if "json" in ct and r.status_code == 200:
            d = r.json()
            print("  -> OK! Site name: " + str(d.get("name", "?")))
            break
        else:
            body_preview = r.text[:200].replace("\n", " ")
            print("  -> Body: " + body_preview)
    except Exception as e:
        print("  variant#" + str(i) + ": ERROR " + str(e))

print()
print("[TEST 2] GET /wp-json/wp/v2/users/me - auth verification")
for i, h in enumerate(headers_list):
    try:
        r = requests.get(WP_URL + "/wp-json/wp/v2/users/me", headers=h, timeout=15)
        print("  variant#" + str(i) + ": " + str(r.status_code))
        if r.status_code == 200:
            d = r.json()
            print("  -> AUTH OK! User: " + str(d.get("name", "?")) + " roles: " + str(d.get("roles", [])))
            break
        else:
            body_preview = r.text[:300].replace("\n", " ")
            print("  -> Body: " + body_preview)
    except Exception as e:
        print("  variant#" + str(i) + ": ERROR " + str(e))

print()
print("[TEST 3] POST /wp/v2/posts - create draft post")
post_data = {
    "title": "NEXUS-14 Diag Test - DELETE ME",
    "content": "<p>This is a diagnostic test post from NEXUS-14. Safe to delete.</p>",
    "status": "draft"
}
for i, h in enumerate(headers_list):
    try:
        r = requests.post(WP_URL + "/wp-json/wp/v2/posts", headers=h, json=post_data, timeout=30)
        print("  variant#" + str(i) + ": " + str(r.status_code))
        if r.status_code in (200, 201):
            d = r.json()
            pid = d.get("id", "?")
            print("  -> POST SUCCESS! ID=" + str(pid) + " link=" + str(d.get("link", "?")))
            del_r = requests.delete(
                WP_URL + "/wp-json/wp/v2/posts/" + str(pid) + "?force=true",
                headers=h, timeout=15
            )
            print("  -> Cleanup delete: " + str(del_r.status_code))
            break
        else:
            body_preview = r.text[:400].replace("\n", " ")
            print("  -> Body: " + body_preview)
    except Exception as e:
        print("  variant#" + str(i) + ": ERROR " + str(e))

print()
print("[TEST 4] GET /wp-json/ without any auth - bot check")
try:
    r = requests.get(WP_URL + "/wp-json/", timeout=15)
    print("  No-auth status: " + str(r.status_code))
    print("  Content-Type: " + r.headers.get("Content-Type", "?"))
    body = r.text
    if "litespeed" in body.lower():
        print("  -> DETECTED: LiteSpeed bot protection!")
    if "bot" in body.lower() and "verif" in body.lower():
        print("  -> DETECTED: Bot verification page!")
    if r.status_code == 200 and "json" in r.headers.get("Content-Type", ""):
        print("  -> API root accessible without auth")
    print()
    print("  Response headers:")
    for k, v in list(r.headers.items())[:15]:
        print("    " + k + ": " + v)
except Exception as e:
    print("  ERROR: " + str(e))

print()
print("[TEST 5] XMLRPC availability check")
try:
    r = requests.get(WP_URL + "/xmlrpc.php", timeout=15)
    print("  XMLRPC status: " + str(r.status_code))
    if "XML-RPC server accepts POST requests only" in r.text:
        print("  -> XMLRPC is ENABLED and accessible!")
    elif r.status_code == 403:
        print("  -> XMLRPC is BLOCKED (403)")
    elif r.status_code == 404:
        print("  -> XMLRPC not found (404)")
    else:
        print("  -> Body: " + r.text[:200])
except Exception as e:
    print("  ERROR: " + str(e))

print()
print("[TEST 6] Application Password format test")
app_pass_spaced = " ".join(WP_PASS[i:i+4] for i in range(0, len(WP_PASS), 4))
creds_app = base64.b64encode((WP_USER + ":" + app_pass_spaced).encode()).decode()
h_app = {
    "Authorization": "Basic " + creds_app,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}
try:
    r = requests.get(WP_URL + "/wp-json/wp/v2/users/me", headers=h_app, timeout=15)
    print("  App-password format: " + str(r.status_code))
    if r.status_code == 200:
        d = r.json()
        print("  -> SUCCESS! User: " + str(d.get("name", "?")))
    else:
        print("  -> Body: " + r.text[:200])
except Exception as e:
    print("  ERROR: " + str(e))

print()
print("=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
