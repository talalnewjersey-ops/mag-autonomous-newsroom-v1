"""INTERNAL MARKER LEAK FIX (2026-07-06): every published article ended with
a trailing blockquote that ALSO printed internal pipeline artifacts --
"**Tier**: OPPORTUNITY | NEXUS-14 V5.0" -- straight into the published HTML.
Confirmed on real captured drafts from two separate runs (run7/article_3,
the Gemini-verification test run's article_1): both ended in the exact line
'> **Last Updated**: July 2026 | **Tier**: OPPORTUNITY | NEXUS-14 V5.0'.
Same class of bug as the "Categories not covered" leak fixed in PR #53 --
an internal-only value (tier name, engine version) that the reader was
never meant to see. The reader must only ever see the update date.

The fix is scoped to agents/agent_04_article_writer.py's trailing-blockquote
f-string (the single source of this line, confirmed via a full-codebase
grep before this fix -- no other occurrence). _write_article_standalone is
an async function that makes several live Claude API calls, so it isn't
exercised directly here; these tests instead (1) source-guard the exact
literal that must and must not appear, and (2) reproduce the trailing-line
CONSTRUCTION logic in isolation (the same one-liner, copied verbatim) against
both a synthetic case and the real frozen buggy strings, proving the new
construction can never reproduce them.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = open(os.path.join(ROOT, "agents/agent_04_article_writer.py"), encoding="utf-8").read()


# ---------------------------------------------------------------- source guards

def test_source_no_longer_builds_a_tier_or_nexus_version_marker_line():
    # scoped to the trailing-blockquote f-string that actually ends up in
    # published content -- NOT the module's own header docstring/comments
    # (e.g. "COST-OPTIMIZED v5.0"), which are source-only and never leak.
    trailing_line_src = re.search(r'f"> \*\*Last Updated\*\*:.*"', SRC)
    assert trailing_line_src is not None, "the trailing blockquote f-string must still exist"
    assert "Tier" not in trailing_line_src.group(0)
    assert "NEXUS" not in trailing_line_src.group(0)


def test_source_still_builds_the_last_updated_line():
    assert '"> **Last Updated**: {_updated}"' in SRC


def test_only_one_place_in_the_whole_agent_ever_built_this_trailing_line():
    # guards against a second, un-fixed occurrence elsewhere in the same file
    assert SRC.count("**Last Updated**") == 1


# ---------------------------------------------------------------- construction-logic reproduction
# mirrors agent_04_article_writer.py's exact one-liner (kept in sync manually,
# cross-checked by the source guards above).

def _build_trailing_line(updated: str) -> str:
    return f"> **Last Updated**: {updated}"


def test_new_construction_never_contains_a_tier_or_version_marker():
    line = _build_trailing_line("July 2026")
    assert "Tier" not in line
    assert "NEXUS" not in line
    assert "V5.0" not in line
    assert line == "> **Last Updated**: July 2026"


def test_new_construction_still_shows_a_real_update_date():
    line = _build_trailing_line("July 2026")
    assert "Last Updated" in line
    assert "July 2026" in line


# ---------------------------------------------------------------- real captured regression cases

REAL_BUGGY_LINES = [
    # run7/article_3 (us_credit) and the Gemini-verification test run's
    # article_1 (us_auto) -- both real, both frozen verbatim from the
    # actual published-bound drafts.
    "> **Last Updated**: July 2026 | **Tier**: OPPORTUNITY | NEXUS-14 V5.0",
]


def test_real_buggy_lines_would_have_been_caught_by_this_pattern():
    marker_re = re.compile(r"\*\*Tier\*\*|NEXUS-14|V\d\.\d")
    for buggy in REAL_BUGGY_LINES:
        assert marker_re.search(buggy), "the detection pattern must catch the real historical bug"


def test_new_construction_output_never_matches_the_leak_pattern():
    marker_re = re.compile(r"\*\*Tier\*\*|NEXUS-14|V\d\.\d")
    line = _build_trailing_line("July 2026")
    assert not marker_re.search(line), f"leaked internal marker in published output: {line!r}"


# ---------------------------------------------------------------- full-article HTML simulation
# a published article is this trailing line joined with the rest of the body,
# exactly as agent_04 builds it and as WordPress would render it -- confirms
# no Tier/NEXUS/version marker survives in the assembled output while the
# update date remains visible.

def test_assembled_article_body_has_no_marker_leak_but_keeps_the_date():
    intro = "Some intro paragraph."
    faq = "## FAQ\n\n### Question?\n\nAnswer."
    closing = "## Conclusion\n\nWrap-up text."
    trailing = _build_trailing_line("July 2026")
    body = "\n\n".join([intro, faq, closing, trailing])

    assert re.search(r"\bTier\b", body) is None
    assert "NEXUS" not in body
    assert not re.search(r"\bV\d\.\d\b", body)
    assert "Last Updated" in body
    assert "July 2026" in body
