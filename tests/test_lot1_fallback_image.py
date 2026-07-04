"""Lot 1 -- decorative fallback header image. Offline: no network, no API key.

Proves the fallback image is a VALID decorative PNG, per-vertical (accent colour),
and -- the invariant -- that it DISPLAYS NO DATA (the only text is the site name;
no digit / number / stat can appear on it, so it can never carry a fabricated fact).
"""
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

Image = pytest.importorskip("PIL.Image")  # Pillow present in CI (requirements); skip if absent
from agents._fallback_image import make_fallback_image, _LABEL, _ACCENT


def test_makes_a_valid_png(tmp_path):
    p = make_fallback_image("us_credit", str(tmp_path / "h.png"))
    img = Image.open(p)
    assert img.format == "PNG" and img.size == (1200, 630)


def test_per_vertical_accent_differs(tmp_path):
    a = Image.open(make_fallback_image("us_credit", str(tmp_path / "a.png"))).getpixel((5, 620))
    b = Image.open(make_fallback_image("us_banking", str(tmp_path / "b.png"))).getpixel((5, 620))
    assert a != b   # different accent colour -> different bottom pixel


def test_unknown_vertical_falls_back_without_crashing(tmp_path):
    p = make_fallback_image("does_not_exist", str(tmp_path / "u.png"))
    assert Image.open(p).size == (1200, 630)


def test_label_carries_no_data():
    # The invariant: the only text on the image is the site name -- never a figure.
    assert _LABEL == "MoneyAbroadGuide"
    assert not re.search(r"\d", _LABEL)               # no digit anywhere
    assert "%" not in _LABEL and "$" not in _LABEL


def test_all_nine_verticals_have_an_accent():
    for v in ("us_credit", "us_banking", "us_auto", "us_health", "us_mortgage",
              "us_transfers", "us_housing", "us_students", "canada_newcomer", "us_default"):
        assert v in _ACCENT
