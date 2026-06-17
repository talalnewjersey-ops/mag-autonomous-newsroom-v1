#!/usr/bin/env python3
"""
NEXUS-14: WordPress Authentication Audit Script
scripts/verify_wordpress_auth.py

Purpose:
  - Full diagnostic of WordPress REST API authentication
  - Uses GitHub Secrets: WORDPRESS_URL, WORDPRESS_USERNAME, WORDPRESS_PASSWORD
  - Tests: API root, auth, current user, draft creation, draft retrieval
  - Produces: PASS or FAIL with root cause details

ROOT CAUSE OF RUN #5 FAILURE (documented evidence):
  Log line 28: WordPress: https://moneyabroadguide.com/wp-admin | user=***
  Log line 53: [11-12] WordPress Draft Creation...
  Log line 54:   WP Auth warning: 404
  Log line 55:   FAIL - HTTP 404: <!DOCTYPE html>

  The WORDPRESS_URL secret contained /wp-admin suffix.
  This caused all REST API calls to:
    https://moneyabroadguide.com/wp-admin/wp-json/wp/v2/posts  (WRONG - 404)
  Instead of the correct:
    https://moneyabroadguide.com/wp-json/wp/v2/posts  (CORRECT)

  The server returned the wp-admin HTML login page (<!DOCTYPE html>)
  instead of a JSON response - confirmed by HTTP 404 + HTML body in logs.

ADDITIONAL ROOT CAUSE (401 errors on Runs #6-#8):
  Even after fixing the URL, WORDPRESS_USERNAME was wrong.
  Correct value: ai-publisher (login slug, not email)
  Wrong value:   Some other value was stored initially
"""
import os, sys, json, time, requests
from base64 import b64encode
from datetime import datetime

SEPARATOR = "=" * 70

def log(msg):
    print(msg, flush=True)

def separator(title=""):
    if title:
        log(SEPARATOR)
        log(title)
        log(SEPARATOR)
    else:
        log(SEPARATOR)

# ============================================================
# READ ENVIRONMENT
# ============================================================
WP_URL_RAW = os.environ.get("WORDPRESS_URL", "")
WP_USER    = os.environ.get("WORDPRESS_USERNAME", "")
WP_PASS    = os.environ.get("WORDPRESS_APP_PASSWORD", "") or os.environ.get("WORDPRESS_PASSWORD", "")

# Strip trailing slash and /wp-admin suffix if present
WP_URL_CLEAN = WP_URL_RAW.rstrip("/")
if WP_URL_CLEAN.endswith("/wp-admin"):
    WP_URL_CLEAN = WP_URL_CLEAN[:-len("/wp-admin")]

ENDPOINT_API_ROOT   = WP_URL_CLEAN + "/wp-json/"
ENDPOINT_V2_POSTS   = WP_URL_CLEAN + "/wp-json/wp/v2/posts"
ENDPOINT_V2_USERS   = WP_URL_CLEAN + "/wp-json/wp/v2/users/me"

TIMESTAMP = datetime.utcnow().isoformat()
RESULTS = {}
ERRORS = []

separator("NEXUS-14 WORDPRESS AUTH AUDIT")
log("Timestamp    : " + TIMESTAMP)
log("WP_URL raw   : " + (WP_URL_RAW if WP_URL_RAW else "NOT SET"))
log("WP_URL used  : " + WP_URL_CLEAN)
log("WP_USER      : " + (WP_USER if WP_USER else "NOT SET"))
log("WP_PASS      : " + ("SET (" + str(len(WP_PASS)) + " chars)" if WP_PASS else "NOT SET"))
log("")

# ============================================================
# TEST 0: ENVIRONMENT VALIDATION
# ============================================================
separator("TEST 0: ENVIRONMENT VALIDATION")
env_ok = True

if not WP_URL_RAW:
    log("[FAIL] WORDPRESS_URL secret is EMPTY or not set")
    ERRORS.append("WORDPRESS_URL not set")
    env_ok = False
else:
    log("[PASS] WORDPRESS_URL is set")

if WP_URL_RAW.rstrip("/").endswith("/wp-admin"):
    log("[WARN] WORDPRESS_URL contains /wp-admin suffix - THIS WAS THE RUN #5 ROOT CAUSE")
    log("       Raw value   : " + WP_URL_RAW)
    log("       Constructed : " + WP_URL_RAW.rstrip("/") + "/wp-json/wp/v2/posts")
    log("       That URL returns HTTP 404 <!DOCTYPE html> (WP admin login page)")
    log("       Auto-corrected to: " + WP_URL_CLEAN)
    ERRORS.append("WORDPRESS_URL had /wp-admin suffix (auto-corrected)")
else:
    log("[PASS] WORDPRESS_URL base URL is clean (no /wp-admin suffix)")

