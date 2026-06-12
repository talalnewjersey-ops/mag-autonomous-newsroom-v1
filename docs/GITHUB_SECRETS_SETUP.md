# NEXUS-14 V3 — GitHub Secrets Setup Guide
# MoneyAbroadGuide.com Autonomous Newsroom
# Updated: 2026-06-12 | Version: 3.1.0 (SERPAPI/SEMRUSH/S3 made optional)
# ============================================================
#
# KEY CHANGES IN V3.1:
#   - SERPAPI_KEY:     NOW OPTIONAL (Claude + built-in DB fallback)
#   - SEMRUSH_API_KEY: NOW OPTIONAL (built-in difficulty scores fallback)
#   - AWS_ACCESS_KEY_ID:     REMOVED (WordPress Media Library replaces S3)
#   - AWS_SECRET_ACCESS_KEY: REMOVED (WordPress Media Library replaces S3)
#   - S3_BUCKET:             REMOVED (WordPress Media Library replaces S3)
#
# HOW TO ADD SECRETS:
# 1. Go to: https://github.com/talalnewjersey-ops/mag-autonomous-newsroom-v1/settings/secrets/actions
# 2. Click "New repository secret"
# 3. Enter the Name and Value exactly as listed below
# 4. Click "Add secret"
# ============================================================

# MINIMUM VIABLE PRODUCTION SET
# These 5 secrets are sufficient to run full production:
#
#   ANTHROPIC_API_KEY        (article writing, research, all AI tasks)
#   GEMINI_API_KEY           (image generation)
#   WORDPRESS_URL            (post creation)
#   WORDPRESS_USERNAME       (authentication)
#   WORDPRESS_APP_PASSWORD   (authentication + image upload)
#
# Everything else is optional or enhances quality.

---

## STATUS LEGEND

| Symbol | Meaning |
|--------|---------|
| REQUIRED | Must have for production to run |
| OPTIONAL | Enhances quality; production runs without it |
| FIX | Wrong name configured — add with correct name |
| REMOVED | No longer needed in V3.1 |

---

## SECTION 1: REQUIRED SECRETS (Production Cannot Run Without These)

### 1. ANTHROPIC_API_KEY
- **Status:** REQUIRED — Already configured OK
- **Used by:** ALL agents (01 through 18)
- **Purpose:** Claude API for article writing, research, quality analysis
- **Get from:** https://console.anthropic.com/settings/keys
- **Format:** sk-ant-api03-...
- **Impact if missing:** NOTHING works. This is the core engine.

### 2. WORDPRESS_URL
- **Status:** REQUIRED — Already configured OK
- **Used by:** Agents 07, 10, 11, 16, 17
- **Purpose:** WordPress REST API base URL
- **Format:** https://moneyabroadguide.com (no trailing slash)
- **Impact if missing:** No posts created, no images uploaded

### 3. WORDPRESS_USERNAME
- **Status:** REQUIRED — Already configured OK
- **Used by:** Agents 10, 11, 17 (REST API authentication)
- **Format:** WordPress username (not email)
- **Impact if missing:** All WordPress API calls fail

### 4. WORDPRESS_APP_PASSWORD
- **Status:** FIX REQUIRED
- **Current name in GitHub:** WORDPRESS_PASSWORD (WRONG)
- **Required name:** WORDPRESS_APP_PASSWORD
- **Used by:** Agents 10 (image upload), 11 (post creation), 17 (cannibalization scan)
- **Get from:** WordPress Admin > Users > Profile > Application Passwords > Add New
- **Format:** xxxx xxxx xxxx xxxx xxxx xxxx (spaces included)
- **Action:**
  1. Settings > Secrets > Actions > New repository secret
  2. Name: WORDPRESS_APP_PASSWORD
  3. Value: copy from WORDPRESS_PASSWORD secret
- **Impact if missing:** No posts created, no images uploaded to WordPress

---

## SECTION 2: RECOMMENDED SECRETS (Image Generation)

### 5. GEMINI_API_KEY
- **Status:** RECOMMENDED (not strictly required)
- **Used by:** Agent 10 (primary image generation)
- **Purpose:** Generate article images via Google Imagen 3
- **Get from:** https://aistudio.google.com/apikey
- **Format:** AIza...
- **Impact if missing:** Falls back to NANO_BANANA_KEY or OPENAI_API_KEY. If none present, images fail (Gate 2 fails).
- **Note:** At least ONE image generation key (Gemini, Nano Banana, or OpenAI) is needed for full pipeline.

### 6. NANO_BANANA_KEY
- **Status:** FIX REQUIRED (if you want Nano Banana fallback)
- **Current name in GitHub:** NANO_BANANA_API_KEY (WRONG)
- **Required name:** NANO_BANANA_KEY
- **Used by:** Agent 10 (fallback image generation)
- **Action:** Add secret named NANO_BANANA_KEY with value from NANO_BANANA_API_KEY
- **Impact if missing:** Agent 10 skips Nano Banana, tries next API

