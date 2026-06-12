# NEXUS-14 V3 — GitHub Secrets Setup Guide
# MoneyAbroadGuide.com Autonomous Newsroom
# Generated: 2026-06-12 | Version: 3.0.0
# ============================================================
#
# HOW TO ADD SECRETS:
# 1. Go to: https://github.com/talalnewjersey-ops/mag-autonomous-newsroom-v1/settings/secrets/actions
# 2. Click "New repository secret"
# 3. Enter the Name and Value exactly as listed below
# 4. Click "Add secret"
# ============================================================

# COMPLETE SECRETS INVENTORY — NEXUS-14 V3
# Total required: 14 secrets
# Currently configured: 8 (some with wrong names)
# Missing: 6
# Name mismatches: 2

---

## STATUS LEGEND

| Symbol | Meaning |
|--------|---------|
| OK | Secret exists with correct name |
| FIX | Secret exists but with WRONG name — must add with correct name |
| MISSING | Secret does not exist — must be added before production |
| OPTIONAL | Not required for core production |

---

## SECTION 1: CORE AI APIS (Required)

### 1. ANTHROPIC_API_KEY
- **Status:** OK (already configured)
- **Required:** YES — CRITICAL
- **Used in:** Agents 01, 02, 03, 04, 05, 06, 07, 08, 12, 13, 14, 15, 16, 17, 18
- **Get from:** https://console.anthropic.com/settings/keys
- **Format:** sk-ant-api03-...
- **Notes:** Core article writing engine. Without this, NOTHING works.

### 2. GEMINI_API_KEY
- **Status:** MISSING — MUST ADD
- **Required:** YES — CRITICAL (Image Generation)
- **Used in:** Agent 10 (Phase 10 — Image Production)
- **Get from:** https://aistudio.google.com/apikey
- **Format:** AIza...
- **Secret name to use:** GEMINI_API_KEY
- **Notes:** Primary image generation API. If missing, Agent 10 falls back to OpenAI DALL-E.

---

## SECTION 2: SEO & KEYWORD TOOLS (Required)

### 3. SERPAPI_KEY
- **Status:** MISSING — MUST ADD
- **Required:** YES — CRITICAL (Topic Research)
- **Used in:** Agent 01 (SEO Research), Agent 02 (Keyword Validation)
- **Get from:** https://serpapi.com/dashboard
- **Format:** long alphanumeric string
- **Secret name to use:** SERPAPI_KEY
- **Notes:** Required for real keyword research and SERP analysis.

### 4. SEMRUSH_API_KEY
- **Status:** MISSING — MUST ADD
- **Required:** YES — CRITICAL (Keyword Difficulty)
- **Used in:** Agent 01 (SEO Research)
- **Get from:** https://www.semrush.com/api-documentation/
- **Format:** long alphanumeric string
- **Secret name to use:** SEMRUSH_API_KEY
- **Notes:** Required for keyword difficulty scoring used in STANDARD vs PILLAR classification.

---

## SECTION 3: WORDPRESS INTEGRATION (Required)

### 5. WORDPRESS_URL
- **Status:** OK (already configured)
- **Required:** YES — CRITICAL
- **Used in:** Agents 11, 07, 16 (WordPress Integration, Internal Linking, Publishing)
- **Format:** https://moneyabroadguide.com
- **Notes:** Must be the root domain, no trailing slash.

### 6. WORDPRESS_USERNAME
- **Status:** OK (already configured)
- **Required:** YES — CRITICAL
- **Used in:** Agent 11 (WordPress REST API authentication)
- **Format:** WordPress username (not email)
- **Notes:** Must be an admin or editor user with REST API access.

### 7. WORDPRESS_APP_PASSWORD
- **Status:** FIX REQUIRED
- **Current name in GitHub:** WORDPRESS_PASSWORD (WRONG)
- **Required name in workflow:** WORDPRESS_APP_PASSWORD
- **Required:** YES — CRITICAL
- **Used in:** Agents 11 (Phase 11 — WordPress draft creation), Agent 17 (Cannibalization scan)
- **Get from:** WordPress Admin > Users > Your Profile > Application Passwords > Add New
- **Format:** xxxx xxxx xxxx xxxx xxxx xxxx (spaces included)
- **Action required:**
  1. Go to Settings > Secrets > Actions
  2. Add NEW secret named: WORDPRESS_APP_PASSWORD
  3. Copy the value from WORDPRESS_PASSWORD
  4. Optionally delete WORDPRESS_PASSWORD (old name)
- **Notes:** WordPress Application Password (NOT your login password). Must be generated in WP Admin.

---

## SECTION 4: IMAGE GENERATION (Required)

### 8. NANO_BANANA_KEY
- **Status:** FIX REQUIRED
- **Current name in GitHub:** NANO_BANANA_API_KEY (WRONG)
- **Required name in workflow:** NANO_BANANA_KEY
- **Required:** YES (Fallback image generation)
- **Used in:** Agent 10 (Phase 10 — Image Production, fallback API)
- **Action required:**
  1. Go to Settings > Secrets > Actions
  2. Add NEW secret named: NANO_BANANA_KEY
  3. Copy the value from NANO_BANANA_API_KEY
  4. Optionally delete NANO_BANANA_API_KEY (old name)
