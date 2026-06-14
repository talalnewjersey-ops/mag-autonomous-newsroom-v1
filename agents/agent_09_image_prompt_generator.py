"""
NEXUS-14 - Agent 09: Image Prompt Generator Agent
MoneyAbroadGuide Autonomous Newsroom

Creates image prompts for: Featured Image, 3 secondary images,
infographic, visual table. Compatible with Gemini and Nano Banana.
Generates: prompt, alt text, caption, description.
Output: image_prompts.json

V3.2 FIX: Removed duplicate class definition that caused SyntaxError.
"""

import json
import re
import logging
from datetime import datetime
from typing import Any
from pathlib import Path

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Image style presets for financial content
IMAGE_STYLES = {
    "professional_finance": {
        "style": "professional photography, modern financial office, clean minimal design",
        "lighting": "soft natural lighting, bright and airy",
        "color_palette": "blues, whites, light grays, subtle gold accents",
        "avoid": "text overlays, clutter, dark moody tones, cheap stock photo look",
    },
    "expat_lifestyle": {
        "style": "lifestyle photography, diverse people, international feel",
        "lighting": "warm golden hour or bright daylight",
        "color_palette": "warm tones, natural colors, vibrant",
        "avoid": "stereotypes, single nationality representation, formal corporate look",
    },
    "infographic": {
        "style": "clean flat design infographic, modern icons, data visualization",
        "lighting": "flat 2D, no shadows",
        "color_palette": "brand colors: deep blue #1B4F72, orange #E67E22, white",
        "avoid": "3D effects, complex gradients, too much text",
    },
    "comparison_table": {
        "style": "clean minimalist table design, comparison chart, icons",
        "lighting": "flat design, clean white background",
        "color_palette": "blue and white with green checkmarks and red crosses",
        "avoid": "complex backgrounds, poor contrast, illegible text",
    },
}

# Image types required per article
REQUIRED_IMAGE_TYPES = [
    "featured_image",
    "section_image_1",
    "section_image_2",
    "section_image_3",
    "infographic",
    "comparison_table",
]

# Gemini Imagen recommended resolutions
GEMINI_SPECS = {
    "featured_image": {"width": 1200, "height": 628, "aspect": "16:9"},
    "section_image_1": {"width": 800, "height": 600, "aspect": "4:3"},
    "section_image_2": {"width": 800, "height": 600, "aspect": "4:3"},
    "section_image_3": {"width": 800, "height": 600, "aspect": "4:3"},
    "infographic": {"width": 800, "height": 1200, "aspect": "2:3"},
    "comparison_table": {"width": 1000, "height": 600, "aspect": "5:3"},
}

# Nano Banana compatible specs
NANO_BANANA_SPECS = {
    "featured_image": {"width": 1200, "height": 628, "model": "realistic"},
    "section_image_1": {"width": 800, "height": 533, "model": "realistic"},
    "section_image_2": {"width": 800, "height": 533, "model": "realistic"},
    "section_image_3": {"width": 800, "height": 533, "model": "realistic"},
    "infographic": {"width": 800, "height": 1200, "model": "illustration"},
    "comparison_table": {"width": 1000, "height": 600, "model": "illustration"},
}


