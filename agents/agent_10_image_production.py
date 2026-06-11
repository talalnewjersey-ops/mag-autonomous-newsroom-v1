"""NEXUS-14 Agent 10: Image Production Agent
MoneyAbroadGuide Autonomous Newsroom
Generates real images from prompts using Gemini Imagen / Nano Banana.
Downloads, stores, verifies quality, auto-retries on failure.
Output: generated_images/ directory"""

import asyncio, json, logging, os, re
from datetime import datetime
from pathlib import Path
from typing import Any
import aiohttp
import base64
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Supported image generation APIs
IMAGE_APIS = {
    "gemini_imagen": {
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:predict",
        "auth_header": "x-goog-api-key",
        "max_retries": 3,
        "timeout": 60,
    },
    "nano_banana": {
        "endpoint": "https://api.nanobanana.ai/v1/generate",
        "auth_header": "Authorization",
        "max_retries": 3,
        "timeout": 45,
    },
    "openai_dalle": {
        "endpoint": "https://api.openai.com/v1/images/generations",
        "auth_header": "Authorization",
        "max_retries": 3,
        "timeout": 60,
    },
}

# Quality thresholds
MIN_FILE_SIZE_BYTES = 10_000  # 10KB minimum
MAX_FILE_SIZE_BYTES = 10_000_000  # 10MB maximum
SUPPORTED_FORMATS = {"jpg", "jpeg", "png", "webp"}