if not WP_USER:
    log("[FAIL] WORDPRESS_USERNAME is EMPTY or not set")
    ERRORS.append("WORDPRESS_USERNAME not set")
    env_ok = False
else:
    log("[PASS] WORDPRESS_USERNAME: " + WP_USER)

if not WP_PASS:
    log("[FAIL] WORDPRESS_PASSWORD is EMPTY or not set")
    ERRORS.append("WORDPRESS_PASSWORD not set")
    env_ok = False
else:
    log("[PASS] WORDPRESS_PASSWORD: SET (" + str(len(WP_PASS)) + " chars)")

RESULTS["env_valid"] = env_ok
log("")

if not env_ok:
    log("[ABORT] Missing required credentials")
    RESULTS["verdict"] = "FAIL"
    RESULTS["errors"] = ERRORS
    with open("wp_auth_audit.json", "w") as f:
        json.dump(RESULTS, f, indent=2)
    sys.exit(1)

# Build auth header
creds = b64encode((WP_USER + ":" + WP_PASS).encode("utf-8")).decode("utf-8")
HEADERS = {
    "Authorization": "Basic " + creds,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; NEXUS14-WPAudit/1.0)",
}
log("Auth header  : Basic " + creds[:20] + "... (length=" + str(len(creds)) + ")")
log("Username len : " + str(len(WP_USER)) + " chars")
log("Password len : " + str(len(WP_PASS)) + " chars")
log("")

# ============================================================
# TEST 1: WP-JSON API ROOT (unauthenticated)
# ============================================================
separator("TEST 1: WP-JSON API ROOT (unauthenticated)")
log("Endpoint: " + ENDPOINT_API_ROOT)
try:
    t1 = time.time()
    r1 = requests.get(ENDPOINT_API_ROOT, timeout=15)
    e1 = round(time.time() - t1, 2)
    log("Status : " + str(r1.status_code) + " (" + str(e1) + "s)")
    log("CType  : " + r1.headers.get("Content-Type", ""))

    if r1.status_code == 200 and "json" in r1.headers.get("Content-Type", ""):
        d1 = r1.json()
        log("[PASS] API root returns valid JSON")
        log("Site   : " + str(d1.get("name", "n/a")))
        ns = d1.get("namespaces", [])
        log("NS     : " + str(ns))
        RESULTS["api_root_ok"] = True
        RESULTS["wp_v2_active"] = "wp/v2" in ns
        log("[PASS] wp/v2: " + str(RESULTS["wp_v2_active"]))
    elif r1.status_code == 404:
        log("[FAIL] HTTP 404 - URL incorrect or REST API disabled")
        log("First 200 chars: " + r1.text[:200])
        if "<!DOCTYPE" in r1.text[:100]:
            log("DIAGNOSIS: Response is HTML - URL points to wrong location")
            log("           This is identical to the Run #5 failure pattern")
        RESULTS["api_root_ok"] = False
        ERRORS.append("API root 404")
    else:
        log("[WARN] Status " + str(r1.status_code))
        RESULTS["api_root_ok"] = r1.status_code == 200
except Exception as e:
    log("[FAIL] " + str(e))
    RESULTS["api_root_ok"] = False
    ERRORS.append("API root error: " + str(e))
log("")

# ============================================================
# TEST 2: AUTHENTICATION - GET CURRENT USER
# ============================================================
separator("TEST 2: AUTHENTICATION - GET /wp/v2/users/me")
log("Endpoint: " + ENDPOINT_V2_USERS)
log("Method  : GET with Basic Auth")
try:
    t2 = time.time()
    r2 = requests.get(ENDPOINT_V2_USERS, headers=HEADERS, timeout=15)
    e2 = round(time.time() - t2, 2)
    log("Status : " + str(r2.status_code) + " (" + str(e2) + "s)")
    log("CType  : " + r2.headers.get("Content-Type", ""))

    if r2.status_code == 200:
        d2 = r2.json()
        log("[PASS] AUTH SUCCESSFUL")
        log("User ID: " + str(d2.get("id")))
        log("Name   : " + str(d2.get("name")))
        log("Slug   : " + str(d2.get("slug")))
        log("Email  : " + str(d2.get("email", "n/a")))
        roles = d2.get("roles", [])
        log("Roles  : " + str(roles))
        RESULTS["auth_ok"] = True
        RESULTS["user_id"] = d2.get("id")
        RESULTS["user_display_name"] = d2.get("name")
        RESULTS["user_roles"] = roles
        RESULTS["can_publish"] = any(r in roles for r in ["administrator","editor","author"])
    elif r2.status_code == 401:
        log("[FAIL] HTTP 401 UNAUTHORIZED")
        try:
            err = r2.json()
            log("WP code: " + str(err.get("code")))
            log("WP msg : " + str(err.get("message")))
        except Exception:
            log("Body   : " + r2.text[:300])
        log("")
        log("DIAGNOSIS:")
        log("  USERNAME must be WP login slug (e.g. 'ai-publisher'), NOT email address")
        log("  PASSWORD must be Application Password (from WP Admin > Users > Profile)")
        log("  App Password format: xxxx xxxx xxxx xxxx xxxx xxxx (29 chars with spaces)")
        RESULTS["auth_ok"] = False
        ERRORS.append("401 Unauthorized - check username/password")
    elif r2.status_code == 404:
        log("[FAIL] HTTP 404 - Endpoint not found")
        log("Body: " + r2.text[:200])
        log("DIAGNOSIS: WP_URL is likely still wrong - check for /wp-admin in URL")
        RESULTS["auth_ok"] = False
        ERRORS.append("404 on users/me - check WP_URL")
    else:
        log("[FAIL] Status: " + str(r2.status_code))
        log("Body: " + r2.text[:300])
        RESULTS["auth_ok"] = False
        ERRORS.append("Unexpected status " + str(r2.status_code) + " on auth")
