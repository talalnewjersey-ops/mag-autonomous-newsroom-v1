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
    "publication_finance": {
        "style": "ultra realistic professional photography, shot with Canon EOS R5, 85mm f/1.4 lens, magazine editorial quality, modern financial publication aesthetic",
        "lighting": "professional studio lighting, soft diffused natural light, highlights on key subjects, no harsh shadows",
        "color_palette": "deep navy #1B4F72, clean white, subtle gold accents #D4AF37, minimal and sophisticated",
        "avoid": "cartoon style, AI artifacts, text overlays, clip art, thumbnail style, cheap stock photo look, low resolution appearance, watermarks",
        "quality": "photorealistic, 4K equivalent quality, ultra sharp, depth of field, professional composition",
    },
    "professional_finance": {
        "style": "ultra realistic professional photography, modern financial services, clean minimal magazine design, editorial quality",
        "lighting": "soft natural lighting, bright and airy, professional studio quality",
        "color_palette": "blues, whites, light grays, subtle gold accents",
        "avoid": "cartoon style, AI artifacts, text overlays, clutter, dark moody tones, cheap stock photo look",
        "quality": "photorealistic, magazine grade, ultra sharp, professional composition",
    },
    "expat_lifestyle": {
        "style": "ultra realistic lifestyle photography, diverse multicultural professionals, international financial services, editorial magazine quality",
        "lighting": "warm natural golden hour lighting or bright professional studio daylight",
        "color_palette": "warm sophisticated tones, natural vibrant colors, trustworthy blues",
        "avoid": "cartoon style, AI artifacts, stereotypes, single nationality representation, formal corporate stiffness",
        "quality": "photorealistic, magazine editorial grade, ultra sharp, authentic real-life feel",
    },
    "infographic": {
        "style": "clean professional flat design infographic, modern finance icons, sophisticated data visualization, magazine publication quality",
        "lighting": "flat 2D, clean white background, professional design",
        "color_palette": "brand colors: deep blue #1B4F72, accent orange #E67E22, white background, dark text",
        "avoid": "3D effects, complex gradients, too much text, amateur design, cartoon icons",
        "quality": "professional graphic design quality, clear typography, scalable vector aesthetic",
    },
    "comparison_table": {
        "style": "clean minimalist professional comparison chart design, finance publication quality, modern icons",
        "lighting": "flat clean design, crisp white background",
        "color_palette": "blue and white with green checkmarks, red crosses, professional palette",
        "avoid": "complex backgrounds, poor contrast, amateur design, illegible text",
        "quality": "professional graphic design, publication ready, clear and legible",
    },
}

# Image types required per article
REQUIRED_IMAGE_TYPES = [
    "featured_image",       # Featured: 1200x675, 16:9, publication hero image
    "comparison_graphic",   # Comparison: side-by-side comparison chart
    "checklist_graphic",    # Checklist: step-by-step visual guide
    "process_graphic",      # Process: flow diagram / how-it-works visual
    "supporting_graphic",   # Supporting: contextual lifestyle / finance image
]

# Gemini Imagen 3 publication-grade specs
# Gemini supports aspect ratios: 1:1, 3:4, 4:3, 16:9, 9:16
GEMINI_SPECS = {
    "featured_image":     {"width": 1200, "height": 675,  "aspect": "16:9", "aspect_ratio": "16:9"},
    "comparison_graphic": {"width": 1200, "height": 675,  "aspect": "16:9", "aspect_ratio": "16:9"},
    "checklist_graphic":  {"width": 800,  "height": 1200, "aspect": "2:3",  "aspect_ratio": "9:16"},
    "process_graphic":    {"width": 1200, "height": 675,  "aspect": "16:9", "aspect_ratio": "16:9"},
    "supporting_graphic": {"width": 1200, "height": 675,  "aspect": "16:9", "aspect_ratio": "16:9"},
    # Legacy types for backwards compatibility
    "section_image_1":    {"width": 1200, "height": 675,  "aspect": "16:9", "aspect_ratio": "16:9"},
    "section_image_2":    {"width": 1200, "height": 675,  "aspect": "16:9", "aspect_ratio": "16:9"},
    "section_image_3":    {"width": 1200, "height": 675,  "aspect": "16:9", "aspect_ratio": "16:9"},
    "infographic":        {"width": 800,  "height": 1200, "aspect": "2:3",  "aspect_ratio": "9:16"},
    "comparison_table":   {"width": 1200, "height": 675,  "aspect": "16:9", "aspect_ratio": "16:9"},
}

