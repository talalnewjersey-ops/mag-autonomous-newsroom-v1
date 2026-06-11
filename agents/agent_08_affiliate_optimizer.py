"""
NEXUS-14 - Agent 08: Affiliate Optimization Agent
MoneyAbroadGuide Autonomous Newsroom
Detects affiliate opportunities: banks, credit cards, insurance,
money transfer, fintech. Adds approved affiliate blocks.
Output: affiliate_report.json
"""

import json
import re
import logging
from datetime import datetime
from typing import Any
from pathlib import Path

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Affiliate program registry
AFFILIATE_PROGRAMS = {
    "wise": {
        "name": "Wise (TransferWise)",
        "category": "money_transfer",
        "cta": "Send money abroad with Wise - up to 8x cheaper than banks",
        "url_template": "https://wise.com?ref=MAG",
        "keywords": ["wise", "transferwise", "international transfer", "send money abroad", "remittance", "currency exchange"],
        "commission": "cpa",
        "priority": 10,
    },
    "revolut": {
        "name": "Revolut",
        "category": "fintech",
        "cta": "Get Revolut - the all-in-one financial app for expats",
        "url_template": "https://revolut.com?ref=MAG",
        "keywords": ["revolut", "neobank", "digital bank", "multi-currency", "fintech"],
        "commission": "cpa",
        "priority": 9,
    },
    "rbc_canada": {
        "name": "RBC Newcomers Package",
        "category": "banking_canada",
        "cta": "Open an RBC bank account as a newcomer to Canada - no monthly fees for 1 year",
        "url_template": "https://www.rbcroyalbank.com/newcomers?ref=MAG",
        "keywords": ["rbc", "newcomer to canada", "newcomer bank account", "move to canada", "canadian bank"],
        "commission": "cpl",
        "priority": 10,
    },
    "td_canada": {
        "name": "TD Canada Trust",
        "category": "banking_canada",
        "cta": "TD Bank for newcomers to Canada - special welcome offer",
        "url_template": "https://www.td.com/ca/en/personal-banking/newcomers?ref=MAG",
        "keywords": ["td bank", "td canada", "toronto dominion", "newcomer banking"],
        "commission": "cpl",
        "priority": 9,
    },
    "scotiabank": {
        "name": "Scotiabank StartRight",
        "category": "banking_canada",
        "cta": "Scotiabank StartRight Program - designed for newcomers to Canada",
        "url_template": "https://www.scotiabank.com/startright?ref=MAG",
        "keywords": ["scotiabank", "startright", "newcomer scotiabank", "canadian banking newcomer"],
        "commission": "cpl",
        "priority": 8,
    },
    "charles_schwab": {
        "name": "Charles Schwab International",
        "category": "banking_usa",
        "cta": "Charles Schwab - no foreign transaction fees, global ATM rebates",
        "url_template": "https://www.schwab.com/international?ref=MAG",
        "keywords": ["charles schwab", "schwab international", "expat banking usa", "no atm fees abroad"],
        "commission": "cpa",
        "priority": 9,
    },
    "manulife_insurance": {
        "name": "Manulife Travel Insurance",
        "category": "insurance",
        "cta": "Manulife travel insurance - comprehensive coverage for expats",
        "url_template": "https://www.manulife.com/insurance?ref=MAG",
        "keywords": ["manulife", "travel insurance", "expat insurance", "health insurance abroad"],
        "commission": "cps",
        "priority": 7,
    },
    "world_nomads": {
        "name": "World Nomads Insurance",
        "category": "insurance",
        "cta": "World Nomads - travel insurance built for adventurous expats",
        "url_template": "https://www.worldnomads.com?ref=MAG",
        "keywords": ["world nomads", "nomad insurance", "digital nomad insurance", "travel insurance expat"],
        "commission": "cps",
        "priority": 6,
    },
}

