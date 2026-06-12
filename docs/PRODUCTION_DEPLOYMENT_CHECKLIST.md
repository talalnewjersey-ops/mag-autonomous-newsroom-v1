# NEXUS-14 V3 — Production Deployment Checklist
# MoneyAbroadGuide.com Quality-First Autonomous Newsroom
# Version: 3.0.0 | Date: 2026-06-12
# ============================================================
#
# INSTRUCTIONS:
# Work through each section in order.
# Do NOT proceed to the next section until the current one is complete.
# Mark each item with [x] when completed.
# Items marked BLOCKER must be resolved before any production run.
# ============================================================

## SECTION 1: GitHub Repository Setup

### 1.1 Repository Access
- [ ] You have admin access to: https://github.com/talalnewjersey-ops/mag-autonomous-newsroom-v1
- [ ] GitHub Actions is enabled (Settings > Actions > Allow all actions)
- [ ] Main branch protection is configured (optional but recommended)

### 1.2 Repository Structure Verified
- [ ] agents/ directory contains 18 agents (01 through 18)
- [ ] scripts/ directory contains v2_quality_gate.py
- [ ] config/ directory contains nexus14_v2_config.yaml and article_strategy.json
- [ ] .github/workflows/production_v2.yml exists
- [ ] docs/ directory contains all documentation

---

## SECTION 2: GitHub Secrets Configuration (BLOCKERS)

### 2.1 Secrets with Wrong Names — FIX REQUIRED
Path: Settings > Secrets and variables > Actions > New repository secret

- [ ] **WORDPRESS_APP_PASSWORD** — Add with value from WORDPRESS_PASSWORD
  - Go to WordPress Admin > Users > Profile > Application Passwords
  - Generate a new Application Password named "NEXUS-14 V3"
  - Add as GitHub secret: WORDPRESS_APP_PASSWORD
  - Test: curl -u "username:app_password" https://yoursite.com/wp-json/wp/v2/posts

- [ ] **NANO_BANANA_KEY** — Add with value from NANO_BANANA_API_KEY
  - Copy value from existing NANO_BANANA_API_KEY secret
  - Add new secret named exactly: NANO_BANANA_KEY
  - Verify at: https://nanobanana.ai/dashboard

### 2.2 Missing Secrets — MUST ADD
- [ ] **GEMINI_API_KEY** — Google AI Studio
  - Get from: https://aistudio.google.com/apikey
  - Required for: Image generation (Agent 10)
  - Format: AIza...

- [ ] **SERPAPI_KEY** — SerpAPI
  - Get from: https://serpapi.com/dashboard
  - Required for: SEO research (Agents 01, 02)
  - Note: Free plan = 100 searches/month; production needs paid plan

- [ ] **SEMRUSH_API_KEY** — SEMrush
  - Get from: https://www.semrush.com/api-documentation/
  - Required for: Keyword difficulty (Agent 01)
  - Note: Requires active SEMrush subscription

- [ ] **AWS_ACCESS_KEY_ID** — Amazon Web Services
  - Get from: AWS Console > IAM > Users > Security Credentials
  - Required for: Image hosting (Agent 10 uploads to S3)
  - Create dedicated IAM user with S3-only permissions

- [ ] **AWS_SECRET_ACCESS_KEY** — Amazon Web Services
  - Paired with AWS_ACCESS_KEY_ID
  - Generated at same time as Access Key ID

- [ ] **S3_BUCKET** — S3 bucket name
  - Create S3 bucket in AWS Console
  - Enable public read access or configure CloudFront
  - Enter bucket name only (e.g.: moneyabroadguide-images)

### 2.3 Already Configured — No Action Needed
- [x] ANTHROPIC_API_KEY
- [x] OPENAI_API_KEY (fallback for images)
- [x] SENDGRID_API_KEY
- [x] EMAIL_RECIPIENT
- [x] WORDPRESS_URL
- [x] WORDPRESS_USERNAME

---

## SECTION 3: WordPress Setup

### 3.1 WordPress Version & Plugins
- [ ] WordPress version >= 5.6 (REST API v2 required)
- [ ] Rank Math SEO plugin installed and activated
- [ ] REST API accessible: https://yoursite.com/wp-json/wp/v2/ returns JSON

### 3.2 WordPress User Permissions
- [ ] WordPress user (from WORDPRESS_USERNAME) has Editor or Administrator role
- [ ] Application Password generated for this user (WORDPRESS_APP_PASSWORD)
- [ ] Test authentication: curl -u "username:app_password" https://yoursite.com/wp-json/wp/v2/users/me

### 3.3 WordPress Content Setup
- [ ] Author profile exists with bio (used in Gate 8)
- [ ] At least 5 existing published posts (for internal linking, Agent 07)
- [ ] Categories created: immigrants-usa, immigrants-canada, banking, credit, taxes, insurance
- [ ] Featured image size configured: 1200x630px minimum

### 3.4 WordPress Test
- [ ] Create test draft via REST API and confirm it appears in WordPress admin
- [ ] Upload test image via REST API and confirm it uploads
- [ ] Verify featured image can be set via REST API

---

## SECTION 4: Anthropic (Claude) Setup

