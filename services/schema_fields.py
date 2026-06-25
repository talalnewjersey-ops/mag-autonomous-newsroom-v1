"""
NEXUS-14 V4 - services/schema_fields.py
Single Source of Truth helper for schema-relevant structured fields.

In V4, the pipeline NEVER emits schema markup (JSON-LD) itself. Yoast SEO is
the single schema authority. This module maps internal article data onto the
Yoast-consumable post-meta keys and the structured fields Yoast needs to render
exactly one schema @graph (WebPage / Article / Person|Organization / Breadcrumb).

It deliberately does NOT produce any <script type="application/ld+json"> output.
Any code path that needs schema should set these fields and let Yoast render.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


# Yoast post-meta keys we are allowed to write. Rank Math keys are intentionally
# absent: V4 removes Rank Math metadata generation entirely.
YOAST_META_KEYS = {
    "focus_keyword": "_yoast_wpseo_focuskw",
    "seo_title": "_yoast_wpseo_title",
    "meta_description": "_yoast_wpseo_metadesc",
    "canonical": "_yoast_wpseo_canonical",
    "article_type": "_yoast_wpseo_schema_article_type",
    "page_type": "_yoast_wpseo_schema_page_type",
}

# Keys that must NEVER be written by V4 (guard list used by tests + agent_11).
FORBIDDEN_META_KEYS = (
    "_rank_math_focus_keyword",
    "_rank_math_description",
    "_rank_math_title",
    "_rank_math_facebook_title",
    "_rank_math_twitter_title",
)


@dataclass
class SchemaFields:
    """Structured fields that Yoast consumes to render a single schema graph."""

    focus_keyword: str = ""
    seo_title: str = ""
    meta_description: str = ""
    canonical: str = ""
    article_type: str = "Article"
    page_type: str = "WebPage"
    author_name: str = "Talal Eddaouahiri"
    date_published: Optional[str] = None
    date_modified: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_date: Optional[str] = None
    official_references: List[str] = field(default_factory=list)

    def to_yoast_meta(self) -> Dict[str, str]:
        """Return only Yoast meta keys. No Rank Math, no JSON-LD."""
        meta = {
            YOAST_META_KEYS["focus_keyword"]: self.focus_keyword or "",
            YOAST_META_KEYS["seo_title"]: self.seo_title or "",
            YOAST_META_KEYS["meta_description"]: self.meta_description or "",
            YOAST_META_KEYS["article_type"]: self.article_type or "Article",
            YOAST_META_KEYS["page_type"]: self.page_type or "WebPage",
        }
        if self.canonical:
            meta[YOAST_META_KEYS["canonical"]] = self.canonical
        return meta


def build_schema_fields(article_data: Dict) -> SchemaFields:
    """Map an internal article_data dict onto SchemaFields.

    article_data is the standard payload produced by Agent 04 / Agent 03.
    """
    now = datetime.now(timezone.utc).date().isoformat()
    return SchemaFields(
        focus_keyword=(article_data.get("keyword") or "").strip(),
        seo_title=(article_data.get("seo_title") or article_data.get("title") or "").strip(),
        meta_description=(article_data.get("meta_description") or "").strip(),
        canonical=(article_data.get("canonical") or "").strip(),
        article_type=article_data.get("schema_article_type", "Article"),
        page_type=article_data.get("schema_page_type", "WebPage"),
        author_name=article_data.get("author", "Talal Eddaouahiri"),
        date_published=article_data.get("date_published") or now,
        date_modified=article_data.get("date_modified") or now,
        reviewed_by=article_data.get("reviewed_by"),
        review_date=article_data.get("review_date") or now,
        official_references=list(article_data.get("official_references", [])),
    )


def assert_no_forbidden_meta(meta: Dict[str, str]) -> None:
    """Raise if any forbidden (Rank Math) meta key is present."""
    bad = [k for k in meta if k in FORBIDDEN_META_KEYS]
    if bad:
        raise ValueError(f"Forbidden schema meta keys present (Rank Math): {bad}")


def contains_jsonld(html: str) -> bool:
    """True if the HTML body contains an embedded JSON-LD <script> block.

    Used by the body-schema guard in Agent 11 and by regression tests to ensure
    no manual JSON-LD is ever injected into post content.
    """
    if not html:
        return False
    lowered = html.lower()
    return "application/ld+json" in lowered
