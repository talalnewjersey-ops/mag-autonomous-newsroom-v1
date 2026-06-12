# 🤖 NEXUS-14 V2 — MoneyAbroadGuide Quality-First Autonomous Newsroom

> **QUALITY ALWAYS WINS OVER VOLUME.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![16 Agents](https://img.shields.io/badge/agents-16-green.svg)](#16-agents)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-orange.svg)](https://github.com/features/actions)
[![Version 2.0](https://img.shields.io/badge/version-2.0.0-purple.svg)](#)

---

## 🎯 SYSTEM OVERVIEW

**NEXUS-14 V2** is a fully autonomous, 16-agent AI newsroom built for MoneyAbroadGuide.com.

**Mission:** Publish fewer articles, but ensure every article is publication-ready, EEAT-compliant, fact-checked, visually rich, and capable of ranking on Google.

### What Changed from V1?

| Metric | V1 | V2 |
|--------|----|----|
| Daily articles | 20+ (volume target) | Max 6 (quality enforced) |
| Quality gates | Basic | 15 mandatory gates |
| Agents | 14 | 16 (+ Agent 15 + Agent 16) |
| Publication on fail | Sometimes | NEVER |
| Primary AI | Multiple | Claude API (primary) |

---

## 📅 PRODUCTION SCHEDULE

| Time (UTC) | Action |
|------------|--------|
| 06:00 | 🚀 Batch 1 Production Start — Max 3 articles |
| 09:30 | 🔍 Global Quality Audit #1 (Agent 13) |
| 09:45 | 📧 Morning Production Report (Agent 14) |
| 13:00 | 🚀 Batch 2 Production Start — Max 3 articles |
| 16:30 | 🔍 Global Quality Audit #2 (Agent 13) |
| 18:00 | 📊 Evening Production Report |
| 18:30 | 📊 Executive Daily Report (Agent 14) |

**Maximum daily production: 6 articles**

---

## 🏗️ ARCHITECTURE (V2 — 16 Agents)

```
[Production Director Agent 14] — Supervise | Monitor | Recover | Report
     |
[Chief Editor Agent 13] — Audit 09:30 + 16:30
     |
+----+----+----+----+----+
|         |         |         |         |
RESEARCH  PRODUCTION QUALITY   MEDIA     NEW V2
Agent 01  Agent 04  Agent 12  Agent 09  Agent 15
Agent 02  Agent 05  Agent 06  Agent 10  Agent 16
Agent 03  Agent 07
          Agent 08
          Agent 11
```

---

## 🤖 16 AGENTS

### Research Layer
- **AGENT 01** — SEO Research Agent | Output: `topics.json`
- **AGENT 02** — Keyword Validation Agent | Output: `validated_topics.json`
- **AGENT 03** — Content Planner Agent | Output: `article_outline.json`

### Production Layer
- **AGENT 04** — Article Writer Agent (Anthropic Claude API — Primary) | Output: `article_draft.md`
- **AGENT 05** — Fact Checker Agent | Output: `fact_check_report.json`
- **AGENT 06** — EEAT Validator Agent | Output: `eeat_report.json`
- **AGENT 07** — Internal Linking Agent | Output: `internal_links.json`
- **AGENT 08** — Affiliate Optimization Agent | Output: `affiliate_report.json`

### Media Layer
- **AGENT 09** — Image Prompt Generator Agent | Output: `image_prompts.json`
- **AGENT 10** — Image Production Agent (Gemini AI + Nano Banana) | Output: `image_validation_report.json`
- **AGENT 11** — WordPress Integration Agent | Output: `wordpress_validation_report.json`

### Quality Layer
- **AGENT 12** — Quality Assurance Agent | Output: `qa_report.json`
- **AGENT 13** — Chief Editor Agent | Decisions: READY_TO_PUBLISH / NEEDS_CORRECTION / REJECTED
- **AGENT 14** — Production Director Agent | Output: `daily_production_report.html`

### NEW in V2
- **AGENT 15** — Affiliate Compliance Agent | Output: `affiliate_compliance.json`
  - FTC disclosure verification
  - Partner disclosure validation
  - Prohibited language check
  - Affiliate block validation

- **AGENT 16** — Publishing Optimization Agent | Output: `publishing_optimizer.json`
  - Meta title generation (50-60 chars)
  - Meta description generation (150-160 chars)
  - JSON-LD Schema (Article + FAQ + BreadcrumbList)
  - Open Graph optimization
  - Twitter Card optimization
  - Rank Math field completion

---

## ✅ CONTENT REQUIREMENTS (V2)

Each article must contain:

| Requirement | Minimum |
|-------------|---------|
| Word Count | 5,000 (target: 6,000–9,000) |
| FAQ Questions | 20 |
| Internal Links | 5 |
| Authoritative Sources | 10 |
| Real-World Case Studies | 3 |
| Ebook Opportunities | 2 |
| Affiliate Opportunities | 2 |
| Comparison Tables | 1 |
| Checklist Sections | 1 |
| Step-by-Step Action Plans | 1 |
| Expert Recommendation Sections | 1 |
| Newcomer Mistakes Sections | 1 |

### Image Requirements

| Type | Count |
|------|-------|
| Featured Image | 1 |
| Professional Infographic | 1 |
| Visual Comparison Graphic | 1 |
| Checklist Graphic | 1 |
| Educational Diagram | 1 |
| **Minimum Total** | **5** |
| Pillar Articles | 6–8 |

---

## 🛡️ QUALITY GATES (15 Mandatory — All Must Pass)

```
READY_TO_PUBLISH only if ALL 15 gates pass:

Gate 01: Word Count ≥ 5,000
Gate 02: Images ≥ 5 (zero upload errors)
Gate 03: Featured Image Present
Gate 04: FAQ ≥ 20 questions
Gate 05: Internal Links ≥ 5
Gate 06: Authoritative Sources ≥ 10
Gate 07: Case Studies ≥ 3
Gate 08: Author Assigned
Gate 09: Author Bio Inserted
Gate 10: SEO Score ≥ 90/100
Gate 11: EEAT Score ≥ 90/100
Gate 12: Affiliate Compliance PASS (Agent 15)
Gate 13: Publishing Optimization PASS (Agent 16)
Gate 14: Broken Links = 0
Gate 15: WordPress Draft Exists (with Post ID)

If ANY gate fails:
  ❌ DO NOT PUBLISH
  ❌ DO NOT CREATE DRAFT
  ❌ DO NOT REPORT SUCCESS
  ✅ Explain what failed, why, and how to fix
```

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

**Minimum: 10 authoritative sources per article**

---

## 🖥️ WORDPRESS REQUIREMENTS

Auto-inserted by Agent 11 + Agent 16:
- Author: **Talal Eddaouahiri**
- Author Bio: Founder of MoneyAbroadGuide.com...
- Author Image
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
ANTHROPIC_API_KEY=         # Primary writing engine
GEMINI_API_KEY=            # Image generation
NANO_BANANA_KEY=           # Image generation
WORDPRESS_URL=             # Your WP site
WORDPRESS_USERNAME=
WORDPRESS_APP_PASSWORD=
SERPAPI_KEY=               # SEO research
SEMRUSH_API_KEY=           # Keyword data
SENDGRID_API_KEY=          # Email reports
EMAIL_RECIPIENT=talalnewjersey@gmail.com
AWS_ACCESS_KEY_ID=         # S3 image storage
AWS_SECRET_ACCESS_KEY=
S3_BUCKET=
```

### V2 Config: `config/nexus14_v2_config.yaml`

Full V2 configuration including production strategy, quality gates, and agent settings.

---

## 🔄 GITHUB ACTIONS WORKFLOWS

| Workflow | Purpose |
|----------|---------|
| `production_v2.yml` | ⭐ V2 main workflow (quality-first, 6/day max) |
| `production.yml` | V1 legacy (retained for reference) |
| `test_single_article.yml` | Single article testing |
| `wp_diagnostic.yml` | WordPress connectivity check |

**Use `production_v2.yml` for all V2 operations.**

---

## 📋 REAL EXECUTION POLICY

> **CRITICAL:** Success is NEVER declared based on assumptions, code written, or workflow configured.

**Success must be proven through real execution:**

### Required Deliverables for Operational Status
1. ✅ Real WordPress Draft URL
2. ✅ Real WordPress Post ID
3. ✅ Real Generated Image URLs (from Gemini/NanoBanana)
4. ✅ Real QA Report (`qa_report.json`)
5. ✅ Real Image Validation Report (`image_validation_report.json`)
6. ✅ Real WordPress Validation Report (`wordpress_validation_report.json`)
7. ✅ Real Affiliate Compliance Report (`affiliate_compliance.json`)
8. ✅ Real Publishing Optimizer Report (`publishing_optimizer.json`)
9. ✅ Real End-to-End Test Report (`end_to_end_test_report.html`)

---

## 📧 EMAIL REPORTING

Recipient: talalnewjersey@gmail.com

**Morning Report (09:45 UTC):** Articles produced, validated, rejected, errors, SEO/EEAT scores, image status, workflow state

**Executive Daily Report (18:30 UTC):** Full daily summary, total articles published, revenue analysis, agent performance, tomorrow's queue

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
│   ├── agent_15_affiliate_compliance.py  ★ NEW V2
│   ├── agent_16_publishing_optimization.py  ★ NEW V2
│   └── base_agent.py
├── .github/workflows/
│   ├── production_v2.yml  ★ NEW V2 (primary)
│   ├── production.yml
│   └── test_single_article.yml
├── config/
│   ├── config.yaml
│   └── nexus14_v2_config.yaml  ★ NEW V2
├── docs/
│   └── MIGRATION_REPORT_V2.md  ★ NEW V2
├── scripts/
│   ├── v2_quality_gate.py  ★ NEW V2
│   └── produce_article.py
├── services/
├── orchestrator/
├── monitoring/
├── .env.example
└── README.md
```

---

## 🏆 PROJECT CODE NAME: NEXUS-14 V2

Sixteen agents. One mission. **Publish only what deserves to rank.**

Built for MoneyAbroadGuide.com | Powered by Anthropic Claude API | Version 2.0.0

> *Migration completed June 12, 2026. See [docs/MIGRATION_REPORT_V2.md](docs/MIGRATION_REPORT_V2.md) for full details.*
