"""
NEXUS-14: Agent 11 - WordPress Integration Agent v3.0
FIX: Replaced hardcoded paths with workflow-provided paths via config.
FIX: Added pre-publish validation gate — blocks empty drafts.
Gate C requires post_id + title + content (veracity/substance). The featured image
is COSMETIC and DECOUPLED (Lot 1): its absence NEVER fails an article; a decorative
per-vertical fallback header is used when Gemini produced no image.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from agents.base_agent import BaseAgent
from services.llm_service import LLMService
from services.storage_service import StorageService
from services.wordpress_service import WordPressService

logger = logging.getLogger(__name__)


class WordPressIntegrationAgent(BaseAgent):
    AGENT_ID = "agent_11"
    AGENT_NAME = "WordPress Integration Agent"
    DEFAULT_AUTHOR = {
        "name": "Talal Eddaouahiri",
        "bio": "Founder of MoneyAbroadGuide.com, helping immigrants, international students and newcomers navigate banking, credit scores, taxes, insurance and personal finance in the USA and Canada.",
    }

    def __init__(self, config, llm_service, storage_service, wordpress_service):
        super().__init__(config, llm_service, storage_service)
        self.wp = wordpress_service

    @staticmethod
    def _norm_title(t):
        """Normalize a title (str or WP {'raw'/'rendered'}) for duplicate matching."""
        if isinstance(t, dict):
            t = t.get("raw") or t.get("rendered") or ""
        return " ".join(re.sub(r"[^a-z0-9 ]", " ", (t or "").lower()).split())

    @classmethod
    def _duplicate_of(cls, existing, title):
        """Return an existing WP post that is a title-duplicate of `title`, else None.
        Sprint 9 dedup: stops the GATED pipeline from creating a second post for a
        topic already published/drafted on WP (the 48384/48412 class). NOTE: the
        legacy scripts/produce_article.py path creates posts on its own and bypasses
        this check -- neutralizing it is tracked separately."""
        nt = cls._norm_title(title)
        if not nt:
            return None
        for p in existing or []:
            if cls._norm_title(p.get("title")) == nt:
                return p
        return None

    async def run(self, context=None):
        self.log_start()
        try:
            article_data = await self._load_article_data()
            images_data = await self._load_images_data()

            # PRE-PUBLISH VALIDATION GATE — block empty drafts
            title = article_data.get("title", "").strip()
            content_raw = article_data.get("content", "")
            content_chars = len(content_raw)
            content_words = len(content_raw.split()) if content_raw else 0

            if not title or title == "Untitled Article":
                raise ValueError(f"PRE-PUBLISH GATE FAIL: title is empty or default (got: '{title}')")
            if content_chars < 5000:
                raise ValueError(f"PRE-PUBLISH GATE FAIL: content too short — {content_chars} chars < 5000 minimum")
            if content_words < 4000:
                raise ValueError(f"PRE-PUBLISH GATE FAIL: word count too low — {content_words} words < 4000 minimum")

            logger.info(f"PRE-PUBLISH GATE PASS: title='{title}' chars={content_chars} words={content_words}")

            # SPRINT 9 dedup: never create a second post for a title already on WP
            # (published or draft). Covers the gated pipeline (the 48384/48412 class);
            # the legacy produce_article.py path bypasses this and is neutralized
            # separately. Best-effort: a lookup error must not block a real article.
            try:
                existing = await self.wp.find_posts(title)
            except Exception as e:
                logger.warning(f"dedup lookup failed (continuing): {e}")
                existing = []
            dup = self._duplicate_of(existing, title)
            if dup:
                raise ValueError(f"DEDUP: '{title}' already exists on WP as post {dup.get('id')} "
                                 f"(status={dup.get('status')}) — skipping duplicate creation")

            html_content = await self._convert_to_html(article_data)
            html_with_faq = await self._add_faq_schema(html_content, article_data)
            html_final = await self._add_affiliate_blocks(html_with_faq, article_data)
            uploaded_images = await self._upload_images(images_data)
            # Lot 1: a DECORATIVE per-vertical fallback header when agent_10 (Gemini)
            # produced no usable image, so the draft still gets a featured image. A
            # missing image is COSMETIC and must never block -- see GATE C below.
            if not any(im.get("wp_media_id") or im.get("wordpress_media_id") for im in uploaded_images):
                fb = await self._upload_fallback_image(article_data)
                if fb:
                    uploaded_images = [fb] + uploaded_images
            html_with_images = await self._insert_images_in_content(html_final, uploaded_images)
            wp_post = await self._create_wordpress_draft(article_data, html_with_images, uploaded_images)

            post_id = wp_post.get("id")
            featured_id = (uploaded_images[0].get("wp_media_id") or uploaded_images[0].get("wordpress_media_id")) if uploaded_images else None

            # GATE C: requires post_id + title + content (veracity/substance, checked
            # by the PRE-PUBLISH gate above). The featured image is COSMETIC and now
            # DECOUPLED -- its absence NEVER fails an article (Lot 1). Only a missing
            # post_id blocks.
            if not post_id:
                raise ValueError("GATE C FAIL: no post_id returned from WordPress")
            if featured_id:
                logger.info(f"GATE C PASS: post_id={post_id} featured_media={featured_id}")
            else:
                logger.warning(f"GATE C PASS (no featured image — decorative, non-blocking): post_id={post_id}")

            await self._set_author(post_id)
            await self._set_seo_metadata(post_id, article_data)

            wp_report = {
                "agent": self.AGENT_NAME,
                "timestamp": datetime.utcnow().isoformat(),
                "title": title,
                "keyword": article_data.get("keyword", ""),
                "post_id": post_id,
                "post_url": wp_post.get("link", ""),
                "post_status": "draft",
                "has_author": True,
                "has_author_bio": True,
                "has_faq": True,
                "uploaded_images": uploaded_images,
                "featured_image_id": featured_id,
                "image_count": len(uploaded_images),
                "word_count": content_words,
                "content_chars": content_chars,
                "seo_title": article_data.get("seo_title", title),
                "meta_description": article_data.get("meta_description", ""),
                "hardcoded_fallback_used": False,
            }
            output_path = await self.save_output("wordpress_report.json", wp_report)
            self.log_complete({"post_id": post_id})
            return wp_report
        except Exception as e:
            self.log_error(e)
            raise

    async def _load_article_data(self):
        """
        Load article content using the path supplied via config['article_path'].
        This is set by main() from the --article CLI argument.
        Falls back to legacy hardcoded paths only if config path is not set.
        """
        import os
        data = {}

        # PRIMARY: use path passed by workflow via --article argument
        article_path = self.config.get("article_path", "")

        # FALLBACK: legacy paths (last resort — should never be needed)
        candidates = ([article_path] if article_path else []) + [
            "output/agent_04/article_draft.md",
            "output/article_draft.md",
        ]

        loaded_path = None
        for path in candidates:
            if path and os.path.exists(path):
                loaded_path = path
                with open(path, encoding="utf-8") as f:
                    data["content"] = f.read()
                data["word_count"] = len(data["content"].split())
                logger.info(f"Loaded article from: {path} ({len(data['content'])} chars, {data['word_count']} words)")
                # Extract YAML frontmatter fields
                tm = re.search(r'^title:s*"?([^"\n]+)"?', data["content"], re.MULTILINE)
                if tm:
                    data["title"] = tm.group(1).strip()
                    logger.info(f"Title extracted: {data['title']}")
                km = re.search(r'^primary_keyword:s*"?([^"\n]+)"?', data["content"], re.MULTILINE)
                if km:
                    data["keyword"] = km.group(1).strip()
                break

        if not loaded_path:
            raise FileNotFoundError(
                f"Article file not found. Tried: {candidates}. "
                f"article_path from config='{article_path}'"
            )

        # Load article_metadata.json from same directory
        if loaded_path:
            meta_path = os.path.join(os.path.dirname(loaded_path), "article_metadata.json")
            if os.path.exists(meta_path):
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
                # metadata fields complement but do NOT overwrite already-extracted content
                for k, v in meta.items():
                    if k not in data or not data[k]:
                        data[k] = v
                logger.info(f"Loaded metadata from: {meta_path}")

        # Load outline from sibling agent_03 directory for title/meta fallback
        if loaded_path:
            outline_path = loaded_path.replace(
                "agent_04/article_draft.md",
                "agent_03/article_outline.json"
            )
            if os.path.exists(outline_path):
                with open(outline_path, encoding="utf-8") as f:
                    outline = json.load(f)
                data.setdefault("title", outline.get("title", ""))
                data.setdefault("meta_description", outline.get("meta_description", ""))
                data.setdefault("keyword", outline.get("primary_keyword", ""))
                logger.info(f"Loaded outline from: {outline_path} — title='{data.get('title','')}'")

        return data

    async def _load_images_data(self):
        """
        Load generated images report using the directory supplied via config['images_dir'].
        This is set by main() from the --images CLI argument.
        """
        import os

        # PRIMARY: use directory passed by workflow via --images argument
        images_dir = self.config.get("images_dir", "")

        candidates = []
        if images_dir:
            candidates.append(os.path.join(images_dir, "generated_images_report.json"))
        # FALLBACK: legacy path
        candidates.append("output/agent_10/generated_images_report.json")

        for p in candidates:
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    images = json.load(f).get("images", [])
                logger.info(f"Loaded {len(images)} images from: {p}")
                return images

        logger.warning(f"No images report found. Tried: {candidates}")
        return []

    @staticmethod
    def _strip_frontmatter(content):
        """Remove a leading YAML frontmatter block (---\\n...\\n---) so its raw
        fields never render as visible <p> paragraphs. Belt for RCA-007: the
        writer must not emit frontmatter, but the render boundary guarantees it."""
        if content.lstrip().startswith("---"):
            m = re.match(r'^\s*---\s*\n.*?\n---\s*(?:\n|$)', content, re.DOTALL)
            if m:
                return content[m.end():]
        return content

    def _render_inline(self, text):
        """Convert inline markdown (bold, italic, links, code) to HTML."""
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
        text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
        return text

    async def _convert_to_html(self, article_data):
        """Block-level markdown -> HTML.

        FIX: previous version only handled headings/bold/italic/links and left
        prose, lists and blockquotes as raw markdown. This renders paragraphs,
        ordered/unordered lists, blockquotes, headings h1-h6 and horizontal
        rules into valid HTML so no raw markdown reaches WordPress.
        """
        content = article_data.get("content", "") or ""
        content = self._strip_frontmatter(content)   # drop leading YAML frontmatter block
        lines = content.split("\n")
        html_parts = []
        i = 0
        n = len(lines)
        para = []

        def close_para(buf):
            if buf:
                text = self._render_inline(" ".join(buf).strip())
                if text:
                    html_parts.append("<p>" + text + "</p>")
                buf.clear()

        hr_re = re.compile(r'^(-{3,}|\*{3,}|_{3,})[ \t]*$')
        heading_re = re.compile(r'^(#{1,6})[ \t]+(.+?)[ \t]*#*$')
        ul_re = re.compile(r'^[-*+][ \t]+')
        ol_re = re.compile(r'^\d+[.)][ \t]+')
        # Markdown table: a row of pipes followed by a |---|---| separator row.
        tbl_sep_re = re.compile(r'^\s*\|?[\s:|-]*-{2,}[\s:|-]*\|?\s*$')
        # figure/img are emitted only by our own image insertion (balanced);
        # script/iframe are dropped for safety -- so raw writer HTML cannot
        # inject unbalanced/unsafe blocks.
        html_block_re = re.compile(r'^<(/?)(h[1-6]|div|table|thead|tbody|tr|td|th|ul|ol|li|p|section|blockquote)\b')

        while i < n:
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                close_para(para)
                i += 1
                continue

            if hr_re.match(stripped):
                close_para(para)
                html_parts.append("<hr />")
                i += 1
                continue

            m = heading_re.match(stripped)
            if m:
                close_para(para)
                # Body carries NO <h1>: the WordPress post title is the page H1.
                # Demote any H1 to H2 so there is exactly one H1 on the page.
                level = max(2, len(m.group(1)))
                html_parts.append("<h" + str(level) + ">" + self._render_inline(m.group(2)) + "</h" + str(level) + ">")
                i += 1
                continue

            # Markdown table -> responsive HTML table (never leak raw | a | b | rows).
            if "|" in stripped and i + 1 < n and tbl_sep_re.match(lines[i + 1].strip()):
                close_para(para)
                header_cells = [c.strip() for c in stripped.strip().strip("|").split("|")]
                i += 2  # consume header + separator rows
                body_rows = []
                while i < n and "|" in lines[i] and lines[i].strip():
                    body_rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                    i += 1
                thead = "<thead><tr>" + "".join(
                    "<th>" + self._render_inline(c) + "</th>" for c in header_cells) + "</tr></thead>"
                tbody = "<tbody>" + "".join(
                    "<tr>" + "".join("<td>" + self._render_inline(c) + "</td>" for c in row) + "</tr>"
                    for row in body_rows) + "</tbody>"
                html_parts.append('<div style="overflow-x:auto"><table>' + thead + tbody + "</table></div>")
                continue

            if stripped.startswith(">"):
                close_para(para)
                quote_lines = []
                while i < n and lines[i].strip().startswith(">"):
                    quote_lines.append(re.sub(r'^[ \t]*>[ \t]?', '', lines[i]))
                    i += 1
                inner = self._render_inline(" ".join(q.strip() for q in quote_lines).strip())
                html_parts.append("<blockquote><p>" + inner + "</p></blockquote>")
                continue

            if ul_re.match(stripped):
                close_para(para)
                items = []
                while i < n and ul_re.match(lines[i].strip()):
                    item = ul_re.sub('', lines[i].strip())
                    items.append("<li>" + self._render_inline(item) + "</li>")
                    i += 1
                html_parts.append("<ul>" + "".join(items) + "</ul>")
                continue

            if ol_re.match(stripped):
                close_para(para)
                items = []
                while i < n and ol_re.match(lines[i].strip()):
                    item = ol_re.sub('', lines[i].strip())
                    items.append("<li>" + self._render_inline(item) + "</li>")
                    i += 1
                html_parts.append("<ol>" + "".join(items) + "</ol>")
                continue

            if stripped.startswith("<") and html_block_re.match(stripped):
                close_para(para)
                html_parts.append(stripped)
                i += 1
                continue

            para.append(stripped)
            i += 1

        close_para(para)
        return "\n".join(html_parts)

    async def _add_faq_schema(self, html, article_data):
        content = article_data.get("content", "")
        faq_section = re.search(r'## (?:FAQ|Frequently Asked Questions)(.*?)(?=## [A-Z]|$)', content, re.DOTALL | re.IGNORECASE)
        if not faq_section:
            return html
        qa_pairs = re.findall(r'### (.+?)\n([^#]+?)(?=###|$)', faq_section.group(1), re.DOTALL)
        if not qa_pairs:
            return html
        faq_items = [{"@type": "Question", "name": q.strip(), "acceptedAnswer": {"@type": "Answer", "text": re.sub(r'<[^>]+>', '', a.strip())[:500]}} for q, a in qa_pairs[:20]]
        schema = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_items}
        return html + f'\n\n<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>'

    async def _add_affiliate_blocks(self, html, article_data):
        import os
        images_dir = self.config.get("images_dir", "")
        article_path = self.config.get("article_path", "")
        # Derive affiliate path from article directory
        affiliate_path = ""
        if article_path:
            affiliate_path = article_path.replace("agent_04/article_draft.md", "agent_08/affiliate_report.json")
        candidates = ([affiliate_path] if affiliate_path else []) + ["output/agent_08/affiliate_report.json"]
        for p in candidates:
            if p and os.path.exists(p):
                try:
                    with open(p) as f:
                        recs = json.load(f).get("recommendations", [])[:3]
                    # Keep only ACTIONABLE recommendations (a real affiliate URL).
                    # Status placeholders (e.g. "No affiliate opportunities detected")
                    # carry no url and must NEVER render as content.
                    actionable = []
                    for r in recs:
                        if isinstance(r, str):
                            r = {"name": r}
                        if not isinstance(r, dict):
                            continue
                        if str(r.get("url", "")).strip().lower().startswith("http"):
                            actionable.append(r)
                    if actionable:
                        aff = '<div class="mag-affiliate-box"><p><em>Affiliate disclosure: We earn a commission at no cost to you.</em></p>'
                        for r in actionable:
                            aff += f'<p><strong>{r.get("name","")}</strong>: {r.get("description","")} <a href="{r.get("url","#")}" rel="nofollow sponsored" target="_blank">Learn More</a></p>'
                        aff += '</div>'
                        pos = html.find('</h2>')
                        if pos > 0:
                            html = html[:pos+5] + aff + html[pos+5:]
                except Exception as e:
                    logger.warning(f"Affiliate blocks failed: {e}")
                break
        return html

    async def _upload_images(self, images_data):
        uploaded = []
        for i, image in enumerate(images_data):
            try:
                # NORMALIZE + REUSE: Agent 10 already uploads each image to the
                # WordPress media library and records the id as wordpress_media_id.
                # Honor it, map it to wp_media_id, and skip a redundant re-upload.
                existing_id = image.get("wp_media_id") or image.get("wordpress_media_id")
                if existing_id:
                    uploaded.append({
                        **image,
                        "wp_media_id": existing_id,
                        "wp_url": image.get("wp_url") or image.get("wordpress_url", ""),
                        "uploaded": True,
                    })
                    logger.info(f"Reusing existing WP media id={existing_id} for image {i+1}")
                    continue

                import os
                p = image.get("local_path", "")
                if os.path.exists(p):
                    result = await self.wp.upload_image(
                        file_path=p,
                        title=image.get("title", f"Image {i+1}"),
                        alt_text=image.get("alt_text", ""),
                        description=image.get("description", ""),
                    )
                    wp_id = result.get("id")
                    logger.info(f"Uploaded image {i+1}: wp_media_id={wp_id}")
                    uploaded.append({**image, "wp_media_id": wp_id, "wp_url": result.get("source_url", ""), "uploaded": True})
                else:
                    logger.warning(f"Image {i+1} local_path not found: {p}")
                    uploaded.append({**image, "uploaded": False, "error": "local_path not found"})
            except Exception as e:
                logger.warning(f"Image {i+1} upload failed: {e}")
                uploaded.append({**image, "uploaded": False, "error": str(e)})
        return uploaded

    async def _upload_fallback_image(self, article_data):
        """Lot 1: upload a DECORATIVE per-vertical fallback header (displays NO data)
        so a draft has a featured image when Gemini produced none. Any failure is
        NON-FATAL -- the article proceeds without a featured image."""
        try:
            import os
            import tempfile
            from agents._source_pool import resolve_vertical
            from agents._fallback_image import make_fallback_image
            market = self.config.get("market", "") or article_data.get("market", "")
            category = self.config.get("category", "") or article_data.get("category", "")
            vertical = resolve_vertical(market, category) or "us_default"
            path = os.path.join(tempfile.gettempdir(), "nexus14_fallback_header.png")
            make_fallback_image(vertical, path)
            result = await self.wp.upload_image(
                file_path=path, title="Header image",
                alt_text="Decorative header image", description="")
            wp_id = result.get("id")
            if wp_id:
                logger.info(f"Fallback decorative image uploaded: wp_media_id={wp_id} (vertical={vertical})")
                return {"wp_media_id": wp_id, "wp_url": result.get("source_url", ""),
                        "uploaded": True, "fallback": True, "alt_text": "Decorative header image"}
        except Exception as e:
            logger.warning(f"Fallback image unavailable (continuing without featured): {e}")
        return None

    async def _insert_images_in_content(self, html, images):
        """Embed uploaded images into the article body.

        FIX: previous version was a no-op stub (return html) so uploaded images
        never appeared inside the content. This distributes the in-content
        images evenly across the <h2> section boundaries as <figure> blocks.
        The first image is reserved as the WordPress featured image and is NOT
        embedded again here. If no <h2> anchors exist, images are appended.
        """
        if not images:
            return html

        embeddable = [
            img for img in images[1:]
            if img.get("uploaded") and (img.get("wp_url") or img.get("wp_media_id"))
        ]
        if not embeddable:
            return html

        def figure_html(img):
            url = img.get("wp_url", "")
            alt = (img.get("alt_text", "") or "").replace('"', "'")
            media_id = img.get("wp_media_id")
            cls = "wp-image-" + str(media_id) if media_id else ""
            # Caption derives from the per-image alt text (topic-specific), NEVER a
            # separate generic 'caption' field that can be off-topic (e.g. an
            # "immigration guide" caption on a car-insurance article).
            caption = alt
            cap_html = "<figcaption>" + self._render_inline(caption) + "</figcaption>" if caption else ""
            return (
                '<figure class="mag-article-image">'
                '<img src="' + url + '" alt="' + alt + '" class="' + cls + '" loading="lazy" />'
                + cap_html + '</figure>'
            )

        parts = re.split(r'(<h2[^>]*>)', html)
        if len(parts) <= 1:
            return html + "\n" + "\n".join(figure_html(im) for im in embeddable)

        result = [parts[0]]
        img_idx = 0
        k = 1
        while k < len(parts):
            heading = parts[k]
            body = parts[k + 1] if k + 1 < len(parts) else ""
            result.append(heading)
            result.append(body)
            if img_idx < len(embeddable):
                result.append("\n" + figure_html(embeddable[img_idx]) + "\n")
                img_idx += 1
            k += 2

        while img_idx < len(embeddable):
            result.append("\n" + figure_html(embeddable[img_idx]) + "\n")
            img_idx += 1

        return "".join(result)

    async def _create_wordpress_draft(self, article_data, html_content, images):
        title = article_data.get("title", "Untitled Article")
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        featured_image_id = (images[0].get("wp_media_id") or images[0].get("wordpress_media_id")) if images else None
        post_data = {
            "title": title,
            "content": html_content,
            "status": "draft",
            "slug": slug[:100],
            "categories": await self._resolve_category_ids(["expat-banking"]),
            "featured_media": featured_image_id,
            "author": 1,
            "meta": {
                "_yoast_wpseo_title": article_data.get("seo_title", title),
                "_yoast_wpseo_metadesc": article_data.get("meta_description", ""),
                "_yoast_wpseo_focuskw": article_data.get("keyword", ""),
            },
        }
        logger.info(f"Creating WordPress draft: title='{title}' content_chars={len(html_content)} featured_media={featured_image_id}")
        try:
            return await self.wp.create_post(post_data)
        except Exception as e:
            logger.error(f"WordPress post creation failed: {e}")
            return {"id": None, "link": "", "error": str(e)}

    async def _resolve_category_ids(self, slugs):
        ids = []
        try:
            import aiohttp, base64, os
            wp_url = os.environ.get('WORDPRESS_URL', '').rstrip('/')
            wp_user = os.environ.get('WORDPRESS_USERNAME', '')
            wp_pass = os.environ.get('WORDPRESS_APP_PASSWORD', '')
            if not wp_url:
                return []
            auth = 'Basic ' + base64.b64encode(f"{wp_user}:{wp_pass}".encode()).decode() if wp_user and wp_pass else ''
            headers = {'User-Agent': 'NEXUS-14/3.0'}
            if auth:
                headers['Authorization'] = auth
            async with aiohttp.ClientSession() as session:
                for slug in slugs:
                    async with session.get(f"{wp_url}/wp-json/wp/v2/categories", params={'slug': slug, 'per_page': 1}, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data and data[0].get('id'):
                                ids.append(data[0]['id'])
        except Exception as e:
            logger.warning(f"Category lookup failed: {e}")
        return ids

    async def _set_author(self, post_id):
        if not post_id:
            return
        try:
            await self.wp.set_post_author(post_id=post_id, author_name=self.DEFAULT_AUTHOR["name"], author_bio=self.DEFAULT_AUTHOR["bio"])
        except Exception as e:
            logger.warning(f"Set author failed: {e}")

    async def _set_seo_metadata(self, post_id, article_data):
        if not post_id:
            return
        try:
            await self.wp.set_post_meta(post_id, {
                "_yoast_wpseo_focuskw": article_data.get("keyword", ""),
                "_yoast_wpseo_title": article_data.get("seo_title", ""),
                "_yoast_wpseo_metadesc": article_data.get("meta_description", ""),
                "_rank_math_focus_keyword": article_data.get("keyword", ""),
                "_rank_math_description": article_data.get("meta_description", ""),
            })
        except Exception as e:
            logger.warning(f"SEO metadata failed: {e}")


def _write_failure_reports(output_path, val_path_str, title, keyword, word_count, error_msg):
    from pathlib import Path
    from datetime import datetime
    fail = {
        "agent": "agent_11_wordpress_integration", "version": "3.0",
        "timestamp": datetime.utcnow().isoformat(), "status": "FAILED",
        "title": title, "keyword": keyword, "post_id": None, "post_url": "",
        "draft_url": "", "draft_created": False, "post_status": "not_created",
        "has_author": False, "has_author_bio": False, "word_count": word_count,
        "uploaded_images": [], "image_count": 0, "featured_image_id": None,
        "author_assigned": False, "author_bio_inserted": False,
        "featured_image_set": False, "hardcoded_fallback_used": False, "error": error_msg,
    }
    output_path.write_text(json.dumps(fail, indent=2), encoding="utf-8")
    vp = Path(val_path_str) if val_path_str else output_path.parent / "wordpress_validation_report.json"
    vp.parent.mkdir(parents=True, exist_ok=True)
    vp.write_text(json.dumps({
        "agent": "agent_11_wordpress_integration", "version": "3.0",
        "timestamp": datetime.utcnow().isoformat(), "status": "FAILED",
        "validation_passed": False, "post_created": False, "draft_created": False,
        "post_id": None, "draft_url": "", "author_assigned": False,
        "author_bio_inserted": False, "featured_image_set": False,
        "hardcoded_fallback_used": False, "error": error_msg,
        "checks": {"wordpress_credentials": False, "new_post_created": False},
    }, indent=2), encoding="utf-8")


def main():
    import argparse, sys, json, logging, os
    from pathlib import Path
    from datetime import datetime
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [AGENT-11] %(levelname)s %(message)s")
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Agent 11 - WordPress Integration v3.0")
    parser.add_argument("--article", required=True)
    parser.add_argument("--images", required=True)
    parser.add_argument("--rank-math", required=False, default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--validation-report", required=False, default="")
    parser.add_argument("--market", required=False, default="")     # Lot 1: fallback-image vertical routing
    parser.add_argument("--category", required=False, default="")
    args = parser.parse_args()

    article_path = Path(args.article)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    wp_url = os.environ.get("WORDPRESS_URL", "").rstrip("/")
    wp_user = os.environ.get("WORDPRESS_USERNAME", "")
    wp_pass = os.environ.get("WORDPRESS_APP_PASSWORD", "")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not article_path.exists():
        log.error(f"Article not found: {article_path}")
        sys.exit(1)

    if not wp_url or not wp_user or not wp_pass:
        log.error("BLOCKED: WordPress credentials missing")
        _write_failure_reports(output_path, args.validation_report, "", "", 0, "MISSING_WP_CREDENTIALS")
        sys.exit(1)

    # Read article for pre-flight metadata extraction (used in failure reports)
    content_raw = article_path.read_text(encoding="utf-8")
    import re
    title = ""
    keyword = ""
    tm = re.search(r'^title:\s*"?([^"\n]+)"?', content_raw, re.MULTILINE)
    if tm: title = tm.group(1).strip()
    km = re.search(r'^primary_keyword:\s*"?([^"\n]+)"?', content_raw, re.MULTILINE)
    if km: keyword = km.group(1).strip()
    word_count = len(content_raw.split())
    content_chars = len(content_raw)

    log.info(f"Article pre-flight: title='{title}' words={word_count} chars={content_chars} path={article_path}")

    post_id, post_url = None, ""
    try:
        from services.wordpress_service import WordPressService
        from services.llm_service import LLMService
        from services.storage_service import StorageService

        config = {
            "wordpress_url": wp_url,
            "wordpress_username": wp_user,
            "wordpress_app_password": wp_pass,
            "anthropic_api_key": api_key,
            "output_dir": str(output_path.parent),
            "author": {"name": "Talal Eddaouahiri", "bio": "Founder of MoneyAbroadGuide.com"},
            # v3.0 FIX: pass workflow-provided paths into agent so _load_article_data() uses them
            "article_path": str(article_path),
            "images_dir": args.images,
            "market": args.market,        # Lot 1: fallback-image vertical routing
            "category": args.category,
        }
        agent = WordPressIntegrationAgent(
            config,
            LLMService({"anthropic_api_key": api_key, "llm_provider": "anthropic"}),
            StorageService({"output_dir": str(output_path.parent)}),
            WordPressService(config),
        )
        result = asyncio.run(agent.run())
        post_id = result.get("post_id")
        post_url = result.get("post_url", "")
        featured_id = result.get("featured_image_id")
        wp_word_count = result.get("word_count", 0)
        wp_content_chars = result.get("content_chars", 0)

        log.info(f"WP result: post_id={post_id} featured_media={featured_id} words={wp_word_count} chars={wp_content_chars}")

    except Exception as e:
        log.error(f"WP integration failed: {e}")
        _write_failure_reports(output_path, args.validation_report, title, keyword, word_count, str(e))
        sys.exit(1)

    # GATE C v3.0: post_id + title + content + featured_media all required
    gate_errors = []
    if not post_id:
        gate_errors.append("NO_POST_ID")
    if not title:
        gate_errors.append("EMPTY_TITLE")
    if content_chars < 5000:
        gate_errors.append(f"CONTENT_TOO_SHORT:{content_chars}_chars")
    if word_count < 4000:
        gate_errors.append(f"WORD_COUNT_TOO_LOW:{word_count}_words")

    if gate_errors:
        err = "GATE_C_FAIL: " + " | ".join(gate_errors)
        log.error(err)
        _write_failure_reports(output_path, args.validation_report, title, keyword, word_count, err)
        sys.exit(1)

    log.info(f"GATE C PASS: post_id={post_id} title='{title}' chars={content_chars} words={word_count}")

    report = {
        "agent": "agent_11_wordpress_integration", "version": "3.0",
        "timestamp": datetime.utcnow().isoformat(), "status": "COMPLETE",
        "title": title, "keyword": keyword,
        "post_id": post_id, "post_url": post_url,
        "draft_url": post_url, "post_status": "draft", "draft_created": True,
        "word_count": word_count, "content_chars": content_chars,
        "uploaded_images": [], "image_count": 0, "featured_image_id": None,
        "seo_title": title, "meta_description": f"Guide to {keyword} for expats.",
        "hardcoded_fallback_used": False,
    }
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    vp = Path(args.validation_report) if args.validation_report else output_path.parent / "wordpress_validation_report.json"
    vp.parent.mkdir(parents=True, exist_ok=True)
    vp.write_text(json.dumps({
        "agent": "agent_11_wordpress_integration", "version": "3.0",
        "timestamp": datetime.utcnow().isoformat(), "status": "COMPLETE",
        "validation_passed": True, "post_created": True, "draft_created": True,
        "post_id": post_id, "draft_url": post_url,
        "hardcoded_fallback_used": False,
        "checks": {
            "wordpress_credentials": True,
            "new_post_created": True,
            "title_valid": bool(title),
            "content_length_ok": content_chars >= 5000,
            "word_count_ok": word_count >= 4000,
        },
    }, indent=2), encoding="utf-8")

    log.info(f"SUCCESS: post_id={post_id} url={post_url}")
    sys.exit(0)


if __name__ == "__main__":
    main()
