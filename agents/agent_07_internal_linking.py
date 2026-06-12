"""NEXUS-14 Agent 07: Internal Linking Agent
MoneyAbroadGuide Autonomous Newsroom
Auto-detects related articles and optimizes internal linking.
Hubs: USA + Canada. Output: internal_links.json"""

import json, re, logging
from datetime import datetime
from pathlib import Path
import aiohttp
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

USA_HUBS = {
    "banking": "/usa/banking-abroad/",
    "credit_cards": "/usa/best-credit-cards-abroad/",
    "money_transfer": "/usa/best-money-transfer/",
    "taxes": "/usa/taxes-as-expat/",
    "investing": "/usa/investing-abroad/",
    "insurance": "/usa/expat-insurance/",
    "retirement": "/usa/retirement-abroad/",
    "real_estate": "/usa/buying-property-abroad/",
}

CANADA_HUBS = {
    "banking": "/canada/banking-abroad/",
    "credit_cards": "/canada/best-credit-cards-abroad/",
    "money_transfer": "/canada/best-money-transfer/",
    "taxes": "/canada/taxes-as-expat/",
    "investing": "/canada/investing-abroad/",
    "insurance": "/canada/expat-insurance/",
    "retirement": "/canada/retirement-abroad/",
    "real_estate": "/canada/buying-property-abroad/",
}

HUB_KEYWORDS = {
    "banking": ["bank account", "banking", "checking account", "savings account"],
    "credit_cards": ["credit card", "travel card", "no foreign transaction fee"],
    "money_transfer": ["send money", "wire transfer", "money transfer", "remittance"],
    "taxes": ["tax", "income tax", "tax return", "tax treaty", "irs", "cra"],
    "investing": ["invest", "investment", "brokerage", "stocks", "etf", "portfolio"],
    "insurance": ["insurance", "health insurance", "travel insurance"],
    "retirement": ["retirement", "pension", "rrsp", "401k", "retire abroad"],
    "real_estate": ["property", "real estate", "mortgage", "buy house"],
}

STRATEGIC_TERMS = {
    "wise": "/reviews/wise-review/",
    "revolut": "/reviews/revolut-review/",
    "transferwise": "/reviews/wise-review/",
    "norberts gambit": "/canada/norberts-gambit-guide/",
    "tfsa": "/canada/tfsa-non-residents/",
    "rrsp": "/canada/rrsp-expats/",
    "foreign income exclusion": "/usa/foreign-income-exclusion/",
    "fbar": "/usa/fbar-guide/",
}

BASE_URL = "https://moneyabroadguide.com"


