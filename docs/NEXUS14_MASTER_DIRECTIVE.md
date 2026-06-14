# NEXUS-14 MASTER PRODUCTION DIRECTIVE
## MoneyAbroadGuide.com — Official Global Production Standard

**Version:** 2026  
**Status:** ACTIVE — Integrated into NEXUS-14 V3 Workflow  
**Date Added:** 2026-06-14  
**References:** MONEYABROADGUIDE_ENTERPRISE_STANDARD.md, NEXUS-14-ENTERPRISE-v3.md, nexus14_v2_config.yaml, production_v2.yml

---

## 1. CORE PHILOSOPHY

**QUALITY ALWAYS WINS OVER VOLUME.**

MoneyAbroadGuide is a premium financial education platform for newcomers to the USA and Canada, immigrants, expats, international students, non-residents, and cross-border families.

Every article must be capable of ranking on Google, meeting EEAT standards, being approved by AdSense, and supporting affiliate, banking, insurance, and tax-service partnerships while building long-term domain authority.

**Quality benchmark:** https://moneyabroadguide.com/best-way-to-send-money-usa-to-canada-2026/

---

## 2. DAILY PRODUCTION MODEL

| Parameter | Value |
|---|---|
| Maximum articles per day | 6 |
| Batch 1 (morning) | Max 3 articles — 06:00 UTC |
| Batch 2 (afternoon) | Max 3 articles — 13:00 UTC |
| Quality drop policy | Reduce volume automatically |

Never exceed 6 articles per day. Quality has absolute priority.

---

## 3. ARTICLE LENGTH

| Type | Minimum | Target |
|---|---|---|
| STANDARD | 3,500 words | 4,500–7,000 words |
| PILLAR | 7,000 words | 7,000–10,000 words |
| Enterprise Gold | 8,500 words | 10,000–12,000 words |

---

## 4. MANDATORY CONTENT ELEMENTS

Every article must contain — no exceptions:

- Strong introduction (problem + opportunity + outcome + CTA)
- Key Takeaways / Quick Answer Box
- Comparison tables
- Pros and Cons table
- Checklist table
- Timeline table (where applicable)
- Expert Tip boxes
- Warning boxes
- Common Mistake boxes
- Real examples with real numbers
- Minimum 2 case studies (STANDARD) / 6 case studies (PILLAR/Gold)
- FAQ section (8–12 STANDARD / 15–20 PILLAR / 20+ Gold)
- FAQ Schema (JSON-LD)
- Internal links (min 5 STANDARD / min 15 PILLAR/Gold)
- External authority links (min 5 STANDARD / min 10 PILLAR)
- Natural CTA placement (ebook + affiliate + service)
- Author bio with credentials
- Compliance / disclaimer section
- Sources section (government + primary sources only)

---

## 5. CONTENT VALIDATION GATE (Post Agent 04 — Pre Agent 11)

This mandatory gate runs immediately after Agent 04 (Article Writer) and before Agent 11 (WordPress Publisher).

### 5.1 Article Cleanup (Automated)

Automatically remove: YAML blocks, frontmatter, agent metadata headers, duplicate titles, duplicate sections, AI-style filler introductions.

### 5.2 Content Requirements Check

| Metric | STANDARD | PILLAR | Gold |
|---|---|---|---|
| Word count | 3,500 min | 7,000 min | 8,500 min |
| FAQ questions | 8–12 | 15–20 | 20+ |
| Authoritative sources | 5 min | 10 min | 10 min |
| Internal links | 5 min | 8 min | 15 min |
| Case studies | 2 min | 3 min | 6 min |
| Images | 5 min | 6–8 | 6 min |

### 5.3 EEAT Validation

Automatically reject: fake experts, fictional credentials, fictional biographies, unverified statistics, unverified surveys.

Automatically require: Talal Eddaouahiri author section, MoneyAbroadGuide disclaimer, editorial review section, minimum official sources.

### 5.4 Mobile Optimization Inserts

Automatically insert: Summary Cards, Quick Answer Cards, Expert Tip boxes, Warning boxes, Checklists.

---

## 6. EEAT POLICY