# Affiliate block HTML templates
BLOCK_TEMPLATES = {
    "inline": (
        '<div class="mag-affiliate-block mag-affiliate-inline">'
        '<span class="mag-affiliate-badge">Recommended</span>'
        '<strong>{name}</strong> - {cta} '
        '<a href="{url}" rel="sponsored nofollow" target="_blank" '
        'class="mag-affiliate-link mag-btn-primary">Get Started</a>'
        '</div>'
    ),
    "box": (
        '<div class="mag-affiliate-box">'
        '<div class="mag-affiliate-box-header"><span class="mag-badge">Affiliate</span>'
        '{name}</div>'
        '<p>{cta}</p>'
        '<a href="{url}" rel="sponsored nofollow" target="_blank" '
        'class="mag-btn-cta">Learn More &rarr;</a>'
        '</div>'
    ),
}


class AffiliateOptimizerAgent(BaseAgent):
    """Agent 08: Automated affiliate link optimization."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(agent_id="agent_08", name="AffiliateOptimizerAgent", config=config)
        self.llm_service = None
        self.max_affiliates = config.get("max_affiliate_blocks", 4)
        self.block_style = config.get("affiliate_block_style", "box")

    async def run(self, article_draft_path: str, output_dir: str = "outputs") -> dict[str, Any]:
        """Detect affiliate opportunities and generate approved blocks."""
        self.logger.info("Agent 08 - Affiliate Optimizer starting...")
        start_time = datetime.now()

        draft_path = Path(article_draft_path)
        if not draft_path.exists():
            raise FileNotFoundError(f"Article draft not found: {article_draft_path}")
        article_text = draft_path.read_text(encoding="utf-8")
        article_lower = article_text.lower()

        # Detect relevant affiliate programs
        opportunities = self._detect_opportunities(article_lower)
        self.logger.info(f"Detected {len(opportunities)} affiliate opportunities")

        # Score and rank by priority and relevance
        ranked = sorted(opportunities, key=lambda x: x["score"], reverse=True)
        selected = ranked[:self.max_affiliates]

        # Generate affiliate blocks
        blocks = self._generate_blocks(selected)

        # Find best insertion points
        insertion_points = self._find_insertion_points(article_text, selected)

        # LLM enhancement
        llm_suggestions = []
        if self.llm_service:
            try:
                llm_suggestions = await self._llm_suggest_placements(article_text, selected)
            except Exception as e:
                self.logger.warning(f"LLM affiliate suggestion failed: {e}")

        elapsed = (datetime.now() - start_time).total_seconds()
        report = {
            "agent": "agent_08_affiliate_optimizer",
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "summary": {
                "total_programs_checked": len(AFFILIATE_PROGRAMS),
                "opportunities_detected": len(opportunities),
                "selected_affiliates": len(selected),
                "blocks_generated": len(blocks),
            },
            "opportunities": opportunities,
            "selected_affiliates": selected,
            "affiliate_blocks": blocks,
            "insertion_points": insertion_points,
            "llm_suggestions": llm_suggestions,
            "compliance": self._generate_compliance_notes(selected),
        }

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "affiliate_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self.logger.info(f"Affiliate optimization complete - {len(blocks)} blocks generated")
        return report

    def _detect_opportunities(self, text: str) -> list:
        opportunities = []
        for prog_id, prog in AFFILIATE_PROGRAMS.items():
            matched_kws = [kw for kw in prog["keywords"] if kw.lower() in text]
            if matched_kws:
                score = len(matched_kws) * prog["priority"]
                opportunities.append({
                    "program_id": prog_id,
                    "name": prog["name"],
                    "category": prog["category"],
                    "cta": prog["cta"],
                    "url": prog["url_template"],
                    "matched_keywords": matched_kws[:5],
                    "priority": prog["priority"],
                    "score": score,
                    "commission_type": prog["commission"],
                })
        return opportunities

    def _generate_blocks(self, affiliates: list) -> list:
        blocks = []
        template = BLOCK_TEMPLATES.get(self.block_style, BLOCK_TEMPLATES["box"])
        for aff in affiliates:
            html = template.format(
                name=aff["name"],
                cta=aff["cta"],
                url=aff["url"],
            )
            blocks.append({
                "program_id": aff["program_id"],
                "name": aff["name"],
                "html": html,
                "style": self.block_style,
                "position": "after_section",
            })
        return blocks

    def _find_insertion_points(self, article_text: str, affiliates: list) -> list:
        insertions = []
        paragraphs = article_text.split("\n\n")
        total_paras = len(paragraphs)
        for i, aff in enumerate(affiliates):
            # Distribute evenly through article (25%, 50%, 75% positions)
            ideal_para = int(total_paras * (i + 1) / (len(affiliates) + 1))
NEXUS-14 - Agent 08: Affiliate Optimization Agent
MoneyAbroadGuide Autonomous Newsroom

Detects affiliate opportunities in articles and
integrates affiliate blocks for banks, cards, insurance,
money transfer, and fintech services.
Output: affiliate_report.json
"""

