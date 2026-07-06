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


def test_no_static_internal_links_dict_remains():
    # POINT 4 (2026-07-05): the static, hand-maintained INTERNAL_LINKS dict was
    # REMOVED (it had drifted to 18/21 = 86% dead links -- see
    # agents/_real_internal_links.py). This guards against reintroducing a
    # hardcoded internal-link list: no bare moneyabroadguide.com markdown link
    # should appear literally in the source any more -- real links now come
    # ONLY from a live WP REST API fetch at write time.
    assert not re.search(r"^INTERNAL_LINKS\s*=\s*\{", SRC, re.MULTILINE), \
        "the static INTERNAL_LINKS dict reappeared"
    hardcoded = re.findall(r"\[[^\]]+\]\(https?://moneyabroadguide\.com[^\)]*\)", SRC)
    assert hardcoded == [], f"a hardcoded internal link reappeared in source: {hardcoded}"
    assert "from agents._real_internal_links import" in SRC


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
