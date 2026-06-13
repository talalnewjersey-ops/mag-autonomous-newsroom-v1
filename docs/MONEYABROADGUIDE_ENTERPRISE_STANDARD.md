# MONEYABROADGUIDE ENTERPRISE STANDARD v3.0
## Official NEXUS-14 Operating Standard — Effective 2026-06-13

---

> **This document is the single source of truth for ALL content production on MoneyAbroadGuide.com.**
> Every article — new or existing — must comply with this standard before publication.
> Non-compliant articles must be rewritten or rejected.

---

## 1. GOVERNANCE

| Rule | Value |
|------|-------|
| Priority | Quality over volume |
| Minimum publication score | **95/100** |
| EEAT enforcement | **Mandatory** |
| QA approval | **Required — no exceptions** |
| Mobile-first | **Mandatory** |
| Max articles/day | **6** |
| Max articles/batch | **3** |
| Batch times | 06:00 UTC and 13:00 UTC |

---

## 2. ARTICLE TYPES (Authorized)

| Type | Slug Pattern |
|------|-------------|
| Best X for newcomers | `best-[product]-for-newcomers-[country]` |
| Comparison articles | `[product-a]-vs-[product-b]-for-newcomers` |
| Banking guides | `bank-account-for-newcomers-[country]` |
| Credit score guides | `credit-score-guide-newcomers-[country]` |
| Tax guides | `tax-guide-expats-[country]-[year]` |
| Money transfer guides | `best-way-to-send-money-[country]` |
| Insurance guides | `insurance-guide-newcomers-[country]` |
| Settlement guides | `newcomer-settlement-guide-[country]` |

---

## 3. GOLD STANDARD ARTICLE TEMPLATE

### Required Sections (in order)

1. **Introduction** — Problem + Opportunity + Expected outcome + CTA
2. **Quick Answer Box** — Summary for featured snippet
3. **Comparison Table** — Visual comparison of top options
4. **Deep Analysis** — Full research with primary sources
5. **Case Studies** — Minimum **6** real-world scenarios
6. **Expert Recommendation** — Author opinion with credentials
7. **FAQ Section** — Minimum **20 questions**
8. **Sources** — Minimum **10 primary sources**
9. **Conclusion** — Summary + CTA

---

## 4. CONTENT REQUIREMENTS

| Metric | Minimum | Target |
|--------|---------|--------|
| Word count | **8,500** | 10,000–12,000 |
| Case studies | **6** | 8+ |
| FAQ questions | **20** | 25+ |
| Internal links | **15** | 20+ |
| External sources | **10** | 15+ |
| Schemas | **5** | 5 (Article, FAQ, Person, Org, Breadcrumb) |

---

## 5. QUALITY GATES (All must score ≥ 95/100)

| Gate | Minimum Score |
|------|--------------|
| Content quality | **95/100** |
| SEO score | **95/100** |
| EEAT score | **95/100** |
| UX score | **95/100** |
| WordPress technical | **95/100** |
| Overall publication score | **95/100** |

**Pipeline gates (before content generation):**
- Revenue Intelligence score ≥ 60/100 (gate 2.6)
- Cannibalization check: PASS required (gate 2.5)

---

## 6. IMAGE SYSTEM (6 images per article)

| # | Image Type | Purpose |
|---|-----------|---------|
| 1 | Featured Image | Hero image, 1200×628 |
| 2 | Comparison Graphic | Side-by-side table visual |
| 3 | Process Graphic | Step-by-step infographic |
| 4 | Checklist Graphic | Action checklist visual |
| 5 | Data Visualization | Chart or graph |
| 6 | Topic Graphic | Supporting illustration |

**For each image, NEXUS-14 must generate:**
- Prompt (for Gemini/NanoBanana)
- Alt text (keyword-optimized)
- Caption (context-informative)
- Filename (SEO-friendly slug)
- Placement (exact position in article)

---

## 7. SEO FRAMEWORK

**Title:** Primary keyword + year + intent modifier
**Slug:** lowercase-hyphenated, max 60 chars
**Meta description:** 150–160 chars, includes primary keyword + CTA

**Keyword requirements:**
- 1 primary keyword (target keyword)
- 3–5 secondary keywords
- 5–10 semantic entities (people, places, organizations)

**Internal linking:**
- Minimum 15 internal links per article
- Links must use descriptive anchor text
- No orphan articles (every article linked from at least 2 others)

---

## 8. EEAT FRAMEWORK (All mandatory)