import json
import re
import logging
from datetime import datetime
from pathlib import Path

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Affiliate program catalog
AFFILIATE_PROGRAMS = {
    # Money Transfer
    "wise": {
        "category": "money_transfer",
        "name": "Wise (formerly TransferWise)",
        "affiliate_url": "https://moneyabroadguide.com/go/wise/",
        "commission": "15 USD per signup",
        "keywords": ["wise", "transferwise", "wise transfer", "wise fees", "wise review"],
        "cta": "Send Money with Wise - Low Fees",
        "block_template": "cta_box",
        "priority": 1,
    },
    "revolut": {
        "category": "money_transfer",
        "name": "Revolut",
        "affiliate_url": "https://moneyabroadguide.com/go/revolut/",
        "commission": "10 USD per signup",
        "keywords": ["revolut", "revolut account", "revolut fees", "multi-currency account"],
        "cta": "Open a Revolut Account - Free",
        "block_template": "cta_box",
        "priority": 2,
    },
    "remitly": {
        "category": "money_transfer",
        "name": "Remitly",
        "affiliate_url": "https://moneyabroadguide.com/go/remitly/",
        "commission": "10 USD per transfer",
        "keywords": ["remitly", "send money home", "remittance"],
        "cta": "Send Money with Remitly",
        "block_template": "cta_box",
        "priority": 3,
    },
    "xe": {
        "category": "money_transfer",
        "name": "XE Money Transfer",
        "affiliate_url": "https://moneyabroadguide.com/go/xe/",
        "commission": "8 USD per transfer",
        "keywords": ["xe", "xe money transfer", "xe.com"],
        "cta": "Transfer with XE - Competitive Rates",
        "block_template": "cta_box",
        "priority": 4,
    },
    # Banking
    "n26": {
        "category": "banking",
        "name": "N26 Bank",
        "affiliate_url": "https://moneyabroadguide.com/go/n26/",
        "commission": "25 USD per account",
        "keywords": ["n26", "n26 bank", "n26 account", "n26 card"],
        "cta": "Open N26 Account - Free",
        "block_template": "comparison_box",
        "priority": 5,
    },
    "chime": {
        "category": "banking",
        "name": "Chime",
        "affiliate_url": "https://moneyabroadguide.com/go/chime/",
        "commission": "20 USD per account",
        "keywords": ["chime", "chime bank", "chime account", "chime card"],
        "cta": "Get Chime - No Hidden Fees",
        "block_template": "comparison_box",
        "priority": 6,
    },
    # Insurance
    "safetywing": {
        "category": "insurance",
        "name": "SafetyWing Travel Insurance",
        "affiliate_url": "https://moneyabroadguide.com/go/safetywing/",
        "commission": "10% of premium",
        "keywords": ["safetywing", "expat insurance", "nomad insurance", "travel insurance"],
        "cta": "Get SafetyWing Insurance",
        "block_template": "insurance_box",
        "priority": 7,
    },
    "cigna": {
        "category": "insurance",
        "name": "Cigna Global Health",
        "affiliate_url": "https://moneyabroadguide.com/go/cigna/",
        "commission": "50 USD per signup",
        "keywords": ["cigna", "cigna global", "global health insurance", "international health"],
        "cta": "Get Cigna Global Health Insurance",
        "block_template": "insurance_box",
        "priority": 8,
    },
    # Fintech
    "payoneer": {
        "category": "fintech",
        "name": "Payoneer",
        "affiliate_url": "https://moneyabroadguide.com/go/payoneer/",
        "commission": "25 USD per signup",
        "keywords": ["payoneer", "payoneer card", "payoneer account", "freelancer payment"],
        "cta": "Get Payoneer - Global Payments",
        "block_template": "cta_box",
        "priority": 9,
    },
    "transfergo": {
        "category": "money_transfer",
        "name": "TransferGo",
        "affiliate_url": "https://moneyabroadguide.com/go/transfergo/",
        "commission": "8 USD per transfer",
        "keywords": ["transfergo", "transfer go", "transfergo review"],
        "cta": "Transfer with TransferGo",
        "block_template": "cta_box",
        "priority": 10,
    },
}

