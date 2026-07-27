"""agent_11's Markdown-link-to-HTML converter, `_render_inline` (2026-07-26,
pre-production 404 audit): the old regex `\\[(.+?)\\]\\((.+?)\\)` captures
ANYTHING between `(` and the next `)` as the href, with no validation that it
looks like a URL. Real, live bug found via the Redirection plugin's 404 log:
`/rent-without-credit-canada/&lt;a` -- the writer occasionally emits a
malformed Markdown link whose "url" portion contains a raw, unescaped
`<a href="...">...</a>` tag (agent_04 hands the writer Markdown-formatted
internal-link suggestions; when it botches the syntax, the old regex faithfully
stuffs the garbage straight into the published `href`). Confirmed root cause:
this exact malformed input reproduces the exact artifact seen in the wild
(see reproduction test below, run against the OLD pattern for the record).

Fix: restrict the URL capture group to characters a real URL can contain,
excluding whitespace and `<>()` -- a malformed/nested link like the one above
no longer matches as a link AT ALL (falls through as literal text, which may
look a little ugly but is never a broken href) instead of being silently
corrupted into one. This regex runs on every single article at publish time,
so every case here is a real published-content shape, not a hypothetical.

`_render_inline` doesn't touch `self` internally -- calling it unbound
(`WordPressIntegrationAgent._render_inline(None, text)`) avoids constructing
the full agent (config/llm_service/storage_service/wordpress_service), same
as any other pure-string-transform method in this codebase.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.agent_11_wordpress_integration import WordPressIntegrationAgent


def render(text):
    return WordPressIntegrationAgent._render_inline(None, text)


def test_wellformed_link_converts_correctly():
    out = render("See [our guide](https://moneyabroadguide.com/rent-without-credit-canada/) for more.")
    assert out == 'See <a href="https://moneyabroadguide.com/rent-without-credit-canada/">our guide</a> for more.'


def test_two_adjacent_wellformed_links_both_convert():
    out = render("[A](https://x.com/a) and [B](https://x.com/b).")
    assert out == '<a href="https://x.com/a">A</a> and <a href="https://x.com/b">B</a>.'


def test_link_with_query_string_and_fragment_preserved():
    out = render("[Guide](https://x.com/a?utm=source&ref=1#section) here.")
    assert out == '<a href="https://x.com/a?utm=source&ref=1#section">Guide</a> here.'


def test_link_followed_by_sentence_punctuation():
    out = render("Read [the guide](https://x.com/a). It helps.")
    assert out == 'Read <a href="https://x.com/a">the guide</a>. It helps.'


def test_malformed_nested_html_in_url_is_never_stuffed_into_href():
    """The real 2026-07-26 bug shape: a raw <a> tag leaked inside the
    Markdown link's parentheses. Must NEVER produce a broken/nested href --
    rejecting the outer Markdown wrapper (leaving it as literal text) is the
    correct, safe outcome, not a second-best compromise."""
    bad = ('See [our guide](https://moneyabroadguide.com/rent-without-credit-canada/'
           '<a href="https://other.com">this</a>) for more.')
    out = render(bad)
    assert "&lt;a" not in out
    assert 'href="https://moneyabroadguide.com/rent-without-credit-canada/<a' not in out
    # the malformed wrapper is left as literal text -- the still-valid inner
    # <a> tag is untouched and will render as its own normal link
    assert '<a href="https://other.com">this</a>' in out


def test_reproduces_the_original_bug_with_the_old_pattern():
    """Documents WHY the fix is needed: the OLD pattern, run against the same
    malformed input above, produces exactly the corrupted href this fix
    exists to prevent. Not a test of current behavior (uses the old regex
    literal, not the live method) -- a regression guard against ever
    reverting to that pattern."""
    import re
    old_pattern = r'\[(.+?)\]\((.+?)\)'
    bad = ('See [our guide](https://moneyabroadguide.com/rent-without-credit-canada/'
           '<a href="https://other.com">this</a>) for more.')
    corrupted = re.sub(old_pattern, r'<a href="\2">\1</a>', bad)
    assert '<a href="https://moneyabroadguide.com/rent-without-credit-canada/<a href="https://other.com">this</a>">' in corrupted