| Element | Requirement |
|---------|------------|
| Author box | Full name, credentials, photo |
| Founder bio | MoneyAbroadGuide founder details |
| Sources section | Government + primary sources only |
| Compliance section | Legal/financial disclaimer |
| Expert recommendation | Named expert or author opinion |
| Real-world scenarios | Minimum 6 case studies |
| Last reviewed date | Must be current year |

---

## 9. AFFILIATE SYSTEM

| Rule | Value |
|------|-------|
| Maximum partners per article | **3** |
| Link attributes | `rel="nofollow sponsored" target="_blank"` |
| CTA positions | Top + Middle + Bottom of article |
| Disclosure | FTC-compliant disclosure at top |

---

## 10. EBOOK/LEAD GENERATION SYSTEM

**Mandatory CTA locations:**
1. After the Introduction (before comparison table)
2. Mid-article (after case studies)
3. Before the Conclusion

---

## 11. WORDPRESS PUBLICATION SOP

| Step | Action |
|------|--------|
| 1 | Create draft in WordPress |
| 2 | Upload all 6 images to Media Library |
| 3 | Assign author with EEAT credentials |
| 4 | Add categories (max 2) |
| 5 | Add tags (5–10 descriptive tags) |
| 6 | Insert 5 schemas (Article, FAQ, Person, Org, Breadcrumb) |
| 7 | Configure SEO (Rank Math or Yoast) |
| 8 | Run QA checklist (score ≥ 95) |
| 9 | Schedule publication |

---

## 12. DRAFT REWRITE SYSTEM (Existing Articles)

When NEXUS-14 audits existing articles, it must:

1. Audit current article vs this standard
2. Expand content to 8,500+ words
3. Add/update EEAT elements
4. Expand FAQ to 20+ questions
5. Add/replace all 6 images
6. Add/verify 5 schemas
7. Verify 15+ internal links
8. Run QA gate (score ≥ 95)
9. Republish with updated date

---

## 13. SCHEMA REQUIREMENTS (5 per article)

| Schema | Purpose |
|--------|---------|
| Article | Core article metadata |
| FAQPage | All 20+ FAQ questions |
| Person | Author credentials |
| Organization | MoneyAbroadGuide.com entity |
| BreadcrumbList | Navigation path |

---

## 14. REPORTING

| Report | Frequency | Agent |
|--------|-----------|-------|
| Production batch report | After each batch | Agent 14 |
| Daily production report | 18:00 UTC | Agent 14 |
| Weekly KPI report | Monday 08:00 UTC | Agent 14 |
| Monthly performance report | 1st of month | Agent 14 |

**KPIs tracked:**
- Articles published (target: 6/day)
- Average content score (target: ≥ 95/100)
- Traffic per article (from WordPress analytics)
- Affiliate click-through rate
- Ebook conversion rate

---

## 15. NEXUS-14 AGENT RESPONSIBILITIES

| Agent | Responsibility | Enterprise Gate |
|-------|---------------|-----------------|
| Agent 01 | SEO Research + Topic Selection | Revenue ≥ 60 |
| Agent 02 | Keyword Validation | Intent verified |
| Agent 03 | Content Outline | All sections present |
| Agent 04 | Article Writing | 8,500+ words |
| Agent 05 | Fact Checking | 10+ sources |
| Agent 06 | EEAT Validation | Score ≥ 95 |
| Agent 07 | Internal Linking | 15+ links |
| Agent 08 | Affiliate Optimization | Max 3 partners |
| Agent 09 | Image Prompts | 6 prompts complete |
| Agent 10 | Image Production | 6 images generated |
| Agent 11 | WordPress Integration | Draft published |
| Agent 12 | Quality Assurance | Overall ≥ 95 |
| Agent 13 | Chief Editor Decision | READY_TO_PUBLISH |
| Agent 14 | Production Director | Report generated |
| Agent 15 | Affiliate Compliance | FTC compliant |
| Agent 16 | Publishing Optimization | SEO configured |
| Agent 17 | Cannibalization Check | No duplicate |
| Agent 18 | Revenue Intelligence | Score ≥ 60 |

---

## 16. VERSION CONTROL

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2025-01-01 | Initial NEXUS-14 V1 |
| 2.0 | 2026-06-01 | V2 — 18 quality gates |
| 3.0 | 2026-06-13 | **ENTERPRISE** — 95/100 standard, 8500 words, Gold Standard |

---

*This document is enforced by the NEXUS-14 GitHub Actions workflow production_v2.yml.*
*Every run validates compliance with this standard before publication.*
*Non-compliant articles are automatically rejected by the quality pipeline.*