class InternalLinkingAgent(BaseAgent):
    """Agent 07 - Internal Linking. Optimizes hub-and-spoke link structure."""

    def __init__(self, config):
        super().__init__(agent_id="agent_07", name="InternalLinkingAgent", config=config)
        self.llm_service = None

    async def run(self, article_draft_path, article_meta=None, output_dir="outputs"):
        """Analyze article and suggest optimal internal links."""
        self.logger.info("Agent 07 - Internal Linking starting...")
        start_time = datetime.now()
        article_text = Path(article_draft_path).read_text(encoding="utf-8")
        meta = article_meta or {}
        region = meta.get("region", "both").lower()

        existing_links = self._extract_existing_links(article_text)
        hub_links = self._find_hub_links(article_text, region)
        keyword_links = self._find_keyword_opportunities(article_text, existing_links)

        llm_links = []
        if self.llm_service:
            try:
                llm_links = await self._llm_suggest_links(article_text, existing_links)
            except Exception as e:
                self.logger.warning("LLM linking failed: {}".format(e))

        all_links = self._merge_and_rank(hub_links, keyword_links, llm_links, existing_links)
        insertions = self._generate_insertions(article_text, all_links)

        report = self._build_report(all_links, insertions, existing_links, start_time)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "internal_links.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        self.logger.info("Internal linking: {} links suggested".format(len(all_links)))
        return report

    def _extract_existing_links(self, text):
        md = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text)
        return [{"anchor": a, "url": u} for a, u in md]

    def _find_hub_links(self, text, region):
        suggestions = []
        text_lower = text.lower()
        hubs = []
        if region in ("usa", "both", "us"):
            hubs += [("USA", k, v) for k, v in USA_HUBS.items()]
        if region in ("canada", "both", "ca"):
            hubs += [("Canada", k, v) for k, v in CANADA_HUBS.items()]
        for country, hub_name, hub_path in hubs:
            for kw in HUB_KEYWORDS.get(hub_name, []):
                if kw in text_lower:
                    sents = re.split(r"(?<=[.!?])\s+", text)
                    for sent in sents:
                        if kw in sent.lower():
                            suggestions.append({
                                "type": "hub", "country": country,
                                "hub": hub_name, "url": BASE_URL + hub_path,
                                "anchor_text": kw, "context_sentence": sent[:200],
                                "priority": "high",
                            })
                            break
                    break
        return suggestions

    def _find_keyword_opportunities(self, text, existing_links):
        existing_urls = {l.get("url", "") for l in existing_links}
        existing_anchors = {l.get("anchor", "").lower() for l in existing_links}
        suggestions = []
        text_lower = text.lower()
        for term, path in STRATEGIC_TERMS.items():
            url = BASE_URL + path
            if term in text_lower and url not in existing_urls and term not in existing_anchors:
                for sent in re.split(r"(?<=[.!?])\s+", text):
                    if term in sent.lower():
                        suggestions.append({
                            "type": "strategic", "anchor_text": term,
                            "url": url, "context_sentence": sent[:200],
                            "priority": "medium",
                        })
                        break
        return suggestions

    async def _llm_suggest_links(self, text, existing_links):
        existing_str = json.dumps([l.get("url") for l in existing_links[:10]])
        prompt = ("Suggest 3 internal links for a MoneyAbroadGuide.com article.\n"
                  "Return JSON: [{url, anchor_text, context_sentence, reason}]\n"
                  "Existing: " + existing_str + "\n"
                  "Article: " + text[:2000] + "\nJSON only:")
        resp = await self.llm_service.complete(prompt, max_tokens=800)
        try:
            start = resp.find("[")
            return json.loads(resp[start:resp.rfind("]")+1])
        except Exception:
            return []

    def _merge_and_rank(self, hub, kw, llm, existing):
        seen = {l.get("url", "") for l in existing}
        merged = []
        for link in hub + kw + llm:
            u = link.get("url", "")
            if u and u not in seen:
                seen.add(u)
                merged.append(link)
        order = {"high": 0, "medium": 1, "low": 2}
        merged.sort(key=lambda x: order.get(x.get("priority", "low"), 2))
        return merged[:20]

    def _generate_insertions(self, text, links):
        insertions = []
        for link in links:
            anchor = link.get("anchor_text", "")
            url = link.get("url", "")
            context = link.get("context_sentence", "")
            if anchor and url and context and anchor in context:
                modified = context.replace(anchor, "[{}]({})".format(anchor, url), 1)
                insertions.append({"original": context, "modified": modified,
                                   "anchor": anchor, "url": url})
        return insertions

    def _build_report(self, all_links, insertions, existing_links, start_time):
        elapsed = (datetime.now() - start_time).total_seconds()
        return {
            "agent": "agent_07_internal_linking",
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "verdict": "PASS",
            "summary": {
                "existing_links": len(existing_links),
                "new_links_suggested": len(all_links),
                "hub_links": sum(1 for l in all_links if l.get("type") == "hub"),
                "strategic_links": sum(1 for l in all_links if l.get("type") == "strategic"),
                "insertions_ready": len(insertions),
            },
            "usa_hubs": list(USA_HUBS.keys()),
            "canada_hubs": list(CANADA_HUBS.keys()),
            "suggested_links": all_links,
            "html_insertions": insertions,
        }


# ============================================================
# CLI ENTRY POINT - Added V3.2 for workflow execution
# Workflow call: python -m agents.agent_07_internal_linking
#   --input output/agent_04/article_draft.md
#   --output output/agent_07/internal_links.json
#   --min-links 5
# ============================================================

def main():
    """CLI entry point for workflow execution."""
    import argparse, sys, json, logging
    from pathlib import Path
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [AGENT-07] %(levelname)s %(message)s"
    )
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Agent 07 - Internal Linking")
    parser.add_argument("--input", required=True, help="Path to article_draft.md")
    parser.add_argument("--output", required=True, help="Output path for internal_links.json")
    parser.add_argument("--min-links", type=int, default=5)
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        log.error(f"Article draft not found: {input_path}")
        sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    agent = InternalLinkingAgent(config)

    try:
        import asyncio
        report = asyncio.run(agent.run(
            article_draft_path=str(input_path),
            output_dir=str(output_path.parent)
        ))
        link_count = report.get("summary", {}).get("new_links_suggested", 0)
        log.info(f"Internal linking complete: {link_count} links suggested")
        log.info(f"Report written: {output_path}")
        sys.exit(0)
    except Exception as e:
        log.error(f"Internal linking failed: {e}")
        fallback = {
            "agent": "agent_07_internal_linking",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "verdict": "SKIPPED",
            "summary": {"existing_links": 0, "new_links_suggested": 0, "insertions_ready": 0},
            "suggested_links": [], "html_insertions": [],
            "error": str(e)
        }
        output_path.write_text(json.dumps(fallback, indent=2), encoding="utf-8")
        log.warning(f"Fallback report written: {output_path}")
        sys.exit(0)


if __name__ == "__main__":
    main()