class ImageProductionAgent(BaseAgent):
    """Agent 10 - Image Production. Generates, downloads, verifies images."""

    def __init__(self, config):
        super().__init__(agent_id="agent_10", name="ImageProductionAgent", config=config)
        self.gemini_api_key = config.get("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
        self.nano_banana_key = config.get("nano_banana_key", os.getenv("NANO_BANANA_KEY", ""))
        self.openai_key = config.get("openai_api_key", os.getenv("OPENAI_API_KEY", ""))
        self.preferred_api = config.get("image_api", "gemini_imagen")
        self.session = None

    async def run(self, image_prompts_path, output_dir="outputs"):
        """Generate all images from prompts JSON."""
        self.logger.info("Agent 10 - Image Production starting...")
        start_time = datetime.now()

        prompts_data = json.loads(Path(image_prompts_path).read_text(encoding="utf-8"))
        prompts = prompts_data.get("prompts", {})

        images_dir = Path(output_dir) / "generated_images"
        images_dir.mkdir(parents=True, exist_ok=True)

        results = {}
        failed = []
        async with aiohttp.ClientSession() as session:
            self.session = session

            # Generate featured image
            feat = prompts.get("featured_image")
            if feat:
                r = await self._generate_with_retry(feat, images_dir, "featured")
                results["featured_image"] = r
                if r["status"] != "SUCCESS": failed.append("featured")

            # Generate secondary images
            secondary_results = []
            for img_prompt in prompts.get("secondary_images", []):
                img_type = img_prompt.get("type", "secondary")
                r = await self._generate_with_retry(img_prompt, images_dir, img_type)
                secondary_results.append(r)
                if r["status"] != "SUCCESS": failed.append(img_type)
            results["secondary_images"] = secondary_results

            # Generate infographic
            infographic = prompts.get("infographic")
            if infographic:
                r = await self._generate_with_retry(infographic, images_dir, "infographic")
                results["infographic"] = r
                if r["status"] != "SUCCESS": failed.append("infographic")

            # Generate table visual
            table_v = prompts.get("table_visual")
            if table_v:
                r = await self._generate_with_retry(table_v, images_dir, "table_visual")
                results["table_visual"] = r
                if r["status"] != "SUCCESS": failed.append("table_visual")

        report = self._build_report(results, failed, images_dir, start_time)
        (Path(output_dir) / "image_production_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        self.logger.info("Images: {} ok, {} failed".format(
            report["summary"]["success"], report["summary"]["failed"]))
        return report

    async def _generate_with_retry(self, prompt_data, output_dir, img_type):
        """Generate image with retry logic across APIs."""
        apis_to_try = [self.preferred_api]
        # Add fallbacks
        for api in IMAGE_APIS:
            if api not in apis_to_try:
                apis_to_try.append(api)

        last_error = None
        for api_name in apis_to_try:
            api = IMAGE_APIS.get(api_name)
            if not api: continue
            key = self._get_api_key(api_name)
            if not key:
                self.logger.debug("No key for {}, skipping".format(api_name))
                continue
            for attempt in range(api["max_retries"]):
                try:
                    result = await self._call_image_api(api_name, api, key, prompt_data, output_dir, img_type)
                    if result["status"] == "SUCCESS":
                        return result
                except Exception as e:
                    last_error = str(e)
                    self.logger.warning("API {} attempt {}/{} failed: {}".format(
                        api_name, attempt+1, api["max_retries"], e))
                    await asyncio.sleep(2 ** attempt)  # exponential backoff

        # All APIs failed - generate placeholder
        return self._create_placeholder(prompt_data, output_dir, img_type, last_error)

    async def _call_image_api(self, api_name, api, key, prompt_data, output_dir, img_type):
        """Call a specific image generation API."""
        prompt = prompt_data.get("prompt", "")
        neg_prompt = prompt_data.get("negative_prompt", "")
        dims = prompt_data.get("dimensions", "800x500")
        fmt = prompt_data.get("format", "jpg")

        timeout = aiohttp.ClientTimeout(total=api["timeout"])

        if api_name == "gemini_imagen":
            payload = {
                "instances": [{"prompt": prompt}],
                "parameters": {
                    "sampleCount": 1,
                    "negativePrompt": neg_prompt,
                }
            }
            headers = {api["auth_header"]: key, "Content-Type": "application/json"}
            async with self.session.post(api["endpoint"], json=payload,
                                          headers=headers, timeout=timeout) as resp:
                if resp.status != 200:
                    raise Exception("Gemini API error: {}".format(resp.status))
                data = await resp.json()
                img_b64 = data["predictions"][0]["bytesBase64Encoded"]
                return await self._save_base64_image(
                    img_b64, output_dir, img_type, fmt, prompt_data)

        elif api_name == "openai_dalle":
            w, h = (dims.split("x") + ["512", "512"])[:2]
            size = "{}x{}".format(min(int(w), 1792), min(int(h), 1792))
            payload = {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": size,
                "quality": "standard",
                "response_format": "b64_json"
            }
            headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
            async with self.session.post(api["endpoint"], json=payload,
                                          headers=headers, timeout=timeout) as resp:
                if resp.status != 200:
                    raise Exception("DALLE API error: {}".format(resp.status))
                data = await resp.json()
                img_b64 = data["data"][0]["b64_json"]
                return await self._save_base64_image(
                    img_b64, output_dir, img_type, fmt, prompt_data)

        elif api_name == "nano_banana":
            payload = {
                "prompt": prompt,
                "negative_prompt": neg_prompt,
                "width": int(dims.split("x")[0]) if "x" in dims else 800,
                "height": int(dims.split("x")[1]) if "x" in dims else 500,
                "format": fmt,
            }
            headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
            async with self.session.post(api["endpoint"], json=payload,
                                          headers=headers, timeout=timeout) as resp:
                if resp.status != 200:
                    raise Exception("Nano Banana error: {}".format(resp.status))
                data = await resp.json()
                img_b64 = data.get("image_b64") or data.get("base64_image", "")
                return await self._save_base64_image(
                    img_b64, output_dir, img_type, fmt, prompt_data)

        raise Exception("Unknown API: {}".format(api_name))

    async def _save_base64_image(self, b64_data, output_dir, img_type, fmt, prompt_data):
        """Decode base64 image and save to disk."""
        img_bytes = base64.b64decode(b64_data)
        filename = "{}_{}.{}".format(img_type, datetime.now().strftime("%Y%m%d_%H%M%S"), fmt)
        filepath = Path(output_dir) / filename
        filepath.write_bytes(img_bytes)
        # Quality check
        size = filepath.stat().st_size
        if size < MIN_FILE_SIZE_BYTES:
            filepath.unlink()
            raise Exception("Image too small: {} bytes".format(size))
        return {
            "status": "SUCCESS",
            "type": img_type,
            "filename": filename,
            "filepath": str(filepath),
            "file_size_bytes": size,
            "format": fmt,
            "alt_text": prompt_data.get("alt_text", ""),
            "caption": prompt_data.get("caption", ""),
            "description": prompt_data.get("description", ""),
            "generated_at": datetime.now().isoformat(),
        }

    def _create_placeholder(self, prompt_data, output_dir, img_type, error):
        """Create a placeholder entry when image generation fails."""
        return {
            "status": "FAILED",
            "type": img_type,
            "filename": None,
            "filepath": None,
            "error": error,
            "alt_text": prompt_data.get("alt_text", ""),
            "caption": prompt_data.get("caption", ""),
            "prompt": prompt_data.get("prompt", "")[:200],
            "generated_at": datetime.now().isoformat(),
        }

    def _get_api_key(self, api_name):
        if api_name == "gemini_imagen": return self.gemini_api_key
        if api_name == "openai_dalle": return self.openai_key
        if api_name == "nano_banana": return self.nano_banana_key
        return None

    def _build_report(self, results, failed, images_dir, start_time):
        elapsed = (datetime.now() - start_time).total_seconds()
        all_results = []
        feat = results.get("featured_image")
        if feat: all_results.append(feat)
        all_results.extend(results.get("secondary_images", []))
        infog = results.get("infographic")
        if infog: all_results.append(infog)
        tv = results.get("table_visual")
        if tv: all_results.append(tv)

        success = sum(1 for r in all_results if r.get("status") == "SUCCESS")
        total = len(all_results)

        # Quality gate: need at least 4 images, including featured
        feat_ok = feat and feat.get("status") == "SUCCESS"
        quality_passed = success >= 4 and feat_ok

        return {
            "agent": "agent_10_image_production",
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "verdict": "PASS" if quality_passed else "FAIL",
            "quality_gate": {
                "min_4_images": success >= 4,
                "featured_image_present": bool(feat_ok),
                "passed": quality_passed,
            },
            "summary": {
                "total_attempted": total,
                "success": success,
                "failed": len(failed),
                "failed_types": failed,
                "images_directory": str(images_dir),
            },
            "results": results,
            "all_images": all_results,
        }