class ImagePromptGeneratorAgent(BaseAgent):
    """Agent 09: Automated image prompt generation for NEXUS-14."""

    def __init__(self, config: dict):
        super().__init__(agent_id="agent_09", name="ImagePromptGeneratorAgent", config=config)
        self.llm_service = None
        self.image_provider = config.get("image_provider", "gemini")
        self.site_name = config.get("site_name", "MoneyAbroadGuide.com")

    async def run(
        self,
        article_draft_path: str,
        article_outline_path: str = None,
        output_dir: str = "outputs",
    ) -> dict:
        """Generate all required image prompts for the article."""
        self.logger.info("Agent 09 - Image Prompt Generator starting...")
        start_time = datetime.now()

        draft_path = Path(article_draft_path)
        if not draft_path.exists():
            raise FileNotFoundError(f"Article draft not found: {article_draft_path}")
        article_text = draft_path.read_text(encoding="utf-8")

        # Extract article metadata
        meta = self._extract_metadata(article_text)
        self.logger.info(f"Article: {meta['title']} | Market: {meta['market']}")

        # Extract H2 sections for section images
        sections = self._extract_sections(article_text)
        self.logger.info(f"Found {len(sections)} sections")

        # Generate prompts for each image type
        prompts = {}

        # 1. Featured image
        prompts["featured_image"] = self._generate_featured_prompt(meta)

        # 2-4. Section images (3 most important sections)
        top_sections = sections[:3]
        for i, section in enumerate(top_sections):
            key = f"section_image_{i+1}"
            prompts[key] = self._generate_section_prompt(section, meta, i+1)

        # Fill missing section images if article has fewer than 3 sections
        for i in range(len(top_sections), 3):
            key = f"section_image_{i+1}"
            prompts[key] = self._generate_generic_section_prompt(meta, i+1)

        # 5. Infographic
        prompts["infographic"] = self._generate_infographic_prompt(meta, sections)

        # 6. Comparison table
        prompts["comparison_table"] = self._generate_table_prompt(meta, article_text)

        # LLM enhancement for richer prompts
        if self.llm_service:
            try:
                prompts = await self._llm_enhance_prompts(prompts, article_text, meta)
            except Exception as e:
                self.logger.warning(f"LLM prompt enhancement failed: {e}")

        # Add provider-specific specs
        final_prompts = self._add_provider_specs(prompts)

        elapsed = (datetime.now() - start_time).total_seconds()
        report = {
            "agent": "agent_09_image_prompt_generator",
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "article_title": meta["title"],
            "market": meta["market"],
            "provider": self.image_provider,
            "total_prompts": len(final_prompts),
            "required_types": REQUIRED_IMAGE_TYPES,
            "prompts": final_prompts,
        }

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "image_prompts.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self.logger.info(f"Image prompts generated: {len(final_prompts)} prompts")
        return report

    def _extract_metadata(self, text: str) -> dict:
        meta = {
            "title": "",
            "market": "both",
            "topic": "",
            "keywords": [],
        }
        lines = text.split("\n")[:10]
        for line in lines:
            if line.startswith("#") and not meta["title"]:
                meta["title"] = line.lstrip("#").strip()
                break
        if not meta["title"] and lines:
            meta["title"] = lines[0].strip()[:100]
        usa_signals = len(re.findall(r"\b(usa|united states|american|irs|fdic)\b", text.lower()))
        canada_signals = len(re.findall(r"\b(canada|canadian|cra|rrsp|tfsa)\b", text.lower()))
        if usa_signals > canada_signals * 1.5:
            meta["market"] = "usa"
        elif canada_signals > usa_signals * 1.5:
            meta["market"] = "canada"
        meta["topic"] = self._infer_topic(text)
        return meta

    def _infer_topic(self, text: str) -> str:
        text_lower = text.lower()
        topics = {
            "banking": ["bank account", "checking", "savings account", "banking"],
            "money_transfer": ["transfer", "send money", "remittance", "wire transfer"],
            "credit_cards": ["credit card", "rewards", "cashback", "points"],
            "taxes": ["tax", "irs", "cra", "filing", "return"],
            "insurance": ["insurance", "coverage", "policy", "premium"],
            "immigration": ["visa", "immigration", "permit", "pr", "citizenship"],
            "investing": ["invest", "portfolio", "etf", "rrsp", "401k"],
        }
        scores = {topic: sum(1 for kw in kws if kw in text_lower) for topic, kws in topics.items()}
        return max(scores, key=scores.get) if max(scores.values()) > 0 else "general_finance"

    def _extract_sections(self, text: str) -> list:
        sections = []
        h2_pattern = r"^##\s+(.+)$"
        lines = text.split("\n")
        current_section = None
        current_content = []
        for line in lines:
            h2_match = re.match(h2_pattern, line)
            if h2_match:
                if current_section:
                    sections.append({"heading": current_section, "content": " ".join(current_content)[:300]})
                current_section = h2_match.group(1).strip()
                current_content = []
            elif current_section and line.strip():
                current_content.append(line.strip())
        if current_section:
            sections.append({"heading": current_section, "content": " ".join(current_content)[:300]})
        return sections

    def _generate_featured_prompt(self, meta: dict) -> dict:
        title = meta["title"]
        market = meta["market"]
        topic = meta["topic"]
        style = IMAGE_STYLES["expat_lifestyle" if market != "both" else "professional_finance"]

        market_context = {
            "usa": "American city skyline or US financial district, dollar bills subtly visible",
            "canada": "Canadian city (Toronto/Vancouver/Montreal), maple leaf subtly visible",
            "both": "International finance concept, globe or world map, diverse professionals",
        }

        topic_context = {
            "banking": "person opening bank account on laptop or phone, modern bank lobby",
            "money_transfer": "smartphone showing money transfer app, international connections",
            "credit_cards": "credit cards fanned out, contactless payment",
            "taxes": "tax forms, calculator, filing documents organized neatly",
            "insurance": "umbrella protection concept, family security",
            "immigration": "passport, airplane, new country arrival",
            "investing": "stock charts, growth arrows, financial planning",
        }

        prompt = (",".join([
            f"Featured image for article: {title[:60]}",
            market_context.get(market, market_context["both"]),
            topic_context.get(topic, "professional financial services"),
            style["style"],
            style["lighting"],
            style["color_palette"],
            "No text or watermarks, high quality, editorial style",
            f"avoid: {style['avoid']}",
        ]))

        return {
            "image_type": "featured_image",
            "prompt": prompt,
            "alt_text": f"Featured image: {title[:80]}",
            "caption": f"Guide to {topic.replace('_', ' ')} for expats",
            "description": f"Featured image for {title[:60]}. Shows {topic_context.get(topic, 'finance concept')}",
            "keywords": [topic, market, "expat", "finance", "moneyabroadguide"],
        }

    def _generate_section_prompt(self, section: dict, meta: dict, number: int) -> dict:
        heading = section["heading"]
        content_preview = section["content"][:100]
        style = IMAGE_STYLES["professional_finance"]

        prompt = (",".join([
            f"Section image {number} for: {heading[:60]}",
            f"Topic context: {content_preview[:80]}",
            style["style"],
            style["lighting"],
            "Clean professional look, suitable for financial blog",
            "No text overlays, editorial photography style",
        ]))

        return {
            "image_type": f"section_image_{number}",
            "section_heading": heading,
            "prompt": prompt,
            "alt_text": f"Image for: {heading[:80]}",
            "caption": heading,
            "description": f"Section image for: {heading}",
        }

    def _generate_generic_section_prompt(self, meta: dict, number: int) -> dict:
        style = IMAGE_STYLES["professional_finance"]
        prompt = (",".join([
            f"Generic section image {number} for financial article",
            f"Topic: {meta['topic'].replace('_', ' ')}",
            f"Market: {meta['market']}",
            style["style"],
            style["lighting"],
            "Professional financial content imagery",
        ]))
        return {
            "image_type": f"section_image_{number}",
            "section_heading": f"Section {number}",
            "prompt": prompt,
            "alt_text": f"Financial guide section {number} image",
            "caption": meta["topic"].replace("_", " ").title(),
            "description": f"Section image {number}",
        }

    def _generate_infographic_prompt(self, meta: dict, sections: list) -> dict:
        style = IMAGE_STYLES["infographic"]
        section_titles = [s["heading"] for s in sections[:6]]
        steps_text = " | ".join(section_titles[:4]) if section_titles else "Key Steps"

        prompt = (",".join([
            f"Infographic: How to {meta['topic'].replace('_', ' ')} for {meta['market']} expats",
            f"Flow diagram with steps: {steps_text}",
            style["style"],
            "Icons for each step, numbered sequence, arrows connecting steps",
            style["color_palette"],
            "Tall vertical format (2:3), print-quality",
        ]))

        return {
            "image_type": "infographic",
            "prompt": prompt,
            "alt_text": f"Infographic: {meta['topic'].replace('_', ' ')} guide for {meta['market']} expats",
            "caption": f"Step-by-step {meta['topic'].replace('_', ' ')} guide",
            "description": f"Visual infographic showing {meta['topic']} process",
            "steps": section_titles[:6],
        }

    def _generate_table_prompt(self, meta: dict, article_text: str) -> dict:
        style = IMAGE_STYLES["comparison_table"]
        has_table = "|" in article_text and "---" in article_text

        prompt = (",".join([
            f"Comparison table visual: {meta['topic'].replace('_', ' ')} options for {meta['market']}",
            "Clean minimalist comparison table with checkmarks and crosses",
            "3-4 columns, 5-6 rows of data",
            style["style"],
            style["color_palette"],
            "Professional data visualization, no real data shown",
        ]))

        return {
            "image_type": "comparison_table",
            "prompt": prompt,
            "alt_text": f"Comparison table: {meta['topic'].replace('_', ' ')} options",
            "caption": f"Comparing {meta['topic'].replace('_', ' ')} options",
            "description": f"Visual comparison table for {meta['topic']} choices",
            "has_existing_table": has_table,
        }

    async def _llm_enhance_prompts(self, prompts: dict, article_text: str, meta: dict) -> dict:
        title = meta["title"]
        existing = json.dumps({k: v.get("prompt", "")[:100] for k, v in prompts.items()}, indent=2)
        llm_prompt = (
            f"You are an image prompt expert for {self.site_name}.\n"
            f"Article: {title}\nTopic: {meta['topic']}\nMarket: {meta['market']}\n\n"
            "Enhance these prompts to be more specific and photorealistic:\n"
            f"{existing}\n\n"
            "Return JSON with same keys, enhanced prompts only."
        )
        response = await self.llm_service.complete(llm_prompt, max_tokens=1200)
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            enhanced = json.loads(response[start:end])
            for key, enhanced_prompt in enhanced.items():
                if key in prompts and isinstance(enhanced_prompt, str) and len(enhanced_prompt) > 50:
                    prompts[key]["prompt"] = enhanced_prompt
        except Exception as e:
            self.logger.warning(f"LLM prompt enhancement parse error: {e}")
        return prompts

    def _add_provider_specs(self, prompts: dict) -> dict:
        specs = GEMINI_SPECS if self.image_provider == "gemini" else NANO_BANANA_SPECS
        for img_type, prompt_data in prompts.items():
            if img_type in specs:
                prompt_data["provider"] = self.image_provider
                prompt_data["width"] = specs[img_type]["width"]
                prompt_data["height"] = specs[img_type]["height"]
                if self.image_provider == "gemini":
                    prompt_data["aspect_ratio"] = specs[img_type].get("aspect", "16:9")
                    prompt_data["model"] = "imagen-3.0-generate-001"
                else:
                    prompt_data["model"] = specs[img_type].get("model", "realistic")
                    prompt_data["steps"] = 30
                    prompt_data["guidance_scale"] = 7.5
        return prompts