except Exception as e:
    log("[FAIL] " + str(e))
    RESULTS["auth_ok"] = False
    ERRORS.append("Auth error: " + str(e))
log("")

# ============================================================
# TEST 3: CREATE TEMPORARY DRAFT POST
# ============================================================
separator("TEST 3: CREATE TEMPORARY DRAFT POST")
log("Endpoint: " + ENDPOINT_V2_POSTS)
log("Method  : POST with Basic Auth")
draft_id = None

if not RESULTS.get("auth_ok"):
    log("[SKIP] Auth failed - skipping draft creation")
    RESULTS["draft_created"] = False
else:
    payload = {
        "title": "[NEXUS14-AUDIT] Diagnostic draft - safe to delete",
        "content": "<p>Diagnostic post by NEXUS-14 WP Auth Audit. Created: " + TIMESTAMP + "</p>",
        "status": "draft",
    }
    try:
        t3 = time.time()
        r3 = requests.post(ENDPOINT_V2_POSTS, headers=HEADERS, json=payload, timeout=30)
        e3 = round(time.time() - t3, 2)
        log("Status : " + str(r3.status_code) + " (" + str(e3) + "s)")

        if r3.status_code in (200, 201):
            d3 = r3.json()
            draft_id = d3.get("id")
            edit_url = WP_URL_CLEAN + "/wp-admin/post.php?post=" + str(draft_id) + "&action=edit"
            log("[PASS] Draft CREATED")
            log("Post ID  : " + str(draft_id))
            log("Status   : " + str(d3.get("status")))
            log("Edit URL : " + edit_url)
            RESULTS["draft_created"] = True
            RESULTS["draft_id"] = draft_id
            RESULTS["draft_edit_url"] = edit_url
        elif r3.status_code == 401:
            log("[FAIL] 401 - Cannot create post (auth issue)")
            try:
                log("WP error: " + json.dumps(r3.json()))
            except Exception:
                log("Body: " + r3.text[:300])
            RESULTS["draft_created"] = False
            ERRORS.append("401 on POST /posts")
        elif r3.status_code == 403:
            log("[FAIL] 403 - User lacks permission to create posts")
            log("Body: " + r3.text[:300])
            RESULTS["draft_created"] = False
            ERRORS.append("403 on POST /posts - insufficient permissions")
        else:
            log("[FAIL] Status " + str(r3.status_code))
            log("Body: " + r3.text[:400])
            RESULTS["draft_created"] = False
            ERRORS.append("Status " + str(r3.status_code) + " on POST /posts")
    except Exception as e:
        log("[FAIL] " + str(e))
        RESULTS["draft_created"] = False
        ERRORS.append("POST exception: " + str(e))
log("")

# ============================================================
# TEST 4: RETRIEVE THE DRAFT
# ============================================================
separator("TEST 4: RETRIEVE THE DRAFT POST")
if not draft_id:
    log("[SKIP] No draft was created")
    RESULTS["draft_retrieved"] = False
else:
    ep4 = WP_URL_CLEAN + "/wp-json/wp/v2/posts/" + str(draft_id)
    log("Endpoint: " + ep4)
    try:
        t4 = time.time()
        r4 = requests.get(ep4, headers=HEADERS, timeout=15)
        e4 = round(time.time() - t4, 2)
        log("Status : " + str(r4.status_code) + " (" + str(e4) + "s)")
        if r4.status_code == 200:
            d4 = r4.json()
            log("[PASS] Draft retrieved")
            log("ID     : " + str(d4.get("id")))
            log("Status : " + str(d4.get("status")))
            log("Title  : " + str(d4.get("title", {}).get("rendered", "n/a")))
            RESULTS["draft_retrieved"] = True
        else:
            log("[FAIL] Status " + str(r4.status_code))
            RESULTS["draft_retrieved"] = False
            ERRORS.append("GET draft " + str(r4.status_code))
    except Exception as e:
        log("[FAIL] " + str(e))
        RESULTS["draft_retrieved"] = False
        ERRORS.append("GET draft exception: " + str(e))