- **Notes:** Nano Banana is the fallback image API when Gemini is unavailable.

### 9. OPENAI_API_KEY
- **Status:** OK (already configured)
- **Required:** Optional (second fallback for image generation)
- **Used in:** Agent 10 (DALL-E 3 fallback)
- **Notes:** Used only if both Gemini and Nano Banana fail.

---

## SECTION 5: AWS S3 STORAGE (Required for image hosting)

### 10. AWS_ACCESS_KEY_ID
- **Status:** MISSING — MUST ADD
- **Required:** YES — CRITICAL (Image Upload & Hosting)
- **Used in:** Agent 10 (image upload to S3 for WordPress)
- **Get from:** AWS Console > IAM > Users > Security Credentials
- **Format:** AKIA...
- **Secret name to use:** AWS_ACCESS_KEY_ID
- **Notes:** IAM user must have S3 PutObject, GetObject, PutObjectAcl permissions.

### 11. AWS_SECRET_ACCESS_KEY
- **Status:** MISSING — MUST ADD
- **Required:** YES — CRITICAL (Image Upload & Hosting)
- **Used in:** Agent 10 (paired with AWS_ACCESS_KEY_ID)
- **Get from:** AWS Console > IAM > Users > Security Credentials (shown only once)
- **Format:** 40-character string
- **Secret name to use:** AWS_SECRET_ACCESS_KEY
- **Notes:** Store securely — cannot be retrieved after initial creation.

### 12. S3_BUCKET
- **Status:** MISSING — MUST ADD
- **Required:** YES — CRITICAL (Image Hosting)
- **Used in:** Agent 10 (target bucket for image upload)
- **Format:** bucket-name (no s3:// prefix, no trailing slash)
- **Example:** moneyabroadguide-images
- **Secret name to use:** S3_BUCKET
- **Notes:** Bucket must be in us-east-1 or configure AWS_REGION accordingly. Must have public read ACL enabled or use CloudFront.

---

## SECTION 6: EMAIL NOTIFICATIONS (Required for reports)

### 13. SENDGRID_API_KEY
- **Status:** OK (already configured)
- **Required:** YES (Production Reports)
- **Used in:** Agent 14 (Production Director — daily reports)
- **Get from:** https://app.sendgrid.com/settings/api_keys
- **Format:** SG.xxx...
- **Notes:** Required for executive reports and alerts.

### 14. EMAIL_RECIPIENT
- **Status:** OK (already configured)
- **Required:** YES (Production Reports)
- **Used in:** Agent 14 (sends daily production report to this address)
- **Format:** email@domain.com
- **Notes:** Must be a verified sender address in SendGrid.

---

## COMPLETE CHECKLIST BEFORE FIRST PRODUCTION RUN

### Immediate Actions Required (Blockers):

- [ ] **ADD** GEMINI_API_KEY (new secret — image generation)
- [ ] **ADD** SERPAPI_KEY (new secret — SEO research)
- [ ] **ADD** SEMRUSH_API_KEY (new secret — keyword difficulty)
- [ ] **ADD** WORDPRESS_APP_PASSWORD (rename from WORDPRESS_PASSWORD)
- [ ] **ADD** NANO_BANANA_KEY (rename from NANO_BANANA_API_KEY)
- [ ] **ADD** AWS_ACCESS_KEY_ID (new secret — image hosting)
- [ ] **ADD** AWS_SECRET_ACCESS_KEY (new secret — image hosting)
- [ ] **ADD** S3_BUCKET (new secret — image hosting bucket name)

### Already Configured (No Action Needed):

- [x] ANTHROPIC_API_KEY
- [x] OPENAI_API_KEY
- [x] SENDGRID_API_KEY
- [x] EMAIL_RECIPIENT
- [x] WORDPRESS_URL
- [x] WORDPRESS_USERNAME

---

## VALIDATION — After Adding All Secrets

After adding all required secrets, trigger a test run:

1. Go to: Actions > NEXUS-14 V3 — Quality-First Production
2. Click "Run workflow"
3. Set mode: end_to_end_test
4. Set topic: "How to Open a Bank Account as an Immigrant in the USA"
5. Set max_articles: 1
6. Click "Run workflow"

Expected result: Workflow completes all 18 quality gates and creates a WordPress draft.

---

## SECURITY NOTES

- Never commit secrets to the repository — always use GitHub Secrets
- Rotate ANTHROPIC_API_KEY and GEMINI_API_KEY monthly
- Use separate AWS IAM user for S3 with minimal permissions (S3 only)
- WordPress Application Password can be revoked anytime in WP Admin without changing your login password
- SerpAPI key has rate limits — monitor usage at serpapi.com/dashboard

---

*Generated by NEXUS-14 V3 — Production Blockers Resolution | 2026-06-12*
