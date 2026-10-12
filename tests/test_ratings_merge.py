"""merge_ratings: how raters' individual ratings combine into one, for dashboards and exports."""

from __future__ import annotations

from stillstift.ratings import CellRating, Flag, OnTarget, merge_ratings


def test_taste_and_render_are_the_mean_rounded_to_a_star() -> None:
    merged = merge_ratings(
        [("Anna", CellRating(taste=2, render=3)), ("Sven", CellRating(taste=5, render=4))]
    )
    assert merged.taste == 4  # mean 3.5 rounds to 4 (banker's rounding keeps it even)
    assert merged.render == 4  # mean 3.5 rounds to 4


def test_render_is_none_when_nobody_set_it() -> None:
    merged = merge_ratings([("Anna", CellRating(taste=3)), ("Sven", CellRating(taste=3))])
    assert merged.render is None


def test_rows_average_only_over_raters_who_set_them() -> None:
    merged = merge_ratings(
        [
            ("Anna", CellRating(taste=3, rows={"lines": 4})),
            ("Sven", CellRating(taste=3, rows={"lines": 2, "detail": 5})),
        ]
    )
    assert merged.rows == {"lines": 3, "detail": 5}


def test_flaws_are_the_union() -> None:
    merged = merge_ratings(
        [
            ("Anna", CellRating(taste=3, flaws=("cropped",))),
            ("Sven", CellRating(taste=3, flaws=("speckle", "cropped"))),
        ]
    )
    assert set(merged.flaws) == {"cropped", "speckle"}


def test_book_and_on_target_come_from_the_first_rater_by_name_who_set_them() -> None:
    merged = merge_ratings(
        [
            ("Sven", CellRating(taste=3, book=Flag.YES)),
            ("Anna", CellRating(taste=3, book=Flag.NO, on_target=OnTarget.YES)),
        ]
    )
    assert merged.book == Flag.NO  # "Anna" sorts before "Sven"
    assert merged.on_target == OnTarget.YES


def test_reasons_are_joined_when_they_differ() -> None:
    merged = merge_ratings(
        [("Sven", CellRating(taste=3, reason="sharp")), ("Anna", CellRating(taste=3, reason=""))]
    )
    assert merged.reason == "sharp"
    both = merge_ratings(
        [
            ("Sven", CellRating(taste=3, reason="sharp")),
            ("Anna", CellRating(taste=3, reason="muddy")),
        ]
    )
    assert both.reason == "muddy / sharp"
