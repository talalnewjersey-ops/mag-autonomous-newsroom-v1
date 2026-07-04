"""Part 3: a softened BULLET must keep its "- " marker. soften's _clean() has a
"leading junk" strip whose char class includes '-', which used to eat a bullet's
dash when the bullet line was softened (observed on draft 48434). The marker is now
held out of the cleanup and re-attached verbatim -- deletion-only, nothing new added.

Offline: no network, no API key.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.soften_claims import soften, _clean


def test_softened_dash_bullet_keeps_its_marker():
    out = soften("- **Missing one payment** — payment history is 35% of your FICO score")[0]
    assert out.lstrip().startswith("- ")      # bullet marker preserved
    assert "35%" not in out                    # the unsourced number is STILL stripped


def test_star_and_numbered_markers_preserved():
    assert soften("* Keep utilization below 30% for best results")[0].lstrip().startswith("* ")
    assert soften("1. Open a card with a $200 deposit and pay in full")[0].lstrip().startswith("1. ")


def test_clean_preserves_marker_and_adds_nothing():
    # deletion-only: marker re-attached verbatim, no new content introduced
    assert _clean("- **Foo** bar") == "- **Foo** bar"


def test_non_bullet_leading_junk_still_cleaned():
    # the leading-junk strip must STILL fire when there is no list marker
    assert _clean(", stray leading comma").startswith("stray")
    assert _clean("—dash lead").startswith("dash")
