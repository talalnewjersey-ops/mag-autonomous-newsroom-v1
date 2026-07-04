"""L189 fix: an internal link URL was truncated because agent_04 CHAR-SLICED the
internal-links prompt block ([:200]/[:300]), cutting a URL mid-string -- the model
then faithfully reproduced the dead link (.../international-money-). This is NOT a
filets-v2 regression (soften/polish preserve URLs); it is upstream, in the prompt.

Offline, parse-only: no import of the heavy agent, no network, no API key.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = open(os.path.join(ROOT, "agents/agent_04_article_writer.py"), encoding="utf-8").read()


def test_no_char_slice_on_internal_link_blocks():
    # REGRESSION GUARD: a char-slice on a link block lands mid-URL -> dead internal link.
    # The blocks are already bounded by link COUNT, so a [:N] cap is redundant and harmful.
    hits = re.findall(r"links_(?:intro|expert|block)\w*\[:\s*\d+\s*\]", SRC)
    assert hits == [], f"char-slice on a link block re-introduced: {hits}"


def test_all_curated_internal_links_are_complete():
    # every curated internal markdown link must be a complete URL ending in '/)'
    links = re.findall(r"\[[^\]]+\]\(https?://moneyabroadguide\.com[^\)]*\)", SRC)
    assert links, "no curated internal links found -- parser drift?"
    bad = [l for l in links if not re.fullmatch(r"\[[^\]]+\]\(https?://moneyabroadguide\.com/[a-z0-9-]+/\)", l)]
    assert bad == [], f"incomplete/truncated curated internal link(s): {bad}"


def test_char_slice_would_have_truncated_the_url():
    # documents WHY the [:200] was removed: the real default expert block (2 links = 210 chars)
    # char-sliced to 200 loses 'transfer/)' -> the model receives '.../international-money-'.
    expert_block = (
        "- [Best Bank Account for Newcomers to Canada](https://moneyabroadguide.com/best-bank-account-newcomers-canada/)\n"
        "- [International Money Transfer Guide](https://moneyabroadguide.com/international-money-transfer/)"
    )
    assert len(expert_block) > 200
    sliced = expert_block[:200]
    assert sliced.endswith("international-money-")          # cut mid-URL
    assert "international-money-transfer/)" not in sliced   # the real URL is lost
    # the FIX (no slice) keeps the URL whole:
    assert "international-money-transfer/)" in expert_block