# ============================================================
# CLI ENTRY POINT
# Workflow: python -m agents.agent_09_image_prompt_generator
# --input output/agent_04/article_draft.md
# --output output/agent_09/image_prompts.json
# --count 5
# ============================================================

def main():
    """CLI entry point for workflow execution."""
    import argparse, sys, json, logging
    from pathlib import Path
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [AGENT-09] %(levelname)s %(message)s"
    )
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Agent 09 - Image Prompt Generator")
    parser.add_argument("--input", required=True, help="Path to article_draft.md")
    parser.add_argument("--output", required=True, help="Output path for image_prompts.json")
    parser.add_argument("--count", type=int, default=5, help="Number of images to generate prompts for")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        log.error(f"Article draft not found: {input_path}")
        sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config = {"image_count": args.count}
    agent = ImagePromptGeneratorAgent(config)

    try:
        import asyncio
        result = asyncio.run(agent.run(
            article_draft_path=str(input_path),
            output_dir=str(output_path.parent)
        ))
        prompts = result.get("prompts", result.get("image_prompts", []))
        log.info(f"Image prompts generated: {len(prompts)}")
        log.info(f"Report written: {output_path}")
        sys.exit(0)
    except Exception as e:
        log.error(f"Image prompt generation failed: {e}")
        # Create fallback prompts so pipeline can continue
        fallback_prompts = [
            {"id": f"img_{i+1}", "title": f"Article Image {i+1}",
             "prompt": "Professional financial concept image with charts and graphs, blue color scheme",
             "style": "photorealistic", "aspect_ratio": "16:9"}
            for i in range(args.count)
        ]
        fallback = {
            "agent": "agent_09_image_prompt_generator",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "status": "FALLBACK",
            "prompts": fallback_prompts,
            "image_count": args.count,
            "error": str(e)
        }
        output_path.write_text(json.dumps(fallback, indent=2), encoding="utf-8")
        log.warning(f"Fallback prompts written: {output_path}")
        sys.exit(0)


if __name__ == "__main__":
    main()
