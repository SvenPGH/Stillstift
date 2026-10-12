"""Verdict scoring: per-cell hits and kill/fav recall."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from stillstift.store import Verdict

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class Hits:
    taste: bool
    fav: bool
    issue: bool


@dataclass(frozen=True)
class Recall:
    scored: int
    kills: int
    kills_called: int
    favs: int
    favs_called: int

    @property
    def kill_recall(self) -> float | None:
        return self.kills_called / self.kills if self.kills else None

    @property
    def fav_recall(self) -> float | None:
        return self.favs_called / self.favs if self.favs else None


def hits(prediction: Verdict, verdict: Verdict) -> Hits:
    return Hits(
        taste=(prediction is Verdict.KILL) == (verdict is Verdict.KILL),
        fav=prediction is Verdict.FAV and verdict is Verdict.FAV,
        issue=prediction is Verdict.ISSUE and verdict is Verdict.ISSUE,
    )


def recall(pairs: Sequence[tuple[Verdict, Verdict]], last: int | None = None) -> Recall:
    """Recall over (prediction, verdict) pairs, oldest first; `last` keeps the newest N."""
    window = pairs[-last:] if last else pairs
    kills = [p for p, v in window if v is Verdict.KILL]
    favs = [p for p, v in window if v is Verdict.FAV]
    return Recall(
        scored=len(window),
        kills=len(kills),
        kills_called=kills.count(Verdict.KILL),
        favs=len(favs),
        favs_called=favs.count(Verdict.FAV),
    )