### 4.1 API Access
- [ ] API key is active (verify at https://console.anthropic.com)
- [ ] Sufficient credits available (estimate: $5-15 per article)
- [ ] Rate limits are adequate for production (3 articles x ~20 API calls = 60 calls per batch)

### 4.2 Model Availability
- [ ] Claude claude-3-5-sonnet-20241022 model is accessible
- [ ] Test: curl with ANTHROPIC_API_KEY returns valid response

---

## SECTION 5: Gemini Setup (Image Generation)

### 5.1 API Access
- [ ] Gemini API key is active (verify at https://aistudio.google.com)
- [ ] Imagen 3 model is accessible: imagen-3.0-generate-001
- [ ] Sufficient quota available (estimate: 5-7 images per article)

### 5.2 Billing
- [ ] Google Cloud billing is enabled (Imagen 3 requires billing)
- [ ] Monthly budget alert configured to avoid unexpected charges

---

## SECTION 6: Nano Banana Setup (Image Fallback)

### 6.1 API Access
- [ ] Account active at https://nanobanana.ai
- [ ] API key copied to GitHub secret NANO_BANANA_KEY (correct name)
- [ ] Sufficient credits for fallback generation

### 6.2 Test
- [ ] Test API call returns successful image generation
- [ ] Endpoint https://api.nanobanana.ai/v1/generate is responding

---

## SECTION 7: AWS S3 Setup (Image Hosting)

### 7.1 S3 Bucket Configuration
- [ ] Bucket created in us-east-1 (or configure AWS_REGION secret)
- [ ] Bucket name matches S3_BUCKET secret
- [ ] Public read access enabled for image URLs
- [ ] CORS policy configured to allow WordPress domain

### 7.2 IAM User Configuration
- [ ] Dedicated IAM user created (e.g., nexus14-image-uploader)
- [ ] IAM policy attached with S3 permissions only:
  - s3:PutObject
  - s3:GetObject
  - s3:PutObjectAcl
  - s3:DeleteObject (optional)
- [ ] Access key credentials match AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY secrets

### 7.3 Test
- [ ] Upload test image via AWS CLI or API
- [ ] Verify image is publicly accessible via URL
- [ ] Confirm URL format: https://bucket-name.s3.amazonaws.com/filename.jpg

---

## SECTION 8: SendGrid Setup (Email Reports)

### 8.1 Account Configuration
- [ ] SendGrid account active
- [ ] API key matches SENDGRID_API_KEY secret
- [ ] Sender identity verified (domain or single email)
- [ ] EMAIL_RECIPIENT is a verified email address

### 8.2 Test
- [ ] Send test email via SendGrid dashboard
- [ ] Verify email delivery and formatting

---

## SECTION 9: Pre-Production Validation Run

### 9.1 Syntax Validation
- [ ] Navigate to: Actions > NEXUS-14 V3 — Quality-First Production
- [ ] Verify workflow appears without red X (syntax error indicator)
- [ ] Click "Run workflow" — verify all fields appear correctly

### 9.2 First Test Run
- [ ] Run with mode: end_to_end_test
- [ ] Set topic: "How to Open a Bank Account as an Immigrant in the USA"
- [ ] Set max_articles: 1
- [ ] Monitor each step — all steps must turn green
- [ ] Verify: WordPress draft created with a real Post ID
- [ ] Verify: Images generated and uploaded to S3
- [ ] Verify: Quality gate passes all 18 gates
- [ ] Check artifact: quality_gate_result.json shows "status": "READY_TO_PUBLISH"
- [ ] Check artifact: image_quality_report.json shows "overall_passed": true

### 9.3 WordPress Draft Inspection
- [ ] Log in to WordPress Admin
- [ ] Navigate to Posts > Drafts
- [ ] Find the draft created by the test run
- [ ] Verify: Featured image is set
- [ ] Verify: Rank Math SEO fields are populated (title, description, focus keyword)
- [ ] Verify: Author is assigned
- [ ] Verify: Word count >= 3500 (STANDARD) or >= 7000 (PILLAR)

---

## SECTION 10: Go-Live Authorization

### 10.1 Final Checks
- [ ] All 9 previous sections completed
- [ ] Test run produced a high-quality WordPress draft
- [ ] Quality gate result shows READY_TO_PUBLISH
- [ ] No unexpected API errors in workflow logs
- [ ] First draft manually reviewed and approved by editor

### 10.2 Schedule Activation
The workflow is already scheduled. It will trigger automatically once secrets are in place:
- Batch 1: Daily at 06:00 UTC (max 3 articles)
- Batch 2: Daily at 13:00 UTC (max 3 articles)
- Max production: 6 articles/day

### 10.3 Monitoring Setup
- [ ] Watch Actions tab for first scheduled run
- [ ] Set up email notifications for workflow failures (GitHub > Settings > Notifications)
- [ ] Review daily executive report from Agent 14 in email

---

## EMERGENCY STOP

To stop all production immediately:
1. Go to: Settings > Actions
2. Disable "NEXUS-14 V3 — Quality-First Production" workflow
3. Or: Delete the schedule cron entries from .github/workflows/production_v2.yml

---

*NEXUS-14 V3 — Production Deployment Checklist | MoneyAbroadGuide.com | 2026-06-12*
