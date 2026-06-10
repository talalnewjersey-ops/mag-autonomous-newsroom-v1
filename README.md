# 🤖 NEXUS-14 — MoneyAbroadGuide Autonomous Newsroom V1

> **The most advanced AI-powered autonomous newsroom for financial expatriate content.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![14 Agents](https://img.shields.io/badge/agents-14-green.svg)](#14-agents)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-orange.svg)](https://github.com/features/actions)

---

## 🎯 SYSTEM OVERVIEW

**NEXUS-14** is a fully autonomous, multi-agent AI newsroom built for MoneyAbroadGuide.com.
It automates the entire content pipeline from SEO research to WordPress publishing
using 14 specialized AI agents orchestrated by a Production Director.

### Key Capabilities
- 🔍 **SEO Research**: USA & Canada markets, keyword validation, affiliate & ebook opportunities
- ✍️ **Content Production**: 5,000–10,000 word articles with SEO 2026 + EEAT standards
- ✅ **Quality Control**: Automated fact-checking, EEAT validation, QA audits
- 🖼️ **Image Generation**: Featured images, infographics via Gemini/NanoBanana
- 📡 **WordPress Integration**: Automated draft creation, image upload, author/bio
- 📊 **Daily Reporting**: Morning & Executive reports via email
- 🔁 **Error Recovery**: Automatic workflow retry and self-healing pipelines

---

## 🏗️ ARCHITECTURE

```
NEXUS-14 System Architecture
=======================================================

[Production Director Agent 14] Supervise Monitor Recover Report
          |
[Chief Editor Agent 13] Audit 09:30 + 16:30
          |
+---------+---------+
|         |         |
RESEARCH  PRODUCTION  QUALITY
Agent 01  Agent 04    Agent 12
Agent 02  Agent 05
Agent 03  Agent 06
          Agent 07
          Agent 08

MEDIA
Agent 09
Agent 10
Agent 11
```

---

## 🤖 14 AGENTS

### AGENT 01 — SEO Research Agent
- **Output**: topics.json
- **Responsibilities**: SEO USA, SEO Canada, keyword opportunities, affiliate & ebook opportunities

### AGENT 02 — Keyword Validation Agent
- **Output**: validated_topics.json
- **Responsibilities**: Eliminate duplicates, verify user intent, prioritize subjects

### AGENT 03 — Content Planner Agent
- **Output**: article_outline.json
- **Responsibilities**: H2/H3 structure, FAQ generation, tables, case studies

### AGENT 04 — Article Writer Agent
- **Output**: article_draft.md
- **Responsibilities**: 5,000–10,000 words, SEO 2026, EEAT, Human-first

### AGENT 05 — Fact Checker Agent
- **Output**: fact_check_report.json
- **Responsibilities**: Verify facts, numbers, official links

### AGENT 06 — EEAT Validator Agent
- **Output**: eeat_report.json
- **Responsibilities**: Experience, Expertise, Authority, Trust scoring

### AGENT 07 — Internal Linking Agent
- **Output**: internal_links.json
- **Responsibilities**: Internal links, USA hubs, Canada hubs, related articles

### AGENT 08 — Affiliate Optimization Agent
- **Output**: affiliate_report.json
- **Responsibilities**: Detect affiliate opportunities, integrate recommended blocks

### AGENT 09 — Image Prompt Generator Agent
- **Output**: image_prompts.json
- **Responsibilities**: Featured image, secondary images, infographics, visual tables
- **Compatibility**: Gemini, NanoBanana

### AGENT 10 — Image Production Agent
- **Output**: generated_images/
- **Responsibilities**: Real image generation, error handling, quality verification

### AGENT 11 — WordPress Integration Agent
- **Output**: wordpress_report.json
- **Responsibilities**: Draft creation, image upload, FAQ insertion, author/bio insertion

### AGENT 12 — Quality Assurance Agent
- **Output**: qa_report.json
- **Responsibilities**: SEO, EEAT, FAQ, images, links, responsive checks

### AGENT 13 — Chief Editor Agent
- **Output**: editor_report.json
- **Decisions**: READY_TO_PUBLISH / NEEDS_CORRECTION / REJECTED
- **Schedule**: 09:30 (Batch 1) + 16:30 (Batch 2)

### AGENT 14 — Production Director Agent
- **Output**: daily_production_report.html
- **Responsibilities**: Supervise all agents, detect errors, retry failed workflows, email reports

---

## ⏰ SCHEDULING

| Time | Action |
|------|--------|
| 06:00 | 🚀 Production launch |
| 09:30 | 🔍 Global Audit #1 |
| 09:45 | 📧 Morning Report → talalnewjersey@gmail.com |
| 10:00 | ✅ Batch #1 READY |
| 10:00–15:30 | 🔄 Second production cycle |
| 16:30 | 🔍 Global Audit #2 |
| 18:00 | ✅ Batch #2 READY |
| 18:30 | 📊 Executive Daily Report → talalnewjersey@gmail.com |

---

## ✅ QUALITY RULES

An article NEVER receives READY_TO_PUBLISH if:

| Rule | Threshold |
|------|-----------|
| Word count | < 5,000 words |
| Images | < 4 images |
| Featured image | Absent |
| FAQ section | Absent |
| Author field | Absent |
| Author bio | Absent |
| SEO score | < 95/100 |
| EEAT score | < 95/100 |
| Broken links | Any detected |

---

## 📧 EMAIL REPORTING

**Recipient**: talalnewjersey@gmail.com

**Morning Report (09:45)**: Articles produced, validated, rejected, errors, SEO scores, EEAT scores, image status, workflow state

**Executive Daily Report (18:30)**: Full daily summary, total articles published, revenue analysis, agent performance, tomorrow's queue

---

## 🚀 INSTALLATION

```bash
git clone https://github.com/talalnewjersey-ops/mag-autonomous-newsroom-v1.git
cd mag-autonomous-newsroom-v1
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

---

## ⚙️ CONFIGURATION

Create your .env file from .env.example with these keys:
- OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
- WORDPRESS_URL, WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD
- SERPAPI_KEY, SEMRUSH_API_KEY
- SENDGRID_API_KEY, EMAIL_RECIPIENT=talalnewjersey@gmail.com
- DALLE_API_KEY, NANO_BANANA_KEY
- AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET

---

## 🗺️ IMPLEMENTATION ROADMAP

### Phase 1 — Foundation (Week 1)
- [x] Repository setup (NEXUS-14)
- [ ] Core infrastructure (config, logging, storage)
- [ ] Services layer
- [ ] Base agent class

### Phase 2 — Research Layer (Week 2)
- [ ] Agent 01: SEO Research
- [ ] Agent 02: Keyword Validation
- [ ] Agent 03: Content Planner

### Phase 3 — Production Layer (Week 3)
- [ ] Agent 04: Article Writer
- [ ] Agent 05: Fact Checker
- [ ] Agent 06: EEAT Validator
- [ ] Agent 07: Internal Linking
- [ ] Agent 08: Affiliate Optimizer

### Phase 4 — Media Layer (Week 4)
- [ ] Agent 09: Image Prompt Generator
- [ ] Agent 10: Image Production
- [ ] Agent 11: WordPress Integration

### Phase 5 — Quality & Orchestration (Week 5)
- [ ] Agent 12: Quality Assurance
- [ ] Agent 13: Chief Editor
- [ ] Agent 14: Production Director
- [ ] Orchestrator + Workflow Manager

### Phase 6 — Automation & Monitoring (Week 6)
- [ ] GitHub Actions workflows
- [ ] Cron scheduling
- [ ] Health monitoring
- [ ] Email reporting
- [ ] Full integration testing

---

## 🏆 PROJECT CODE NAME: **NEXUS-14**

*Fourteen agents. One mission. Dominate expatriate financial content.*

---

*Built for MoneyAbroadGuide.com | Powered by AI | Version 1.0.0*
