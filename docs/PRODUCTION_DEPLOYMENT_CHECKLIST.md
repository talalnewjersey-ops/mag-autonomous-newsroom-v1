# NEXUS-14 V3 — Production Deployment Checklist
# MoneyAbroadGuide.com Quality-First Autonomous Newsroom
# Version: 3.1.0 | Updated: 2026-06-12
# ============================================================
#
# V3.1 CHANGES:
#   - SERPAPI_KEY: OPTIONAL (removed as blocker)
#   - SEMRUSH_API_KEY: OPTIONAL (removed as blocker)
#   - AWS S3: REMOVED (WordPress Media Library handles images)
#   - Minimum required secrets: 5 (ANTHROPIC + GEMINI + WP credentials)
#
# INSTRUCTIONS:
# Work through each section in order.
# Items marked BLOCKER must be resolved before any production run.
# Items marked OPTIONAL enhance quality but do not block production.
# ============================================================

## MINIMUM VIABLE PRODUCTION (MVP) SECRET SET

Before anything else, confirm you can answer YES to all of these:

- [ ] I have an active Anthropic API key (ANTHROPIC_API_KEY) — REQUIRED
- [ ] I have a Google AI Studio API key (GEMINI_API_KEY) — REQUIRED for images
- [ ] I have a WordPress site with REST API enabled — REQUIRED
- [ ] I have a WordPress Application Password — REQUIRED (BLOCKER: rename needed)

If YES to all 4: you can run production. SERPAPI and SEMRUSH are NOT needed.

---

## SECTION 1: GitHub Repository Setup

- [ ] Admin access to: https://github.com/talalnewjersey-ops/mag-autonomous-newsroom-v1
- [ ] GitHub Actions is enabled (Settings > Actions > Allow all actions)
- [ ] Main branch is the production branch

### Repository Structure Check:
- [ ] agents/agent_01_seo_research.py (V3 rewrite — no SERPAPI required)
- [ ] agents/agent_02_keyword_validation.py (V3 rewrite — no external APIs)
- [ ] agents/agent_10_image_production.py (V3.1 — WordPress Media Library upload)
- [ ] agents/agent_17_cannibalization.py
- [ ] agents/agent_18_revenue_intelligence.py
- [ ] config/config_loader.py (required for all agents)
- [ ] scripts/v2_quality_gate.py (18 gates)
- [ ] .github/workflows/production_v2.yml

---

## SECTION 2: GitHub Secrets — REQUIRED (Blockers)

Path: Settings > Secrets and variables > Actions > New repository secret

### BLOCKER 1: WORDPRESS_APP_PASSWORD (rename from WORDPRESS_PASSWORD)
- [ ] Go to WordPress Admin > Users > Your Profile > Application Passwords
- [ ] Generate Application Password named "NEXUS-14 V3"
- [ ] Add GitHub secret: Name = WORDPRESS_APP_PASSWORD
- [ ] Value = the generated Application Password
- **Test:** curl -u "username:app_password" https://yoursite.com/wp-json/wp/v2/users/me

### BLOCKER 2: GEMINI_API_KEY (new — needed for image generation)
- [ ] Go to: https://aistudio.google.com/apikey
- [ ] Create or copy API key
- [ ] Add GitHub secret: Name = GEMINI_API_KEY, Value = AIza...
- **Why required:** Without at least one image API key, Agent 10 produces no images → Gate 2 fails

---

## SECTION 3: GitHub Secrets — ALREADY CONFIGURED (Verify)

These are already in GitHub Secrets. Verify they are still valid:

- [ ] ANTHROPIC_API_KEY — Active (test: call Claude API)
- [ ] WORDPRESS_URL — Correct URL with https://
- [ ] WORDPRESS_USERNAME — WordPress admin username
- [ ] OPENAI_API_KEY — Optional image fallback (already set)
- [ ] SENDGRID_API_KEY — Optional email reports (already set)
- [ ] EMAIL_RECIPIENT — Optional email reports (already set)

---

## SECTION 4: GitHub Secrets — OPTIONAL (Not Blockers)

These improve quality but production runs without them:

- [ ] SERPAPI_KEY — Enhanced topic research (OPTIONAL)
  - Without it: Agent 01 uses Claude AI + 20 built-in curated expat finance topics
  - Production continues normally

- [ ] SEMRUSH_API_KEY — Keyword difficulty data (OPTIONAL)
  - Without it: Built-in difficulty scores used
  - Production continues normally

- [ ] NANO_BANANA_KEY — Image generation fallback (OPTIONAL, rename from NANO_BANANA_API_KEY)
  - Without it: Agent 10 falls back to OPENAI_API_KEY for DALL-E 3

### REMOVED — No Longer Needed:
- AWS_ACCESS_KEY_ID — REMOVED (WordPress Media Library replaces S3)
- AWS_SECRET_ACCESS_KEY — REMOVED
- S3_BUCKET — REMOVED

