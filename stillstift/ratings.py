"""A cell's rating: Liked, the page rows, render, flaws, the book flag, on target, a why."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
