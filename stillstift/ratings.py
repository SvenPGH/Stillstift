"""A cell's rating: Liked, the page rows, render, flaws, the book flag, on target, a why."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from stillstift.kinds import Kind

ROWS = ("subject", "composition", "lines", "colorability", "detail", "idea")
FLAWS = (
    "grey/shading",
    "open outlines",
    "solid fills",
    "speckle",
    "too dense",
    "too sparse",
    "anatomy/hands",
    "text/artifacts",
    "cropped",
    "style drift",
)
LIKED_FAV = 5
LIKED_WANTED = 3
RENDER_BROKEN = 2


class Verdict(StrEnum):
    FAV = "fav"
    KEEP = "keep"
    ISSUE = "issue"
    KILL = "kill"


class Flag(StrEnum):
    YES = "yes"
    CANDIDATE = "candidate"
    NO = "no"


class OnTarget(StrEnum):
    YES = "yes"
    PARTLY = "partly"
    NO = "no"


@dataclass(frozen=True)
class CellRating:
    """One rating as given: `taste` is the Liked row, the rest may be left blank."""

    taste: int
    rows: dict[str, int] = field(default_factory=dict[str, int])
    render: int | None = None
    flaws: tuple[str, ...] = ()
    book: Flag | None = None
    on_target: OnTarget | None = None
    reason: str = ""


def verdict_of(rating: CellRating) -> Verdict:
    """Map a rating to the four-way verdict it stands for on the scoreboard."""
    wanted = rating.taste >= LIKED_WANTED
    if wanted and rating.render is not None and rating.render <= RENDER_BROKEN:
        return Verdict.ISSUE
    if rating.taste >= LIKED_FAV:
        return Verdict.FAV
    return Verdict.KEEP if wanted else Verdict.KILL


def merge_ratings(rated: Sequence[tuple[str, CellRating]]) -> CellRating:
    """Combine every rater's rating of one cell into one, for dashboards, exports and scoring.

    Taste and render are the raters' mean, rounded to the nearest star; rows average the same
    way, over whichever raters set them. Flaws are the union. Book, on target and reason come
    from the first rater, by name, who set them: those don't have a sensible average.
    """
    ordered = sorted(rated, key=lambda item: item[0])
    ratings = [rating for _, rating in ordered]
    taste = round(sum(r.taste for r in ratings) / len(ratings))
    renders = [r.render for r in ratings if r.render is not None]
    render = round(sum(renders) / len(renders)) if renders else None
    totals: dict[str, int] = {}
    counts: dict[str, int] = {}
    for r in ratings:
        for row, stars in r.rows.items():
            totals[row] = totals.get(row, 0) + stars
            counts[row] = counts.get(row, 0) + 1
    rows = {row: round(total / counts[row]) for row, total in totals.items()}
    flaws = tuple(f for f in FLAWS if any(f in r.flaws for r in ratings))
    book = next((r.book for r in ratings if r.book is not None), None)
    on_target = next((r.on_target for r in ratings if r.on_target is not None), None)
    reasons = dict.fromkeys(r.reason for r in ratings if r.reason)
    return CellRating(
        taste=taste,
        rows=rows,
        render=render,
        flaws=flaws,
        book=book,
        on_target=on_target,
        reason=" / ".join(reasons),
    )


@dataclass(frozen=True)
class Vocabulary:
    """What a set's kind rates beyond Liked, Render and a why."""

    rows: tuple[str, ...]
    flaws: tuple[str, ...]
    book: bool
    on_target: bool


PAGE = Vocabulary(ROWS, FLAWS, book=True, on_target=True)
LAB = Vocabulary((), (), book=False, on_target=False)


def vocabulary(kind: Kind | None) -> Vocabulary:
    """Page sets rate the page rows; lab sets nothing more."""
    return LAB if kind in ("X", "T") else PAGE


def misfits(kind: Kind | None, rating: CellRating) -> list[str]:
    """Name what the rating carries that its set's kind does not rate."""
    allowed = vocabulary(kind)
    found = [r for r in rating.rows if r not in allowed.rows]
    found += [f for f in rating.flaws if f not in allowed.flaws]
    if rating.book is not None and not allowed.book:
        found.append("book")
    if rating.on_target is not None and not allowed.on_target:
        found.append("on target")
    return found
