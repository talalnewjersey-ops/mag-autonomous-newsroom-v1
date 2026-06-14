"""
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
    "cta_box": (
        '<div class="affiliate-cta-box">'
        "<h3>{name}</h3>"
        '<p class="affiliate-description">{description}</p>'
        '<a href="{url}" class="affiliate-btn" rel="sponsored noopener" target="_blank">{cta}</a>'
        '<small class="affiliate-disclosure">Affiliate link - we may earn a commission</small>'
        "</div>"
    ),
    "comparison_box": (
        '<div class="affiliate-comparison-box">'
        '<div class="comparison-header">'
        "<h3>{name}</h3>"
        '<span class="rating">{rating}/5</span>'
        "</div>"
        '<ul class="pros-list">{pros}</ul>'
        '<a href="{url}" class="affiliate-btn" rel="sponsored noopener" target="_blank">{cta}</a>'
        '<small class="affiliate-disclosure">Affiliate link - we may earn a commission</small>'
        "</div>"
    ),
    "insurance_box": (
        '<div class="affiliate-insurance-box">'
        "<h3>{name}</h3>"
        '<p class="coverage">Coverage from {coverage}/month</p>'
        '<a href="{url}" class="affiliate-btn" rel="sponsored noopener" target="_blank">{cta}</a>'
        '<small class="affiliate-disclosure">Affiliate link - we may earn a commission</small>'
        "</div>"
    ),
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

        opportunities = self._detect_opportunities(article_text)
        self.logger.info(f"Found {len(opportunities)} affiliate opportunities")

        selected = self._select_programs(opportunities)
        blocks = [self._generate_block(prog) for prog in selected]
        enhanced_article = self._integrate_blocks(article_text, blocks, selected)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "article_with_affiliates.md").write_text(enhanced_article, encoding="utf-8")

        report = self._build_report(opportunities, selected, blocks, start_time)
        (output_path / "affiliate_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        self.logger.info(f"Affiliate optimization complete: {len(selected)} blocks added")
        return report

    def _detect_opportunities(self, text: str) -> list:
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
        return sorted(
            opportunities,
            key=lambda x: (x["keyword_matches"], -x["priority"]),
            reverse=True,
        )

    def _select_programs(self, opportunities: list) -> list:
        sorted_ops = sorted(
            opportunities,
            key=lambda x: (x["keyword_matches"] * 10 - x["priority"]),
            reverse=True,
        )
        selected = []
        category_counts: dict = {}
        for op in sorted_ops:
            cat = op["category"]
            if category_counts.get(cat, 0) < 2 and len(selected) < self.MAX_AFFILIATE_BLOCKS:
                selected.append(op)
                category_counts[cat] = category_counts.get(cat, 0) + 1
        return selected

    def _generate_block(self, opportunity: dict) -> str:
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
        paragraphs = text.split("\n\n")
        result_paragraphs = list(paragraphs)
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
        for pos, idx in sorted(insertion_points, reverse=True):
            if idx < len(blocks):
                result_paragraphs.insert(pos, blocks[idx])
        return "\n\n".join(result_paragraphs)

    def _build_report(self, opportunities: list, selected: list, blocks: list, start_time: datetime) -> dict:
        elapsed = (datetime.now() - start_time).total_seconds()
        by_category: dict = {}
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
            "affiliate_disclosure": (
                "Articles may contain affiliate links. "
                "We earn a commission when you click through and make a purchase."
            ),
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


def main():
    """CLI entry point for workflow execution."""
    import argparse
    import sys
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [AGENT-08] %(levelname)s %(message)s",
    )
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Agent 08 - Affiliate Optimizer")
    parser.add_argument("--input", required=True, help="Path to article_draft.md")
    parser.add_argument("--output", required=True, help="Output path for affiliate_report.json")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        log.error(f"Article draft not found: {input_path}")
        sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    agent = AffiliateOptimizerAgent(config)

    try:
        report = asyncio.run(
            agent.run(
                article_draft_path=str(input_path),
                output_dir=str(output_path.parent),
            )
        )
        opp_count = len(report.get("opportunities", []))
        log.info(f"Affiliate optimization complete: {opp_count} opportunities found")
        log.info(f"Report written: {output_path}")
        sys.exit(0)
    except Exception as e:
        log.error(f"Affiliate optimization failed: {e}")
        fallback = {
            "agent": "agent_08_affiliate_optimizer",
            "timestamp": datetime.utcnow().isoformat(),
            "verdict": "SKIPPED",
            "opportunities": [],
            "summary": {"total_opportunities": 0},
            "error": str(e),
        }
        output_path.write_text(json.dumps(fallback, indent=2), encoding="utf-8")
        log.warning(f"Fallback report written: {output_path}")
        sys.exit(0)


if __name__ == "__main__":
    main()