### 7. OPENAI_API_KEY
- **Status:** Already configured OK (second fallback for images)
- **Used by:** Agent 10 (DALL-E 3 as second fallback)
- **Impact if missing:** Falls through to no image generation

---

## SECTION 3: OPTIONAL SECRETS (Enhanced SEO Research)

### 8. SERPAPI_KEY
- **Status:** OPTIONAL — Production continues without it
- **Used by:** Agent 01 (live SERP data enhancement)
- **Fallback behavior when missing:**
  - Agent 01 uses Claude AI to generate topic ideas
  - Agent 01 uses built-in curated topic database (20 pre-qualified topics)
  - Production continues normally — no failure, no degradation of quality gate
- **Impact if present:** Higher quality, more current topic research
- **Impact if absent:** Production runs with built-in topic database. No failure.
- **Get from:** https://serpapi.com/dashboard

### 9. SEMRUSH_API_KEY
- **Status:** OPTIONAL — Production continues without it
- **Used by:** Agent 01 (keyword difficulty scoring from SEMrush data)
- **Fallback behavior when missing:**
  - Agent 01 uses built-in difficulty scores from curated database
  - STANDARD vs PILLAR classification still works
  - Production continues normally
- **Impact if present:** More accurate keyword difficulty data from SEMrush
- **Impact if absent:** Built-in difficulty scores used. No failure.
- **Get from:** https://www.semrush.com/api-documentation/

---

## SECTION 4: OPTIONAL SECRETS (Reporting)

### 10. SENDGRID_API_KEY
- **Status:** Already configured OK
- **Used by:** Agent 14 (executive reports by email)
- **Impact if missing:** No email reports sent. Production pipeline unaffected.

### 11. EMAIL_RECIPIENT
- **Status:** Already configured OK
- **Used by:** Agent 14 (destination for email reports)

---

## SECTION 5: REMOVED SECRETS (No Longer Needed in V3.1)

The following secrets are NO LONGER USED. You may keep them (they are ignored) or delete them.

### AWS_ACCESS_KEY_ID — REMOVED
- **Why removed:** Images now upload to WordPress Media Library instead of S3
- **Replaced by:** WORDPRESS_APP_PASSWORD (already handles image upload via REST API)

### AWS_SECRET_ACCESS_KEY — REMOVED
- **Why removed:** Same as above

### S3_BUCKET — REMOVED
- **Why removed:** Same as above

---

## MINIMUM VIABLE PRODUCTION — VERIFICATION TABLE

Can production run with only these 5 secrets?

| Secret | Status | If Missing |
|--------|--------|-----------|
| ANTHROPIC_API_KEY | Already set | ALL agents fail |
| GEMINI_API_KEY | Need to add | Images fail (Gate 2 fails) |
| WORDPRESS_URL | Already set | Posts/images fail |
| WORDPRESS_USERNAME | Already set | Posts/images fail |
| WORDPRESS_APP_PASSWORD | Need to add (rename) | Posts/images fail |

**Answer: YES** — with these 5 secrets, full production runs successfully:
- Topics: Built-in curated database (20 pre-qualified expat finance topics)
- Research: Claude AI (ANTHROPIC_API_KEY)
- Images: Gemini Imagen 3 (GEMINI_API_KEY) → uploaded to WordPress Media Library
- Posts: WordPress REST API (WORDPRESS credentials)
- Quality gates: All 18 gates evaluated

No SERPAPI, no SEMRUSH, no AWS S3 required.

---

## COMPLETE ACTIONS CHECKLIST

### Must Do — Blockers:
- [ ] Add **WORDPRESS_APP_PASSWORD** (rename from WORDPRESS_PASSWORD)
- [ ] Add **GEMINI_API_KEY** (for image generation)

### Recommended:
- [ ] Add **NANO_BANANA_KEY** (rename from NANO_BANANA_API_KEY — image fallback)

### Optional Enhancements:
- [ ] Add **SERPAPI_KEY** (better topic research — not required)
- [ ] Add **SEMRUSH_API_KEY** (better keyword difficulty — not required)

### No Action Needed — Already Correct:
- [x] ANTHROPIC_API_KEY
- [x] OPENAI_API_KEY
- [x] SENDGRID_API_KEY
- [x] EMAIL_RECIPIENT
- [x] WORDPRESS_URL
- [x] WORDPRESS_USERNAME

### Deprecated — Can Keep or Delete:
- [ ] WORDPRESS_PASSWORD (superseded by WORDPRESS_APP_PASSWORD)
- [ ] NANO_BANANA_API_KEY (superseded by NANO_BANANA_KEY)
- [ ] AWS_ACCESS_KEY_ID (removed in V3.1)
- [ ] AWS_SECRET_ACCESS_KEY (removed in V3.1)
- [ ] S3_BUCKET (removed in V3.1)

---

*NEXUS-14 V3.1 — GitHub Secrets Setup Guide | MoneyAbroadGuide.com | Updated 2026-06-12*
*SERPAPI + SEMRUSH now OPTIONAL | AWS S3 REMOVED | WordPress Media Library for images*
