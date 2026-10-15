"""`just frame <art.png> <day> <out.png>`: lay a page's art into the Advent book's day frame.

The page is KDP's 8.5x11 in trim at 300 dpi without bleed: a double rounded border with a tag
at the top for the day number, set in Fredoka (SIL Open Font License, `stillstift/fonts/OFL.txt`).
The art is scaled to cover the frame's inside, clipped to its rounded corners and thresholded to
pure black and white, so any raw render or upscale of one fits.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from PIL import Image, ImageDraw, ImageFont, ImageOps

if TYPE_CHECKING:
    from collections.abc import Sequence

DPI = 300
TRIM = (8.5, 11.0)
# Fredoka at SemiBold, cut down to the digits: all the tag ever sets.
FONT = Path(__file__).parent / "fonts" / "Fredoka-SemiBold-digits.ttf"

# Inches. KDP asks for 0.375 in inside and 0.25 in outside without bleed (24-150 pages); the
# border keeps well clear of both, and the gutter side gets more for the binding.
OUTSIDE = 0.5
GUTTER = 0.625
TOP = 0.8
BOTTOM = 0.5
RADIUS = 0.3
OUTER_LINE = 0.05
GAP = 0.06
INNER_LINE = 0.025
TAG_SIZE = (1.5, 0.66)
TAG_TEXT = 0.5
STAR_RADIUS = 0.26
STAR_OFFSET = 1.2
INK = 0
PAPER = 255
LAST_DAY = 24

Side = Literal["recto", "verso"]
Box = tuple[int, int, int, int]


def px(inches: float) -> int:
    return round(inches * DPI)


@dataclass(frozen=True)
class Layout:
    """Where everything sits on the page, in pixels; boxes are (left, top, right, bottom)."""

    page: tuple[int, int]
    border: Box
    art: Box
    tag: Box


def layout(side: Side = "recto") -> Layout:
    """Place the page's boxes; a recto (right-hand) page has its gutter on the left."""
    width, height = px(TRIM[0]), px(TRIM[1])
    left, right = (GUTTER, OUTSIDE) if side == "recto" else (OUTSIDE, GUTTER)
    border = (px(left), px(TOP), width - px(right), height - px(BOTTOM))
    inset = px(OUTER_LINE + GAP + INNER_LINE)
    art = (border[0] + inset, border[1] + inset, border[2] - inset, border[3] - inset)
    tag_w, tag_h = px(TAG_SIZE[0]), px(TAG_SIZE[1])
    middle = (border[0] + border[2]) // 2
    tag = (middle - tag_w // 2, border[1] - tag_h // 2, middle + tag_w // 2, border[1] + tag_h // 2)
    return Layout((width, height), border, art, tag)


def _shrunk(box: Box, by: int) -> Box:
    return (box[0] + by, box[1] + by, box[2] - by, box[3] - by)


def star(centre: tuple[float, float], radius: float) -> list[tuple[float, float]]:
    """Return a five-pointed star's corners, point up."""
    corners: list[tuple[float, float]] = []
    for n in range(10):
        reach = radius if n % 2 == 0 else radius * 0.5
        angle = math.pi / 5 * n - math.pi / 2
        corners.append((centre[0] + reach * math.cos(angle), centre[1] + reach * math.sin(angle)))
    return corners


def _covered(art: Image.Image, box: Box) -> Image.Image:
    """Scale the art to cover the box, cut to the middle, and threshold it to black and white."""
    size = (box[2] - box[0], box[3] - box[1])
    gray = ImageOps.fit(art.convert("L"), size, Image.Resampling.LANCZOS)
    return gray.convert("1", dither=Image.Dither.NONE).convert("L")


def framed(art: Image.Image, day: int, side: Side = "recto") -> Image.Image:
    """Draw the finished page: the art inside the border, the day number in the tag."""
    spot = layout(side)
    page = Image.new("L", spot.page, PAPER)
    radius = px(RADIUS)
    inset = spot.art[0] - spot.border[0]
    mask = Image.new("L", spot.page, 0)
    ImageDraw.Draw(mask).rounded_rectangle(spot.art, radius=radius - inset, fill=255)
    page.paste(_covered(art, spot.art), spot.art[:2], mask.crop(spot.art))

    draw = ImageDraw.Draw(page)
    draw.fontmode = "1"
    draw.rounded_rectangle(spot.border, radius=radius, outline=INK, width=px(OUTER_LINE))
    inner = _shrunk(spot.border, px(OUTER_LINE + GAP))
    inner_radius = radius - px(OUTER_LINE + GAP)
    draw.rounded_rectangle(inner, radius=inner_radius, outline=INK, width=px(INNER_LINE))

    middle = (spot.tag[0] + spot.tag[2]) / 2
    for x in (middle - px(STAR_OFFSET), middle + px(STAR_OFFSET)):
        # Pillow's polygon outline frays at a star's inner corners; a black star under a
        # smaller white one gives a clean stroke.
        draw.polygon(star((x, spot.border[1]), px(STAR_RADIUS)), fill=INK)
        draw.polygon(star((x, spot.border[1]), px(STAR_RADIUS - 2.2 * OUTER_LINE)), fill=PAPER)
    tag_radius = (spot.tag[3] - spot.tag[1]) // 2
    draw.rounded_rectangle(
        spot.tag, radius=tag_radius, fill=PAPER, outline=INK, width=px(OUTER_LINE)
    )
    draw.rounded_rectangle(
        _shrunk(spot.tag, px(OUTER_LINE + GAP)),
        radius=tag_radius - px(OUTER_LINE + GAP),
        outline=INK,
        width=px(INNER_LINE),
    )
    font = ImageFont.truetype(FONT, px(TAG_TEXT))
    centre = ((spot.tag[0] + spot.tag[2]) / 2, (spot.tag[1] + spot.tag[3]) / 2)
    draw.text(centre, str(day), fill=INK, font=font, anchor="mm")
    return page


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="just frame", description=__doc__)
    parser.add_argument("art", type=Path, help="the page's art, any size")
    parser.add_argument("day", type=int, help="the day number for the tag, 1 to 24")
    parser.add_argument("out", type=Path, help="the framed page's PNG")
    parser.add_argument("--side", choices=["recto", "verso"], default="recto")
    args = parser.parse_args(argv)
    if not 1 <= args.day <= LAST_DAY:
        sys.stderr.write("frame: day is 1 to 24\n")
        return 1
    side: Side = "verso" if args.side == "verso" else "recto"
    try:
        with Image.open(args.art) as art:
            page = framed(art, args.day, side)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        page.save(args.out, dpi=(DPI, DPI))
    except OSError as error:
        sys.stderr.write(f"frame: {error}\n")
        return 1
    sys.stdout.write(f"{args.out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