# Block templates
BLOCK_TEMPLATES = {
    "cta_box": """
<div class="affiliate-cta-box">
  <h3>{name}</h3>
  <p class="affiliate-description">{description}</p>
  <a href="{url}" class="affiliate-btn" rel="sponsored noopener" target="_blank">{cta}</a>
  <small class="affiliate-disclosure">Affiliate link - we may earn a commission</small>
</div>""",
    "comparison_box": """
<div class="affiliate-comparison-box">
  <div class="comparison-header">
    <h3>{name}</h3>
    <span class="rating">{rating}/5</span>
  </div>
  <ul class="pros-list">{pros}</ul>
  <a href="{url}" class="affiliate-btn" rel="sponsored noopener" target="_blank">{cta}</a>
  <small class="affiliate-disclosure">Affiliate link - we may earn a commission</small>
</div>""",
    "insurance_box": """
<div class="affiliate-insurance-box">
  <h3>{name}</h3>
  <p class="coverage">Coverage from {coverage}/month</p>
  <a href="{url}" class="affiliate-btn" rel="sponsored noopener" target="_blank">{cta}</a>
  <small class="affiliate-disclosure">Affiliate link - we may earn a commission</small>
</div>""",
}


class AffiliateOptimizerAgent(BaseAgent):
    """Agent 08 - Affiliate detection and block integration."""

    MAX_AFFILIATE_BLOCKS = 5

    def __init__(self, config: dict):
        super().__init__(agent_id="agent_08", name="AffiliateOptimizerAgent", config=config)

    async def run(self, article_draft_path: str, output_dir: str = "outputs") -> dict:
        """
        Scan article for affiliate opportunities and integrate blocks.
        Output: affiliate_report.json and article_with_affiliates.md
        """
        self.logger.info("Agent 08 - Affiliate Optimizer starting...")
        start_time = datetime.now()

        draft_path = Path(article_draft_path)
        if not draft_path.exists():
            raise FileNotFoundError(f"Article draft not found: {article_draft_path}")
        article_text = draft_path.read_text(encoding="utf-8")

        # Detect opportunities
        opportunities = self._detect_opportunities(article_text)
        self.logger.info(f"Found {len(opportunities)} affiliate opportunities")

        # Select top programs (max MAX_AFFILIATE_BLOCKS)
        selected = self._select_programs(opportunities)

        # Generate affiliate blocks
        blocks = [self._generate_block(prog) for prog in selected]

        # Integrate blocks into article
        enhanced_article = self._integrate_blocks(article_text, blocks, selected)

        # Save enhanced article
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "article_with_affiliates.md").write_text(enhanced_article, encoding="utf-8")

        report = self._build_report(opportunities, selected, blocks, start_time)
        (output_path / "affiliate_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

        self.logger.info(f"Affiliate optimization complete: {len(selected)} blocks added")
        return report

    # ------------------------------------------------------------------ #
    #  Opportunity Detection                                               #
    # ------------------------------------------------------------------ #

    def _detect_opportunities(self, text: str) -> list:
        """Find all affiliate opportunities in the article text."""
        opportunities = []
        text_lower = text.lower()
        for prog_id, prog in AFFILIATE_PROGRAMS.items():
            matches = []
            for kw in prog["keywords"]:
                found = list(re.finditer(r"\b" + re.escape(kw.lower()) + r"\b", text_lower))
                matches.extend(found)
            if matches:
                opportunities.append({
                    "program_id": prog_id,
                    "name": prog["name"],
                    "category": prog["category"],
                    "keyword_matches": len(matches),
                    "matched_keywords": list(set(m.group() for m in matches[:5])),
                    "priority": prog["priority"],
                    "commission": prog["commission"],
                    "affiliate_url": prog["affiliate_url"],
                })
        return sorted(opportunities, key=lambda x: (x["keyword_matches"], -x["priority"]), reverse=True)

    def _select_programs(self, opportunities: list) -> list:
        """Select top programs up to the maximum limit."""
        # Prioritize by keyword matches, then by priority
        sorted_ops = sorted(
            opportunities,
            key=lambda x: (x["keyword_matches"] * 10 - x["priority"]),
            reverse=True
        )
        # Ensure category diversity (max 2 per category)
        selected = []
        category_counts: dict[str, int] = {}
        for op in sorted_ops:
            cat = op["category"]
            if category_counts.get(cat, 0) < 2 and len(selected) < self.MAX_AFFILIATE_BLOCKS:
                selected.append(op)
                category_counts[cat] = category_counts.get(cat, 0) + 1
        return selected

    # ------------------------------------------------------------------ #
    #  Block Generation                                                    #
    # ------------------------------------------------------------------ #

    def _generate_block(self, opportunity: dict) -> str:
        """Generate HTML affiliate block for a program."""
        prog = AFFILIATE_PROGRAMS.get(opportunity["program_id"], {})
        template_name = prog.get("block_template", "cta_box")
        template = BLOCK_TEMPLATES.get(template_name, BLOCK_TEMPLATES["cta_box"])
        return template.format(
            name=prog.get("name", ""),
            url=prog.get("affiliate_url", "#"),
            cta=prog.get("cta", "Learn More"),
            description=f"One of the best services for {opportunity['category'].replace('_', ' ')}",
            rating="4.5",
            pros="<li>Competitive rates</li><li>No hidden fees</li>",
            coverage="$50",
        )

    def _integrate_blocks(self, text: str, blocks: list, selected: list) -> str:
        """Integrate affiliate blocks into article at optimal positions."""
        # Add blocks at natural section breaks
        paragraphs = text.split("\n\n")
        result_paragraphs = list(paragraphs)

        # Insert blocks after every ~5 paragraphs of content
        block_idx = 0
        total_paragraphs = len(result_paragraphs)
        insertion_points = []
        if total_paragraphs >= 5:
            interval = max(5, total_paragraphs // (len(blocks) + 1))
            pos = interval
            while pos < total_paragraphs and block_idx < len(blocks):
                insertion_points.append((pos, block_idx))
                block_idx += 1
                pos += interval

        # Insert in reverse order to preserve positions
        for pos, idx in sorted(insertion_points, reverse=True):
            if idx < len(blocks):
                result_paragraphs.insert(pos, blocks[idx])

        return "\n\n".join(result_paragraphs)

    # ------------------------------------------------------------------ #
    #  Report Builder                                                      #
    # ------------------------------------------------------------------ #

    def _build_report(self, opportunities: list, selected: list, blocks: list, start_time: datetime) -> dict:
        elapsed = (datetime.now() - start_time).total_seconds()
        by_category: dict[str, list] = {}
        for op in selected:
            cat = op["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(op["name"])

        return {
            "agent": "agent_08_affiliate_optimizer",
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "summary": {
                "total_opportunities": len(opportunities),
                "selected_programs": len(selected),
                "blocks_generated": len(blocks),
                "categories_covered": list(by_category.keys()),
            },
            "opportunities": opportunities,
            "selected_programs": selected,
            "by_category": by_category,
            "affiliate_disclosure": "Articles may contain affiliate links. We earn a commission when you click through and make a purchase.",
            "recommendations": self._generate_recommendations(opportunities, selected),
        }

    def _generate_recommendations(self, opportunities: list, selected: list) -> list:
        recs = []
        if not opportunities:
            recs.append("No affiliate opportunities detected - add mentions of recommended services")
        elif len(opportunities) < 3:
            recs.append(f"Only {len(opportunities)} opportunities found - consider adding more service mentions")
        if len(selected) < 2:
            recs.append("Very few affiliate blocks added - consider adding more service comparisons")
        unmatched_categories = set(AFFILIATE_PROGRAMS[k]["category"] for k in AFFILIATE_PROGRAMS)
        covered = set(op["category"] for op in selected)
        missing = unmatched_categories - covered
        if missing:
            recs.append(f"Categories not covered: {list(missing)} - consider adding content about these")
        if not recs:
            recs.append("Affiliate optimization complete - all categories covered")
        return recs
