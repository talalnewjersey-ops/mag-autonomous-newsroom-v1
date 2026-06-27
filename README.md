# 🤖 NEXUS-14 V3/V4 — MoneyAbroadGuide Quality-First Autonomous Newsroom

> **QUALITY ALWAYS WINS OVER VOLUME.**

## 🎯 SYSTEM OVERVIEW

NEXUS-14 V3 is a fully autonomous, **18-agent AI newsroom** built for [MoneyAbroadGuide.com](https://moneyabroadguide.com).

**Platform:** Financial education for immigrants, newcomers, international students, and expats in the USA and Canada.

**Mission:** Publish fewer articles, but ensure every article is publication-ready, EEAT-compliant, fact-checked, visually rich, revenue-optimized, and capable of ranking on Google.

**Primary Goals:** Google rankings · EEAT compliance · Affiliate revenue · Ebook sales · AdSense approval · Long-term topical authority

### What Changed from V2?

| Metric | V2 | V3 |
|--------|----|----|
| Agents | 16 | **18** (+Agent 17 + Agent 18) |
| Quality gates | 15 | **18** (+Gates 16, 17, 18) |
| Article types | One-size-fits-all | **STANDARD + PILLAR** (two-tier) |
| Word count min | 5,000 | **3,500** (STANDARD) / **7,000** (PILLAR) |
| FAQ min | 20 | **8–12** (STANDARD) / **15–20** (PILLAR) |
| Sources min | 10 | **5** (STANDARD) / **10** (PILLAR) |
| Cannibalization check | None | **Agent 17 — MANDATORY** |
| Revenue scoring | None | **Agent 18 — Score ≥ 60 required** |
| Image validation | Basic | **Enhanced — 10 quality checks** |
| Daily max | 6 | **6** (unchanged) |

---

## 📅 PRODUCTION SCHEDULE

| Time (UTC) | Action |
|-----------|--------|
| 06:00 | 🚀 Batch 1 Production Start — Max 3 articles |
| 09:30 | 🔍 Global Quality Audit #1 (Agent 13) |
| 09:45 | 📧 Morning Production Report (Agent 14) |
| 13:00 | 🚀 Batch 2 Production Start — Max 3 articles |
| 16:30 | 🔍 Global Quality Audit #2 (Agent 13) |
| 18:00 | 📊 Evening Production Report |
| 18:30 | 📊 Executive Daily Report (Agent 14) |

**Maximum daily production: 6 articles**

---

## 🏗️ ARCHITECTURE (V3 — 18 Agents)

```
[Production Director Agent 14] — Supervise | Monitor | Recover | Report
                    |
         [Chief Editor Agent 13] — Audit 09:30 + 16:30
                    |
    +-------+-------+-------+-------+-------+
    |       |       |       |       |       |
PRE-PROD  RESEARCH PRODUCTION QUALITY  MEDIA
Ag 17    Ag 01    Ag 04    Ag 12   Ag 09
Ag 18    Ag 02    Ag 05    Ag 06   Ag 10
         Ag 03    Ag 07    Ag 15   Ag 11
                  Ag 08    Ag 16
```

---

## 🤖 18 AGENTS

### Pre-Production Layer (**NEW in V3**)

| Agent | Name | Output |
|-------|------|--------|
| **AGENT 17** ⭐ | Content Cannibalization Agent | `cannibalization_report.json` |
| **AGENT 18** ⭐ | Revenue Intelligence Agent | `revenue_score.json` |

### Research Layer
| Agent | Name | Output |
|-------|------|--------|
| AGENT 01 | SEO Research Agent | `topics.json` |
| AGENT 02 | Keyword Validation Agent | `validated_topics.json` |
| AGENT 03 | Content Planner Agent + Article Classifier | `article_outline.json` |

### Production Layer
| Agent | Name | Output |
|-------|------|--------|
| AGENT 04 | Article Writer Agent (Anthropic Claude API) | `article_draft.md` |
| AGENT 05 | Fact Checker Agent | `fact_check_report.json` |
| AGENT 06 | EEAT Validator Agent | `eeat_report.json` |
| AGENT 07 | Internal Linking Agent | `internal_links.json` |
| AGENT 08 | Affiliate Optimization Agent | `affiliate_report.json` |

### Media Layer
| Agent | Name | Output |
|-------|------|--------|
| AGENT 09 | Image Prompt Generator Agent | `image_prompts.json` |
| AGENT 10 | Image Production Agent (Gemini AI + Nano Banana) ⭐ Enhanced | `image_quality_report.json` |
| AGENT 11 | WordPress Integration Agent | `wordpress_validation_report.json` |

### Quality Layer
| Agent | Name | Output |
|-------|------|--------|
| AGENT 12 | Quality Assurance Agent | `qa_report.json` |
| AGENT 13 | Chief Editor Agent | READY_TO_PUBLISH / NEEDS_CORRECTION / REJECTED |
| AGENT 14 | Production Director Agent | `daily_production_report.html` |
| AGENT 15 | Affiliate Compliance Agent | `affiliate_compliance.json` |
| AGENT 16 | Publishing Optimization Agent | `publishing_optimizer.json` |

---

## ✅ CONTENT REQUIREMENTS (V3 — Two-Tier System)

### STANDARD ARTICLE

| Requirement | Threshold |
|-------------|-----------|
| Word Count | **3,500 min** (target: 4,500–7,000) |
| FAQ Questions | **8–12** |
| Authoritative Sources | **5 minimum** |
| Internal Links | 5 |
| Images | 5 |

### PILLAR ARTICLE

| Requirement | Threshold |
|-------------|-----------|
| Word Count | **7,000 min** (target: 7,000–10,000) |
| FAQ Questions | **15–20** |
| Authoritative Sources | **10 minimum** |
| Internal Links | 8 |
| Images | 6–8 |

### Article Classification Logic

```
IF keyword_difficulty > 50 OR strategic_topic == true:
    article_type = PILLAR
ELIF search_volume > 5000:
    article_type = PILLAR
ELIF revenue_score > 85:
    article_type = PILLAR
ELSE:
    article_type = STANDARD
```

Classification stored in: `config/article_strategy.json`

---

## 🛡️ QUALITY GATES (18 Mandatory — All Must Pass)

`READY_TO_PUBLISH` only if ALL 18 gates pass:

| Gate | Check | Threshold |
|------|-------|-----------|
| Gate 01 | Word Count | ≥ 3,500 (STANDARD) / ≥ 7,000 (PILLAR) |
| Gate 02 | Images | ≥ 5 (zero upload errors) |
| Gate 03 | Featured Image | Present |
| Gate 04 | FAQ | ≥ 8 (STANDARD) / ≥ 15 (PILLAR) |
| Gate 05 | Internal Links | ≥ 5 |
| Gate 06 | Authoritative Sources | ≥ 5 (STANDARD) / ≥ 10 (PILLAR) |
| Gate 07 | Case Studies | ≥ 2 |
| Gate 08 | Author Assigned | Required |
| Gate 09 | Author Bio Inserted | Required |
| Gate 10 | SEO Score | ≥ 90/100 |
| Gate 11 | EEAT Score | ≥ 90/100 |
| Gate 12 | Affiliate Compliance | PASS (Agent 15) |
| Gate 13 | Publishing Optimization | PASS (Agent 16) |
| Gate 14 | Broken Links | = 0 |
| Gate 15 | WordPress Draft | Exists (with Post ID) |
| **Gate 16** ⭐ | **Cannibalization** | **PASS (Agent 17) — NEW V3** |
| **Gate 17** ⭐ | **Revenue Score** | **≥ 60 (Agent 18) — NEW V3** |
| **Gate 18** ⭐ | **Image Quality** | **PASS (Agent 10 enhanced) — NEW V3** |

> If ANY gate fails: ❌ DO NOT PUBLISH · ❌ DO NOT REPORT SUCCESS · ✅ Explain what failed and how to fix it

---

## 🔍 AGENT 17 — CONTENT CANNIBALIZATION AGENT *(NEW V3)*

**Mission:** Before any article creation, scan all existing WordPress articles, drafts, and internal topic databases to prevent duplicate content.

**Decisions:**

| Decision | Meaning |
|----------|---------|
| `CREATE_NEW_ARTICLE` | Topic is genuinely new — proceed to Agent 04 |
| `UPDATE_EXISTING_ARTICLE` | Existing article found — update instead |
| `MERGE_WITH_EXISTING` | Partial overlap — merge recommended |
| `REJECT_DUPLICATE` | Near-identical topic — blocked |

**Rules:** Duplicate topics are NEVER produced. Agent 17 runs BEFORE Agent 04.

Output: `cannibalization_report.json`

---

## 💰 AGENT 18 — REVENUE INTELLIGENCE AGENT *(NEW V3)*

**Mission:** Score every topic 0–100 for revenue potential before production.

**Evaluates:** Affiliate opportunities · Ebook opportunities · AdSense potential · Internal linking · Search intent · Commercial intent

**Revenue Score Rules:**

| Score | Decision |
|-------|----------|
| < 60 | ❌ REJECT TOPIC |
| 60–70 | ⚠️ OPTIONAL |
| 70–85 | ✅ PRIORITIZE |
| > 85 | 🔥 HIGH PRIORITY QUEUE |

Output: `revenue_score.json`

---

## 🖼️ IMAGE QUALITY SYSTEM (Agent 10 — Enhanced V3)

Agent 10 now validates:

- ✅ Resolution (minimum 800×600)
- ✅ Readability
- ✅ Branding consistency
- ✅ Financial accuracy
- ✅ No AI artifacts
- ✅ Mobile readability

Publishing is blocked if image quality fails (Gate 18).

Output: `image_quality_report.json`

---

## 📊 FACT-CHECKING REQUIREMENTS

Agent 05 verifies claims from:

- IRS (irs.gov)
- CRA (canada.ca/cra)
- USCIS (uscis.gov)
- FDIC (fdic.gov)
- CFPB (consumerfinance.gov)
- Canada.ca
- Official financial institutions

Minimum: **5 sources** (STANDARD) / **10 sources** (PILLAR)

---

## 🖥️ WORDPRESS REQUIREMENTS

Auto-inserted by Agent 11 + Agent 16:

- Author: Talal Eddaouahiri
- Author Bio + Image
- Featured Image (uploaded to S3 + WordPress)
- All generated visuals
- FAQ Schema (JSON-LD)
- Internal Links
- Affiliate Blocks (FTC-compliant)
- Ebook CTA Blocks
- Rank Math Metadata
- Meta Title + Description
- Open Graph + Twitter Card tags

---

## 🚀 INSTALLATION

```bash
git clone https://github.com/talalnewjersey-ops/mag-autonomous-newsroom-v1.git
cd mag-autonomous-newsroom-v1
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python main.py
```

---

## ⚙️ CONFIGURATION

### Environment Variables (.env)

```
ANTHROPIC_API_KEY=      # Primary writing engine
GEMINI_API_KEY=         # Image generation
NANO_BANANA_KEY=        # Image generation
WORDPRESS_URL=          # Your WP site
WORDPRESS_USERNAME=
WORDPRESS_APP_PASSWORD=
SERPAPI_KEY=            # SEO research
SEMRUSH_API_KEY=        # Keyword data
SENDGRID_API_KEY=       # Email reports
EMAIL_RECIPIENT=talalnewjersey@gmail.com
AWS_ACCESS_KEY_ID=      # S3 image storage
AWS_SECRET_ACCESS_KEY=
S3_BUCKET=
```

**V3 Config:** `config/nexus14_v2_config.yaml` (updated to V3)
**Article Strategy:** `config/article_strategy.json` (NEW V3)

---

## 🔄 GITHUB ACTIONS WORKFLOWS

| Workflow | Purpose |
|----------|---------|
| `production_v2.yml` | ⭐ **V4.0 ACTIVE PIPELINE** — Reliability-First, 6/day max |
| `production.yml` | V1 legacy — archived, schedule trigger removed (see commit 16ae5b5) |
| `test_single_article.yml` | Single article manual testing |
| `wp_diagnostic.yml` | WordPress connectivity diagnostics |
| `produce_20_articles.yml` | Bulk 20-article production (manual dispatch) |
| `nexus14-enterprise-enforcement.yml` | Enterprise standard validation on push/PR |
| `nexus14-agent-init-validation.yml` | Agent initialization smoke tests |
| `backfill_images.yml` | Backfill images on existing WordPress posts (dry-run default) |
| `patch_images.yml` | Patch images on draft posts |
| `draft_image_report.yml` | Image report for draft posts |
| `social_video_pipeline.yml` | TikTok/Short-form social video pipeline |

---

## 📋 REAL EXECUTION POLICY

**CRITICAL:** Success is NEVER declared based on assumptions or code written.

Success must be proven through real execution. **Required Deliverables for Operational Status:**

- ✅ Real WordPress Draft URL
- ✅ Real WordPress Post ID
- ✅ Real Featured Image URL
- ✅ Real Uploaded Images URLs
- ✅ QA Report (`qa_report.json`)
- ✅ Image Validation Report (`image_validation_report.json`)
- ✅ **Image Quality Report (`image_quality_report.json`) — NEW V3**
- ✅ **Cannibalization Report (`cannibalization_report.json`) — NEW V3**
- ✅ **Revenue Report (`revenue_score.json`) — NEW V3**
- ✅ Affiliate Compliance Report (`affiliate_compliance.json`)
- ✅ Publishing Optimization Report (`publishing_optimizer.json`)
- ✅ End-to-End Test Report (`end_to_end_test_report.html`)

If any item is missing: **STATUS = FAILED. Never report success.**

---

## 📧 EMAIL REPORTING

**Recipient:** talalnewjersey@gmail.com

**Morning Report (09:45 UTC):** Articles created/rejected, rejection reasons, revenue scores, cannibalization decisions, SEO/EEAT scores, image quality scores, workflow state

**Executive Daily Report (18:30 UTC):** Full daily summary, articles published, revenue analysis, cannibalization decisions, SEO/EEAT scores, affiliate opportunities, ebook opportunities, internal linking opportunities, agent performance, tomorrow's queue

---

## 📁 REPOSITORY STRUCTURE

```
mag-autonomous-newsroom-v1/
├── agents/
│   ├── agent_01_seo_research.py
│   ├── agent_02_keyword_validation.py
│   ├── agent_03_content_planner.py
│   ├── agent_04_article_writer.py
│   ├── agent_05_fact_checker.py
│   ├── agent_06_eeat_validator.py
│   ├── agent_07_internal_linking.py
│   ├── agent_08_affiliate_optimizer.py
│   ├── agent_09_image_prompt_generator.py
│   ├── agent_10_image_production.py
│   ├── agent_11_wordpress_integration.py
│   ├── agent_12_quality_assurance.py
│   ├── agent_13_chief_editor.py
│   ├── agent_14_production_director.py
│   ├── agent_15_affiliate_compliance.py   ★ Added V2
│   ├── agent_16_publishing_optimization.py ★ Added V2
│   ├── agent_17_cannibalization.py        ★ NEW V3
│   ├── agent_18_revenue_intelligence.py   ★ NEW V3
│   └── base_agent.py
├── .github/workflows/
│   ├── production_v2.yml ★ Primary workflow (V3)
│   ├── production.yml
│   └── test_single_article.yml
├── config/
│   ├── config.yaml
│   ├── nexus14_v2_config.yaml   ★ Upgraded to V3
│   └── article_strategy.json   ★ NEW V3 — Classification rules
├── docs/
│   ├── MIGRATION_REPORT_V2.md
│   └── MIGRATION_REPORT_V3.md  ★ NEW V3
├── scripts/
│   ├── v2_quality_gate.py   ★ Upgraded to V3 (18 gates)
│   └── produce_article.py
├── services/
├── orchestrator/
├── monitoring/
├── .env.example
└── README.md
```

---

## 🏆 PROJECT CODE NAME: NEXUS-14 V3

Eighteen agents. One mission. Publish only what deserves to rank.

**Built for MoneyAbroadGuide.com** | Powered by Anthropic Claude API | **Version 3.0.0**

Migration completed June 12, 2026. See `docs/MIGRATION_REPORT_V3.md` for full details.