---

## SECTION 5: WordPress Setup

### 5.1 Core Requirements
- [ ] WordPress version >= 5.6 (REST API v2)
- [ ] REST API accessible: GET https://yoursite.com/wp-json/wp/v2/ returns JSON
- [ ] Rank Math SEO plugin installed and activated

### 5.2 Authentication
- [ ] WordPress user has Editor or Administrator role
- [ ] Application Password generated (WORDPRESS_APP_PASSWORD secret set)
- [ ] Test: curl -X GET https://yoursite.com/wp-json/wp/v2/posts -u "user:app_password"

### 5.3 Media Library (replaces S3)
- [ ] WordPress Media Library accessible via REST API
- [ ] Test image upload: curl -X POST https://yoursite.com/wp-json/wp/v2/media -u "user:app_password" -H "Content-Type: image/jpeg" -H "Content-Disposition: attachment; filename=test.jpg" --data-binary @test.jpg
- [ ] Verify uploaded image appears in Media Library
- [ ] Verify image URL is publicly accessible

### 5.4 Content Setup
- [ ] Author profile exists with bio (required for Gate 8)
- [ ] At least 5 published posts (for internal linking, Agent 07)
- [ ] Categories exist: immigrants-usa, immigrants-canada, banking, credit, taxes

---

## SECTION 6: Anthropic (Claude) Setup — REQUIRED

- [ ] API key active at https://console.anthropic.com
- [ ] Sufficient credits (estimate: $5-15 per article)
- [ ] claude-3-5-sonnet-20241022 model accessible
- [ ] Test: curl https://api.anthropic.com/v1/messages with your key

---

## SECTION 7: Gemini Setup — REQUIRED for Images

- [ ] API key active at https://aistudio.google.com
- [ ] Imagen 3 model accessible: imagen-3.0-generate-001
- [ ] Billing enabled in Google Cloud (Imagen 3 requires billing)
- [ ] Test API key works with a simple generation request

---

## SECTION 8: Optional Services

### Nano Banana (Image Fallback) — OPTIONAL
- [ ] If you have a Nano Banana account: add NANO_BANANA_KEY secret (rename from NANO_BANANA_API_KEY)
- [ ] If not: Agent 10 will use DALL-E 3 (OPENAI_API_KEY already set)

### SerpAPI — OPTIONAL
- [ ] If you want enhanced topic research: add SERPAPI_KEY secret
- [ ] Without it: built-in topic database used (20 curated expat finance topics)

### SEMrush — OPTIONAL
- [ ] If you want accurate keyword difficulty data: add SEMRUSH_API_KEY secret
- [ ] Without it: built-in difficulty scores used

### SendGrid — For Email Reports Only
- [ ] SENDGRID_API_KEY already set — only needed for Agent 14 email reports
- [ ] Production pipeline does not depend on this

---

## SECTION 9: Pre-Production Validation Run

### 9.1 Trigger Test Run
1. Go to: Actions > NEXUS-14 V3 — Quality-First Production
2. Click "Run workflow"
3. Mode: batch_1
4. Max articles: 1
5. Monitor each step

### 9.2 Expected Pass/Fail with Minimum 5 Secrets

| Phase | Expected Result | Notes |
|-------|----------------|-------|
| Route — Identify Trigger Mode | PASS | Always passes |
| Phase 1 — SEO Research (Agent 01) | PASS | Uses built-in DB if no SERPAPI |
| Phase 2 — Keyword Validation (Agent 02) | PASS | No external APIs needed |
| Phase 2.5 — Cannibalization (Agent 17) | PASS | Uses ANTHROPIC_API_KEY |
| Phase 2.6 — Revenue Intelligence (Agent 18) | PASS | Uses ANTHROPIC_API_KEY |
| Phase 3-13 — Content + QA | PASS | Uses ANTHROPIC_API_KEY |
| Phase 10 — Images | PASS | Uses GEMINI_API_KEY |
| Phase 11 — WordPress | PASS | Uses WP credentials |

### 9.3 Success Criteria
- [ ] Workflow runs without errors through Phase 2.6 (Revenue Intelligence)
- [ ] WordPress draft created with real Post ID
- [ ] Images uploaded to WordPress Media Library with real URLs
- [ ] quality_gate_result.json shows "status": "READY_TO_PUBLISH"

---

## SECTION 10: Go-Live Authorization

- [ ] All sections 1-9 completed
- [ ] Test run produced a WordPress draft
- [ ] Draft reviewed and approved by editor
- [ ] Schedule is active (batches at 06:00 UTC and 13:00 UTC)

### Emergency Stop:
Settings > Actions > Disable "NEXUS-14 V3 — Quality-First Production"

---

*NEXUS-14 V3.1 Production Deployment Checklist | SERPAPI/SEMRUSH optional | S3 removed | 2026-06-12*