# Nano Banana compatible specs (fallback, not used in Gemini-only mode)
NANO_BANANA_SPECS = {
    "featured_image":     {"width": 1200, "height": 675,  "model": "realistic"},
    "comparison_graphic": {"width": 1200, "height": 675,  "model": "realistic"},
    "checklist_graphic":  {"width": 800,  "height": 1200, "model": "illustration"},
    "process_graphic":    {"width": 1200, "height": 675,  "model": "realistic"},
    "supporting_graphic": {"width": 1200, "height": 675,  "model": "realistic"},
    "section_image_1":    {"width": 1200, "height": 675,  "model": "realistic"},
    "section_image_2":    {"width": 1200, "height": 675,  "model": "realistic"},
    "section_image_3":    {"width": 1200, "height": 675,  "model": "realistic"},
    "infographic":        {"width": 800,  "height": 1200, "model": "illustration"},
    "comparison_table":   {"width": 1200, "height": 675,  "model": "illustration"},
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

        # 1. Featured image (1200x675, 16:9, publication hero)
        prompts["featured_image"] = self._generate_featured_prompt(meta)

        # 2. Comparison graphic (side-by-side comparison chart)
        prompts["comparison_graphic"] = self._generate_comparison_graphic_prompt(meta, article_text)

        # 3. Checklist graphic (step-by-step visual guide, 9:16 portrait)
        prompts["checklist_graphic"] = self._generate_checklist_graphic_prompt(meta, sections)

        # 4. Process graphic (how-it-works flow diagram, 16:9)
        prompts["process_graphic"] = self._generate_process_graphic_prompt(meta, sections)

        # 5. Supporting graphic (contextual lifestyle / finance image, 16:9)
        prompts["supporting_graphic"] = self._generate_supporting_graphic_prompt(meta)

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
        """Generate publication-grade featured image prompt (1200x675, 16:9)."""
        title = meta["title"]
        market = meta["market"]
        topic = meta["topic"]
        style = IMAGE_STYLES["publication_finance"]

        market_context = {
            "usa": "American financial district skyline, US flag subtly in background, diverse professionals in modern office",
            "canada": "Canadian city skyline (Toronto/Vancouver), multicultural professionals, welcoming banking environment",
            "both": "International finance hub, diverse multicultural professionals, global financial services",
        }

        topic_context = {
            "banking": "diverse newcomer professional opening bank account on laptop in modern Canadian bank branch, warm welcoming atmosphere",
            "money_transfer": "hands holding smartphone showing international money transfer app, financial connectivity",
            "credit_cards": "professional hand holding premium credit card, contactless payment terminal, modern financial lifestyle",
            "taxes": "organized tax documents, calculator, laptop on clean desk, professional tax filing environment",
            "insurance": "diverse family protected under symbolic umbrella, health insurance concept, trust and security",
            "immigration": "passport, airplane window with city view, new arrival excitement, opportunity ahead",
            "investing": "financial charts on screens, growth upward trajectory, confident investor, wealth building",
        }

        prompt = (", ".join([
            f"Ultra realistic magazine editorial hero image, financial publication quality",
            f"Subject: {topic_context.get(topic, 'diverse professional financial services scene')}",
            f"Setting: {market_context.get(market, market_context['both'])}",
            style["style"],
            style["lighting"],
            style["color_palette"],
            style["quality"],
            "No text overlays, no watermarks, no logos, pristine editorial photography",
            f"Avoid: {style['avoid']}",
        ]))

        return {
            "image_type": "featured_image",
            "prompt": prompt,
            "alt_text": f"Featured: {title[:80]}",
            "caption": f"Complete guide to {topic.replace('_', ' ')} for newcomers",
            "description": f"Publication-grade featured image for {title[:60]}",
            "keywords": [topic, market, "expat", "newcomer", "finance", "moneyabroadguide"],
            "format": "jpg",
        }

    def _generate_comparison_graphic_prompt(self, meta: dict, article_text: str) -> dict:
        """Generate comparison graphic prompt (side-by-side analysis, 16:9)."""
        topic = meta["topic"]
        style = IMAGE_STYLES["comparison_table"]
        has_table = "|" in article_text and "---" in article_text

        prompt = (", ".join([
            f"Professional financial comparison chart graphic for {topic.replace('_', ' ')} guide",
            "Ultra clean minimalist design, side-by-side comparison columns with checkmarks and feature icons",
            "Publication quality data visualization, magazine style infographic",
            "Deep blue and white color scheme, green checkmarks, clear hierarchy",
            "Professional financial publication aesthetic, no cartoon elements",
            style["quality"],
            "16:9 landscape format, suitable for featured comparison section",
            "No real data, placeholder comparison layout, clean and authoritative",
        ]))

        return {
            "image_type": "comparison_graphic",
            "prompt": prompt,
            "alt_text": f"Comparison guide: {topic.replace('_', ' ')} options for newcomers",
            "caption": f"Comparing the best {topic.replace('_', ' ')} options",
            "description": f"Professional comparison graphic for {topic} guide",
            "has_existing_table": has_table,
            "format": "png",
        }

    def _generate_checklist_graphic_prompt(self, meta: dict, sections: list) -> dict:
        """Generate checklist graphic prompt (portrait, 9:16 vertical)."""
        topic = meta["topic"]
        market = meta["market"]
        style = IMAGE_STYLES["infographic"]
        section_titles = [s["heading"] for s in sections[:5]]
        steps_text = " | ".join(section_titles[:4]) if section_titles else "Step-by-step guide"

        prompt = (", ".join([
            f"Professional checklist infographic for {topic.replace('_', ' ')} newcomer guide",
            f"Vertical portrait format, numbered checklist items with checkbox icons",
            f"Steps overview: {steps_text[:150]}",
            "Clean flat design, professional icons, modern financial publication quality",
            "Deep blue #1B4F72 headers, white background, orange #E67E22 accent checkmarks",
            style["quality"] if "quality" in style else "professional graphic design quality",
            "No text content visible (placeholder layout), clean and authoritative",
            "Magazine publication infographic style",
        ]))

        return {
            "image_type": "checklist_graphic",
            "prompt": prompt,
            "alt_text": f"Step-by-step checklist: {topic.replace('_', ' ')} guide for {market} newcomers",
            "caption": f"Complete {topic.replace('_', ' ')} checklist",
            "description": f"Visual checklist infographic for {topic} newcomer guide",
            "steps": section_titles[:5],
            "format": "png",
        }

    def _generate_process_graphic_prompt(self, meta: dict, sections: list) -> dict:
        """Generate process/flow graphic prompt (how-it-works, 16:9)."""
        topic = meta["topic"]
        market = meta["market"]
        style = IMAGE_STYLES["infographic"]
        section_titles = [s["heading"] for s in sections[:4]]
        steps_text = " → ".join(section_titles[:4]) if section_titles else "Apply → Verify → Approve → Complete"

        prompt = (", ".join([
            f"Professional process flow diagram for {topic.replace('_', ' ')} in {market}",
            f"Horizontal flow chart showing step-by-step process: {steps_text[:150]}",
            "Ultra clean flat design, numbered steps with connecting arrows, modern icons",
            "Deep navy blue and white, orange accent arrows, professional publication quality",
            "Magazine-grade data visualization, financial guide process illustration",
            "16:9 landscape format, clear left-to-right flow, no real text content",
            "Publication quality, no cartoon elements, authoritative financial aesthetic",
        ]))

        return {
            "image_type": "process_graphic",
            "prompt": prompt,
            "alt_text": f"How to {topic.replace('_', ' ')}: step-by-step process for newcomers",
            "caption": f"How the {topic.replace('_', ' ')} process works",
            "description": f"Process flow diagram for {topic} guide",
            "steps": section_titles[:4],
            "format": "png",
        }

    def _generate_supporting_graphic_prompt(self, meta: dict) -> dict:
        """Generate contextual supporting image (lifestyle/finance scene, 16:9)."""
        topic = meta["topic"]
        market = meta["market"]
        style = IMAGE_STYLES["publication_finance"]

        topic_scenes = {
            "banking": "young diverse professional smiling confidently while using banking app on phone, modern city background",
            "money_transfer": "multicultural family video calling relatives while showing phone with successful money transfer confirmation",
            "credit_cards": "professional using premium card for contactless payment at modern retail establishment",
            "taxes": "confident professional reviewing organized financial documents at clean modern desk, success feeling",
            "insurance": "diverse young family feeling secure and protected, modern home, financial peace of mind",
            "immigration": "newcomer professional arriving in new city with skyline background, hopeful and confident expression",
            "investing": "financial advisor showing growth portfolio on tablet to client, modern office setting",
        }

        canada_elements = {
            "canada": "Toronto or Vancouver skyline subtly visible, Canadian multicultural setting",
            "usa": "American financial district, US setting",
            "both": "International urban financial environment",
        }

        prompt = (", ".join([
            f"Ultra realistic lifestyle editorial photography, magazine quality",
            f"Scene: {topic_scenes.get(topic, 'diverse professionals in modern financial services environment')}",
            f"Context: {canada_elements.get(market, canada_elements['both'])}",
            style["style"],
            style["lighting"],
            style["color_palette"],
            style["quality"],
            "No text overlays, authentic real-life feel, editorial photography standard",
            f"Avoid: {style['avoid']}",
        ]))

        return {
            "image_type": "supporting_graphic",
            "prompt": prompt,
            "alt_text": f"Supporting image: {topic.replace('_', ' ')} lifestyle for {market} newcomers",
            "caption": f"Real stories: newcomers navigating {topic.replace('_', ' ')}",
            "description": f"Lifestyle supporting image for {topic} newcomer guide",
            "format": "jpg",
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
                    prompt_data["aspect_ratio"] = specs[img_type].get("aspect_ratio", specs[img_type].get("aspect", "16:9"))
                    prompt_data["model"] = "imagen-3.0-generate-002"  # Gemini Imagen 3 GA model
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
