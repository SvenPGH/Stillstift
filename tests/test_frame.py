from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from stillstift import frame

# KDP without bleed, 24-150 pages: 0.375 in inside, 0.25 in on the other three sides.
KDP_INSIDE = frame.px(0.375)
KDP_OUTSIDE = frame.px(0.25)


@pytest.mark.parametrize("side", ["recto", "verso"])
def test_everything_stays_inside_kdp_margins(side: frame.Side) -> None:
    spot = frame.layout(side)
    width, height = spot.page
    assert spot.page == (2550, 3300)
    inside_left = side == "recto"
    for box in (spot.border, spot.tag):
        left, top, right, bottom = box
        assert left >= (KDP_INSIDE if inside_left else KDP_OUTSIDE)
        assert width - right >= (KDP_OUTSIDE if inside_left else KDP_INSIDE)
        assert top >= KDP_OUTSIDE
        assert height - bottom >= KDP_OUTSIDE


def test_art_sits_inside_the_border() -> None:
    spot = frame.layout()
    assert spot.border[0] < spot.art[0] < spot.art[2] < spot.border[2]
    assert spot.border[1] < spot.art[1] < spot.art[3] < spot.border[3]


def test_framed_page_is_pure_black_and_white_with_the_number_in_the_tag() -> None:
    art = Image.new("RGB", (896, 1152), "white")
    ImageDraw.Draw(art).ellipse((100, 100, 800, 1000), outline=(90, 90, 90), width=12)
    page = frame.framed(art, 24)
    assert page.size == (2550, 3300)
    assert {value for _, value in page.getcolors() or []} == {frame.INK, frame.PAPER}
    tag = frame.layout().tag
    inner = page.crop((tag[0] + 60, tag[1] + 40, tag[2] - 60, tag[3] - 40))
    assert inner.getextrema() == (frame.INK, frame.PAPER)


def test_star_has_ten_corners_around_its_centre() -> None:
    corners = frame.star((100, 100), 50)
    assert len(corners) == 10
    assert corners[0] == pytest.approx((100, 50))


def test_main_refuses_a_day_past_24() -> None:
    assert frame.main(["art.png", "25", "out.png"]) == 1
