"""Sprint 8 — output sanitization. Offline, no network, no API key.

One test per artifact in the leak map (from the 48418 audit) proving it can no
longer reach WordPress:
  - YAML frontmatter leaking as <p>
  - double <h1> (body H1 on top of the post-title H1)
  - `$` injected into headings (the `stripped + "$"` regex bug)
  - visible `---` separators (same bug broke <hr> detection)
  - Markdown tables left un-converted
  - malformed <figure>/<figcaption>/<p>
  - "No affiliate opportunities detected" placeholder block rendered
  - off-topic image captions
Plus: case-studies section removed + min_case_studies == 0 (anti-fabrication).

agent_11 imports aiohttp + services at module top; CI installs neither, so we
stub them before loading the module. All logic under test is pure string work.
"""
import asyncio
import importlib.util
import json
import os
import sys
import types
from html.parser import HTMLParser

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _stub(name, **attrs):
    if name not in sys.modules:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m


if "aiohttp" not in sys.modules:
    aio = types.ModuleType("aiohttp")
    aio.ClientTimeout = lambda *a, **k: None
    aio.ClientSession = object
    aio.ClientError = Exception
    sys.modules["aiohttp"] = aio
_stub("services.llm_service", LLMService=object)
_stub("services.storage_service", StorageService=object)
_stub("services.wordpress_service", WordPressService=object)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


agent_11 = _load("agents/agent_11_wordpress_integration.py", "agent_11_sani")
agent_04 = _load("agents/agent_04_article_writer.py", "agent_04_sani")
WP = agent_11.WordPressIntegrationAgent


def _agent():
    a = WP.__new__(WP)
    a.config = {}
    return a


def html_of(md):
    return asyncio.run(_agent()._convert_to_html({"content": md}))


class _Balance(HTMLParser):
    """Track open/close balance for block tags we emit."""
    TAGS = {"figure", "figcaption", "p", "table", "thead", "tbody", "tr", "td", "th", "div", "h1", "h2", "h3", "ul", "ol", "li"}
    VOID = {"img", "hr", "br"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.balanced = True
        self.h1 = 0

    def handle_starttag(self, tag, attrs):
        if tag == "h1":
            self.h1 += 1
        if tag in self.VOID:
            return
        if tag in self.TAGS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.TAGS:
            if not self.stack or self.stack[-1] != tag:
                self.balanced = False
            else:
                self.stack.pop()


def _parse(html):
    p = _Balance()
    p.feed(html)
    if p.stack:
        p.balanced = False
    return p


# ---------- frontmatter ----------

def test_frontmatter_stripped():
    md = '---\ntitle: "Car Insurance"\nmarket: "USA"\nstatus: draft\n---\n\n## Intro\nBody text.'
    out = html_of(md)
    assert "title:" not in out
    assert "market:" not in out
    assert "status: draft" not in out
    assert "<h2>Intro</h2>" in out


# ---------- single H1 ----------

def test_body_has_zero_h1():
    md = "# Car Insurance Guide\n\n## Section\nText."
    out = html_of(md)
    p = _parse(out)
    assert p.h1 == 0, "body must contain no <h1> (post title is the only page H1)"
    assert "<h2>Car Insurance Guide</h2>" in out  # demoted, not dropped


# ---------- $ in headings (regex-hack regression) ----------

def test_no_dollar_suffixed_heading():
    out = html_of("## Costs and Premiums")
    assert "<h2>Costs and Premiums</h2>" in out
    assert "$</h2>" not in out and "Premiums$" not in out


# ---------- visible --- separators ----------

def test_hr_rendered_not_visible():
    out = html_of("Above.\n\n---\n\nBelow.")
    assert "<hr />" in out
    assert "<p>---</p>" not in out and "---" not in out.replace("<hr />", "")


# ---------- markdown tables ----------

def test_markdown_table_converted():
    md = "| Plan | Price |\n| --- | --- |\n| Basic | $50 |\n| Premium | $90 |"
    out = html_of(md)
    assert "<table>" in out and "overflow-x:auto" in out
    assert "<th>Plan</th>" in out and "<td>Basic</td>" in out
    assert "|" not in out, "no raw markdown pipes may remain"
    assert _parse(out).balanced


# ---------- balanced HTML ----------

def test_generated_html_is_balanced():
    md = ("## A\nPara with **bold**.\n\n| X | Y |\n| - | - |\n| 1 | 2 |\n\n"
          "- item one\n- item two\n\n> a quote\n\n## B\nMore.")
    assert _parse(html_of(md)).balanced


# ---------- affiliate placeholder ----------

def _affiliate(tmp_path, recs, html):
    d = tmp_path / "agent_08"
    d.mkdir(parents=True, exist_ok=True)
    (d / "affiliate_report.json").write_text(json.dumps({"recommendations": recs}), encoding="utf-8")
    a = _agent()
    a.config = {"article_path": str(tmp_path / "agent_04" / "article_draft.md")}
    return asyncio.run(a._add_affiliate_blocks(html, {}))


def test_no_affiliate_placeholder_block(tmp_path):
    html = "<h2>Section</h2><p>Body</p>"
    out = _affiliate(tmp_path, ["No affiliate opportunities detected"], html)
    assert "No affiliate opportunities detected" not in out
    assert "mag-affiliate-box" not in out


def test_empty_affiliate_recs_render_nothing(tmp_path):
    html = "<h2>Section</h2><p>Body</p>"
    assert "mag-affiliate-box" not in _affiliate(tmp_path, [], html)


def test_actionable_affiliate_renders(tmp_path):
    html = "<h2>Section</h2><p>Body</p>"
    out = _affiliate(tmp_path, [{"name": "Wise", "url": "https://wise.com", "description": "Send money"}], html)
    assert "mag-affiliate-box" in out and "https://wise.com" in out


# ---------- off-topic captions ----------

def test_caption_never_offtopic_default():
    images = [
        {"uploaded": True, "wp_url": "https://x/f.jpg", "wp_media_id": 1, "alt_text": "featured"},
        {"uploaded": True, "wp_url": "https://x/1.jpg", "wp_media_id": 2,
         "alt_text": "car insurance documents", "caption": "immigration guide"},
    ]
    out = asyncio.run(_agent()._insert_images_in_content("<h2>Sec</h2><p>Body</p>", images))
    assert "car insurance documents" in out          # caption derives from alt
    assert "immigration guide" not in out            # off-topic caption field ignored
    assert _parse(out).balanced


# ---------- case studies removed (anti-fabrication) ----------

def test_case_studies_min_is_zero_all_tiers():
    for t in ("PILLAR", "STANDARD", "OPPORTUNITY", "GOLD"):
        assert agent_04._get_tier_config(t)["min_case_studies"] == 0


def test_writer_no_longer_prompts_realworld_examples():
    import inspect
    src = inspect.getsource(agent_04._write_article_standalone)
    assert "Real-World Examples" not in src
    assert "Specific names, outcomes, numbers" not in src


def test_writer_emits_no_frontmatter_or_body_h1():
    import inspect
    src = inspect.getsource(agent_04._write_article_standalone)
    assert 'f"---\\ntitle:' not in src, "writer must not emit YAML frontmatter"
    assert "# {title}" not in src, "writer must not emit a body H1"
