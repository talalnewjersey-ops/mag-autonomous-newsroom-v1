#!/usr/bin/env python3
"""WordPress Diagnostic Script v2 - Tests authentication methods"""
import os
import base64
import requests

WP_URL = os.environ.get("WORDPRESS_URL", "https://moneyabroadguide.com").rstrip("/")
WP_USER = os.environ.get("WORDPRESS_USERNAME", "")
WP_PASS = os.environ.get("WORDPRESS_APP_PASSWORD", "") or os.environ.get("WORDPRESS_PASSWORD", "")

print("=" * 60)
print("WORDPRESS DIAGNOSTIC v2")
print("=" * 60)
print("WP_URL: ***")
print("WP_USER length:", len(WP_USER), "chars")
print("WP_PASS length:", len(WP_PASS), "chars")
print("WP_PASS repr (sanitized):", repr(WP_PASS[:4] + "..." + WP_PASS[-4:]) if len(WP_PASS) > 8 else "TOO SHORT")
print()

# Test 1: Raw password as-is
creds_raw = base64.b64encode((WP_USER + ":" + WP_PASS).encode()).decode()

# Test 2: Password stripped (remove spaces)
wp_pass_stripped = WP_PASS.replace(" ", "")
creds_stripped = base64.b64encode((WP_USER + ":" + wp_pass_stripped).encode()).decode()

# Test 3: Re-space every 4 chars (normalize app password format)
wp_pass_nospace = WP_PASS.replace(" ", "")
wp_pass_respaced = " ".join(wp_pass_nospace[i:i+4] for i in range(0, len(wp_pass_nospace), 4))
creds_respaced = base64.b64encode((WP_USER + ":" + wp_pass_respaced).encode()).decode()

variants = [
    ("Raw password as stored", creds_raw),
    ("Password with spaces removed", creds_stripped),
    ("Password re-spaced every 4 chars", creds_respaced),
]

print("[TEST 1] GET /wp-json/ - API root (no auth needed)")
try:
    r = requests.get(WP_URL + "/wp-json/", timeout=15)
    ct = r.headers.get("Content-Type", "")
    print("  Status:", r.status_code, "| CT:", ct[:50])
    if r.status_code == 200 and "json" in ct:
        d = r.json()
        print("  -> API accessible! Site:", d.get("name", "?"))
    else:
        print("  -> FAILED:", r.text[:100])
except Exception as e:
    print("  ERROR:", e)

print()
print("[TEST 2] GET /wp-json/wp/v2/users/me - Auth check (3 credential variants)")
for name, creds in variants:
    h = {
        "Authorization": "Basic " + creds,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    try:
        r = requests.get(WP_URL + "/wp-json/wp/v2/users/me", headers=h, timeout=15)
        print("  [" + name + "]:", r.status_code)
        if r.status_code == 200:
            d = r.json()
            print("  -> AUTH OK! User:", d.get("name", "?"), "Roles:", d.get("roles", []))
            break
        else:
            body = r.text[:150]
            print("  -> " + body)
    except Exception as e:
        print("  ERROR:", e)

print()
print("[TEST 3] POST /wp/v2/posts - Create draft (3 credential variants)")
post_data = {
    "title": "NEXUS-14 Diag Test - DELETE ME",
    "content": "<p>Diagnostic test. Safe to delete.</p>",
    "status": "draft"
}
success = False
for name, creds in variants:
    h = {
        "Authorization": "Basic " + creds,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    try:
        r = requests.post(WP_URL + "/wp-json/wp/v2/posts", headers=h, json=post_data, timeout=30)
        print("  [" + name + "]:", r.status_code)
        if r.status_code in (200, 201):
            d = r.json()
            pid = d.get("id", "?")
            print("  -> POST SUCCESS! ID=" + str(pid))
            requests.delete(WP_URL + "/wp-json/wp/v2/posts/" + str(pid) + "?force=true", headers=h, timeout=15)
            print("  -> Test post deleted")
            success = True
            break
        else:
            print("  -> " + r.text[:200])
    except Exception as e:
        print("  ERROR:", e)

if not success:
    print("  ALL AUTH VARIANTS FAILED for POST")

print()
print("[TEST 4] Check if Application Passwords are enabled")
try:
    r = requests.get(WP_URL + "/wp-json/", timeout=15)
    if r.status_code == 200:
        d = r.json()
        auth = d.get("authentication", {})
        print("  Authentication methods:", list(auth.keys()) if auth else "None listed")
        if "application-passwords" in auth:
            ap = auth["application-passwords"]
            print("  Application Passwords endpoints:", list(ap.get("endpoints", {}).keys()))
        namespaces = d.get("namespaces", [])
        print("  Available namespaces:", namespaces[:10])
except Exception as e:
    print("  ERROR:", e)

print()
print("=" * 60)
print("DIAGNOSTIC v2 COMPLETE")
print("=" * 60)
