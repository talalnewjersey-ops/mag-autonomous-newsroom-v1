"""Lot 1 -- deterministic DECORATIVE fallback header image.

Generated when agent_10 (Gemini) cannot produce an image (e.g. HTTP 429 quota),
so a draft still gets a featured image WITHOUT depending on the image API. A
missing image must never block or FAIL an article -- the image is cosmetic.

Hard guarantee: this image DISPLAYS NO DATA. It is a branded gradient banner with
the site name only -- no number, statistic, score, chart or fabricated fact can
appear on it. The per-vertical difference is an accent COLOUR only (decoration).
"""
from PIL import Image, ImageDraw, ImageFont

# Per-vertical accent colours -- purely decorative, no meaning beyond theming.
_ACCENT = {
    "us_credit": (37, 99, 235),
    "us_banking": (5, 150, 105),
    "us_auto": (220, 38, 38),
    "us_health": (13, 148, 136),
    "us_mortgage": (109, 40, 217),
    "us_transfers": (2, 132, 199),
    "us_housing": (202, 138, 4),
    "us_students": (219, 39, 119),
    "canada_newcomer": (185, 28, 28),
    "us_default": (30, 58, 138),
}
_LABEL = "MoneyAbroadGuide"  # fixed decorative branding -- NEVER a figure or claim


def make_fallback_image(vertical, out_path, size=(1200, 630)):
    """Write a decorative PNG header for `vertical` to out_path; return out_path."""
    w, h = size
    accent = _ACCENT.get(vertical or "us_default", _ACCENT["us_default"])
    base = (17, 24, 39)
    img = Image.new("RGB", size, base)
    draw = ImageDraw.Draw(img)
    for y in range(h):  # simple vertical gradient base -> accent
        t = y / h
        draw.line([(0, y), (w, y)], fill=tuple(int(base[i] + (accent[i] - base[i]) * t) for i in range(3)))
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 68)
    except Exception:
        font = ImageFont.load_default()
    draw.text((60, h // 2 - 34), _LABEL, fill=(255, 255, 255), font=font)  # branding only
    img.save(out_path, "PNG")
    return out_path
