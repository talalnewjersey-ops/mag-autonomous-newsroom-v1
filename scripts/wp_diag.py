#!/usr/bin/env python3
"""WP Diagnostic v3 - Headers + Blocker ID"""
import os, base64, requests

WP_URL = os.environ.get("WORDPRESS_URL","https://moneyabroadguide.com").rstrip("/")
WP_USER = os.environ.get("WORDPRESS_USERNAME","")
WP_PASS = os.environ.get("WORDPRESS_APP_PASSWORD","") or os.environ.get("WORDPRESS_PASSWORD","")

print("="*60)
print("WP DIAGNOSTIC v3 - HEADER CAPTURE + BLOCKER ID")
print("="*60)
print("WP_USER:", len(WP_USER),"chars")
print("WP_PASS:", len(WP_PASS),"chars", repr(WP_PASS[:4]+"..."+WP_PASS[-4:]) if len(WP_PASS)>8 else "SHORT")
print()

creds = base64.b64encode((WP_USER+":"+WP_PASS.replace(" ","")).encode()).decode()
AUTH = {"Authorization":"Basic "+creds,"Content-Type":"application/json","Accept":"application/json","User-Agent":"NEXUS14-Diag/3"}

def dump(r):
    print("  STATUS:",r.status_code,"TIME:",round(r.elapsed.total_seconds(),2),"s")
    print("  HEADERS:")
    for k,v in r.headers.items(): print(f"    {k}: {v}")
    print("  END-HEADERS")

def blocker(r):
    h={k.lower():v.lower() for k,v in r.headers.items()}
    body=r.text[:2000]; bl=body.lower(); sv=h.get("server","")
    v="UNKNOWN"
    if h.get("cf-ray"): v="CLOUDFLARE"
    elif "cloudflare" in sv or "cloudflare" in bl: v="CLOUDFLARE"
    elif "litespeed" in sv or "lsws" in sv:
        v="LITESPEED+MODSEC" if "modsecurity" in bl or "mod_security" in bl else "LITESPEED WAF"
    elif "apache" in sv: v="APACHE+MODSEC" if "modsec" in bl else "APACHE/.htaccess"
    elif "nginx" in sv: v="NGINX"
    elif "wordfence" in bl: v="WORDFENCE"
    elif "patchstack" in bl: v="PATCHSTACK"
    elif "hostinger" in bl: v="HOSTINGER WAF"
    elif "text/html" in r.headers.get("content-type",""): v="SERVER-LEVEL (HTML not JSON)"
    print(f"  ***BLOCKER: {v}***")
    print("  BODY:",body[:1200])
    return v

print("[T1] GET /wp-json/ no auth")
try:
    r=requests.get(WP_URL+"/wp-json/",timeout=15); dump(r)
    if r.status_code==200:
        d=r.json(); print("  OK site:",d.get("name"),"ns:",d.get("namespaces",[])[:5])
        print("  AppPasswords:", "ON" if "application-passwords" in d.get("authentication",{}) else "OFF")
    else: blocker(r)
except Exception as e: print("  ERR:",e)
print()

print("[T2] GET /wp-json/wp/v2/users/me auth")
try:
    r=requests.get(WP_URL+"/wp-json/wp/v2/users/me",headers=AUTH,timeout=15); dump(r)
    if r.status_code==200:
        d=r.json(); caps=d.get("capabilities",{})
        print("  OK user:",d.get("name"),"roles:",d.get("roles"))
        print("  edit_posts:",caps.get("edit_posts",False),"publish:",caps.get("publish_posts",False),"upload:",caps.get("upload_files",False))
    else: blocker(r)
except Exception as e: print("  ERR:",e)
print()

print("[T3] POST /wp-json/wp/v2/posts create draft")
try:
    r=requests.post(WP_URL+"/wp-json/wp/v2/posts",headers=AUTH,json={"title":"DIAG-DELETE","content":"<p>test</p>","status":"draft"},timeout=30)
    dump(r)
    if r.status_code in(200,201):
        d=r.json(); pid=d.get("id")
        print("  ***SUCCESS Post ID:",pid,"slug:",d.get("slug"),"***")
        print("  ***PIPELINE VALIDATED***")
        requests.delete(WP_URL+f"/wp-json/wp/v2/posts/{pid}?force=true",headers=AUTH,timeout=15)
        print("  cleanup: deleted",pid)
    else: blocker(r)
except Exception as e: print("  ERR:",e)
print()
print("="*60)
print("DIAG v3 DONE")
print("="*60)