log("")

# ============================================================
# TEST 5: ENDPOINT CONSTRUCTION AUDIT
# ============================================================
separator("TEST 5: ENDPOINT CONSTRUCTION AUDIT")
log("Verifying URL construction logic (the Run #5 failure point)")
log("")
log("WORDPRESS_URL secret (raw): " + WP_URL_RAW)
log("After .rstrip('/'):         " + WP_URL_RAW.rstrip("/"))
log("After /wp-admin correction: " + WP_URL_CLEAN)
log("")
log("Constructed endpoints:")
log("  Posts : " + WP_URL_CLEAN + "/wp-json/wp/v2/posts")
log("  Media : " + WP_URL_CLEAN + "/wp-json/wp/v2/media")
log("  Users : " + WP_URL_CLEAN + "/wp-json/wp/v2/users/me")
log("")

expected = "https://moneyabroadguide.com"
if WP_URL_CLEAN == expected:
    log("[PASS] URL matches expected: " + expected)
    RESULTS["endpoint_correct"] = True
else:
    log("[WARN] URL differs from expected")
    log("  Expected: " + expected)
    log("  Got:      " + WP_URL_CLEAN)
    RESULTS["endpoint_correct"] = WP_URL_CLEAN.startswith("http") and "/wp-admin" not in WP_URL_CLEAN

# Test what would have happened with /wp-admin in URL
bad_url = "https://moneyabroadguide.com/wp-admin"
bad_endpoint = bad_url.rstrip("/") + "/wp-json/wp/v2/posts"
log("")
log("RECONSTRUCTION OF RUN #5 FAILURE:")
log("  Secret was  : " + bad_url)
log("  Constructed : " + bad_endpoint)
log("  Result      : HTTP 404 <!DOCTYPE html> (WP admin login page)")
log("  This is why Run #5 reported wordpress_draft_created = FAIL")
log("")

# ============================================================
# FINAL VERDICT
# ============================================================
separator("FINAL VERDICT")

tests = {
    "env_valid"        : RESULTS.get("env_valid", False),
    "api_root_ok"      : RESULTS.get("api_root_ok", False),
    "wp_v2_active"     : RESULTS.get("wp_v2_active", False),
    "auth_ok"          : RESULTS.get("auth_ok", False),
    "draft_created"    : RESULTS.get("draft_created", False),
    "draft_retrieved"  : RESULTS.get("draft_retrieved", False),
    "endpoint_correct" : RESULTS.get("endpoint_correct", False),
}

passed = sum(1 for v in tests.values() if v)
total = len(tests)

for name, val in tests.items():
    log(("[PASS] " if val else "[FAIL] ") + name)

log("")
log("Score: " + str(passed) + "/" + str(total))
log("")

critical_ok = tests["auth_ok"] and tests["draft_created"] and tests["endpoint_correct"]

if critical_ok:
    verdict = "PASS"
    log("VERDICT: PASS - WordPress fully operational")
    log("  Authentication: OK")
    log("  Endpoint:       OK")
    log("  Draft create:   OK")
else:
    verdict = "FAIL"
    log("VERDICT: FAIL - WordPress has issues")
    if ERRORS:
        log("Errors found:")
        for err in ERRORS:
            log("  - " + err)
    log("")
    log("RECOMMENDED FIXES:")
    if any("/wp-admin" in e for e in ERRORS):
        log("  1. WORDPRESS_URL secret must be base URL only:")
        log("     Correct: https://moneyabroadguide.com")
        log("     Wrong  : https://moneyabroadguide.com/wp-admin")
    if any("401" in e for e in ERRORS):
        log("  2. WORDPRESS_USERNAME must be login slug (not email):")
        log("     Correct: ai-publisher")
        log("     Wrong  : ai.publisher.mag@gmail.com")
        log("  3. WORDPRESS_PASSWORD must be an Application Password")
        log("     Generate: WP Admin > Users > Profile > Application Passwords")
        log("     Format : xxxx xxxx xxxx xxxx xxxx xxxx (29 chars)")

log("")
RESULTS["verdict"] = verdict
RESULTS["errors"] = ERRORS
RESULTS["score"] = str(passed) + "/" + str(total)
RESULTS["timestamp"] = TIMESTAMP
RESULTS["wp_url_raw"] = WP_URL_RAW
RESULTS["wp_url_used"] = WP_URL_CLEAN

with open("wp_auth_audit.json", "w") as f:
    json.dump(RESULTS, f, indent=2)

log("Report saved: wp_auth_audit.json")
separator()

if verdict == "FAIL":
    sys.exit(1)