| Element | Requirement |
|---|---|
| Author box | Full name, credentials, photo |
| Founder bio | MoneyAbroadGuide founder details |
| Sources section | Government + primary sources only |
| Compliance section | Legal/financial disclaimer |
| Expert recommendation | Named expert or author opinion |
| Real-world scenarios | Min 2 (STANDARD) / 6 (Gold) |
| Last reviewed date | Must be current year |

Priority sources: IRS, FinCEN, USCIS, SSA, FDIC, CFPB, FTC, HUD, CRA, .gov/.gc.ca sites.

Never invent facts, statistics, or unverifiable numbers. If information cannot be verified: remove it.

---

## 7. SEO POLICY

| Output | Standard |
|---|---|
| SEO title | Primary keyword + year + intent modifier |
| Meta description | 150–160 chars with primary keyword + CTA |
| Slug | Lowercase-hyphenated, max 60 chars |
| Primary keyword | 1 target keyword |
| Secondary keywords | 3–5 keywords |
| Semantic entities | 5–10 entities |
| Internal linking | Min 5 (STANDARD) / Min 15 (Gold) |
| Schemas | Article, FAQPage, Person, Organization, BreadcrumbList |

Avoid: keyword stuffing, AI filler, thin content, duplicate content.

---

## 8. IMAGE REQUIREMENTS (Agent 09 + Agent 10)

| # | Image Type | Dimensions | Purpose |
|---|---|---|---|
| 1 | Featured Image | 1200x628 | Hero image |
| 2 | Comparison Graphic | 16:9 | Side-by-side comparison |
| 3 | Process Graphic | 16:9 | Step-by-step infographic |
| 4 | Checklist Graphic | 16:9 | Action checklist |
| 5 | Data Visualization | 16:9 | Chart or graph |
| 6 | Topic Graphic | 16:9 | Supporting illustration |

All images must be: professional, ultra-realistic, high-trust financial education style, Forbes/Investopedia quality, no distorted text, no watermarks, no AI artifacts, mobile-readable (min 800x600).

For each image provide: prompt, alt text, caption, SEO filename, placement in article.

Agent 10 quality checks (Gate 18): resolution, readability, branding consistency, financial accuracy, no AI artifacts, mobile readability.

---

## 9. MONETIZATION POLICY

| CTA Type | Placement |
|---|---|
| Ebook CTA | After intro, mid-article, before conclusion |
| Affiliate CTA | Max 3 partners — top, middle, bottom |
| Service CTA | Natural placement |
| Comparison CTA | After comparison table |

All affiliate links: rel="nofollow sponsored" target="_blank". FTC-compliant disclosure at top. Education first — never use aggressive sales language.

---

## 10. WORDPRESS PUBLISHING POLICY

Agent 11 + Agent 16 must verify before publication:

- No broken HTML, no duplicate headings, no formatting issues
- Mobile + desktop responsive
- Clean table of contents
- Author: Talal Eddaouahiri — bio + image inserted
- All images uploaded to Media Library (+ S3 backup)
- Featured image assigned
- Categories assigned (max 2), Tags assigned (5–10)
- 5 schemas: Article, FAQPage, Person, Organization, BreadcrumbList
- Rank Math metadata, meta title + description, Open Graph + Twitter Card tags
- FTC-compliant affiliate disclosure blocks
- Ebook CTA blocks

---

## 11. QUALITY GATES (18 Mandatory — All Must Pass ≥ 9.5/10)

| Gate | Check | Threshold |
|---|---|---|
| Gate 01 | Word count | ≥ 3,500 (STANDARD) / ≥ 7,000 (PILLAR) / ≥ 8,500 (Gold) |
| Gate 02 | Images | ≥ 5 with zero upload errors |
| Gate 03 | Featured image | Present and assigned |
| Gate 04 | FAQ | ≥ 8 (STANDARD) / ≥ 15 (PILLAR) / ≥ 20 (Gold) |
| Gate 05 | Internal links | ≥ 5 (STANDARD) / ≥ 15 (Gold) |
| Gate 06 | Authoritative sources | ≥ 5 (STANDARD) / ≥ 10 (PILLAR) |
| Gate 07 | Case studies | ≥ 2 (STANDARD) / ≥ 6 (Gold) |
| Gate 08 | Author assigned | Required |
| Gate 09 | Author bio | Required |
| Gate 10 | SEO score | ≥ 95/100 |
| Gate 11 | EEAT score | ≥ 95/100 |
| Gate 12 | Affiliate compliance | PASS (Agent 15) |
| Gate 13 | Publishing optimization | PASS (Agent 16) |
| Gate 14 | Broken links | = 0 |
| Gate 15 | WordPress draft | Exists with Post ID |
| Gate 16 | Cannibalization | PASS (Agent 17) |
| Gate 17 | Revenue score | ≥ 60/100 (Agent 18) |
| Gate 18 | Image quality | PASS (Agent 10 enhanced) |

If any gate fails: return to pipeline → revise → re-audit → re-score. Do NOT publish. Do NOT report success.

---

## 12. AGENT RESPONSIBILITIES

| Agent | Name | Directive Gate |
|---|---|---|
| Agent 01 | SEO Research | Revenue ≥ 60 validated |
| Agent 02 | Keyword Validation | Intent verified |
| Agent 03 | Content Planner | All sections mapped |
| Agent 04 | Article Writer | Min word count + all elements |
| [Gold Standard Gate] | Content Validation | Post Ag04, Pre Ag11 |
| Agent 05 | Fact Checker | All claims verified |
| Agent 06 | EEAT Validator | Score ≥ 95 |
| Agent 07 | Internal Linking | ≥ 15 links (Gold) |
| Agent 08 | Affiliate Optimization | Max 3 partners |
| Agent 09 | Image Prompt Generator | 6 complete prompts |
| Agent 10 | Image Production | All images pass quality gate |
| Agent 11 | WordPress Integration | Draft published with all assets |
| Agent 12 | Quality Assurance | All 18 gates evaluated |
| Agent 13 | Chief Editor | READY_TO_PUBLISH only if all 18 pass |
| Agent 14 | Production Director | Morning + Executive reports |
| Agent 15 | Affiliate Compliance | FTC disclosure verified |
| Agent 16 | Publishing Optimization | SEO fully configured |
| Agent 17 | Cannibalization Check | No duplicate topics |
| Agent 18 | Revenue Intelligence | Score ≥ 60 |

---

## 13. PER-ARTICLE REPORTING

After every article, report: word count, FAQ count, source count, internal link count, case study count, image count, SEO score, EEAT score, QA score, publication readiness score.

---

## 14. DAILY REPORTING SCHEDULE

| Report | Time | Agent |
|---|---|---|
| Morning Production Report | 09:45 UTC | Agent 14 |
| Evening Production Report | 18:00 UTC | Agent 14 |
| Executive Daily Report | 18:30 UTC | Agent 14 |
| Global Quality Audit 1 | 09:30 UTC | Agent 13 |
| Global Quality Audit 2 | 16:30 UTC | Agent 13 |

---

## 15. REAL EXECUTION POLICY

Success is NEVER declared based on assumptions or code written. Required deliverables for STATUS = PUBLISHED:

Real WordPress Draft URL, Real WordPress Post ID, Real Featured Image URL, Real Uploaded Images URLs, qa_report.json, image_validation_report.json, image_quality_report.json, cannibalization_report.json, revenue_score.json, affiliate_compliance.json, publishing_optimizer.json, end_to_end_test_report.html.

If any item is missing: STATUS = FAILED. Never report success.

---

## 16. VERSION CONTROL

| Version | Date | Change |
|---|---|---|
| 1.0 | 2025-01-01 | NEXUS-14 V1 initial |
| 2.0 | 2026-06-01 | V2 — 16 agents, 15 quality gates |
| 3.0 | 2026-06-12 | V3 — 18 agents, 18 quality gates, two-tier content |
| 3.1 | 2026-06-14 | Master Directive + Gold Standard Gate integrated |

---

## 17. CONFLICT RESOLUTION

If any existing workflow, agent configuration, or sub-document conflicts with this directive: **this directive takes priority.**

The V3 system implementation (18 agents, 18 quality gates, STANDARD/PILLAR/Gold three-tier content, Revenue Intelligence, Cannibalization checks) is the authoritative production standard.

---

*This document is the constitutional reference for the NEXUS-14 ecosystem on MoneyAbroadGuide.com.*  
*Repository: talalnewjersey-ops/mag-autonomous-newsroom-v1 | Last updated: 2026-06-14*
