"""Per-rater ratings and favorites: rate_cell, rating, unrate, favorites, verdicts, entry_counts."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from stillstift.ratings import CellRating
from stillstift.store import Cell, Store

NOW = datetime(2026, 1, 1, tzinfo=UTC)
RATERS = ("Sven", "Anna")


def _store(tmp_path: Path) -> Store:
    return Store.open(tmp_path / "curator.sqlite", raters=RATERS)


def _rendered(store: Store, entry: str = "P1", cell_id: str = "#01") -> None:
    store.add_cells(
        [
            Cell(
                entry=entry,
                cell_id=cell_id,
                dimension="",
                value="",
                prompt="a cat",
                negative="",
                seed=1,
                prediction=None,
                prediction_reason="",
            )
        ]
    )
    store.record_render(entry, cell_id, Path("render.png"), "infotext", NOW)


def test_rate_cell_is_kept_per_rater(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _rendered(store)
    store.rate_cell("P1", "#01", "Sven", CellRating(taste=5), NOW)
    store.rate_cell("P1", "#01", "Anna", CellRating(taste=2), NOW)
    sven = store.rating("P1", "#01", "Sven")
    anna = store.rating("P1", "#01", "Anna")
    assert sven is not None
    assert anna is not None
    assert sven.rating.taste == 5
    assert anna.rating.taste == 2


def test_rating_is_none_for_a_rater_who_has_not_rated(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _rendered(store)
    store.rate_cell("P1", "#01", "Sven", CellRating(taste=5), NOW)
    assert store.rating("P1", "#01", "Anna") is None


def test_unrate_only_removes_that_raters_latest(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _rendered(store)
    store.rate_cell("P1", "#01", "Sven", CellRating(taste=5), NOW)
    store.rate_cell("P1", "#01", "Anna", CellRating(taste=2), NOW)
    removed = store.unrate("P1", "#01", "Sven")
    assert removed is not None
    assert removed.taste == 5
    assert store.rating("P1", "#01", "Sven") is None
    assert store.rating("P1", "#01", "Anna") is not None


def test_favorites_are_kept_per_rater(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _rendered(store)
    _rendered(store, cell_id="#02")
    store.set_favorite("P1", "Sven", "#01", NOW)
    store.set_favorite("P1", "Anna", "#02", NOW)
    assert store.favorite("P1", "Sven") == "#01"
    assert store.favorite("P1", "Anna") == "#02"
    assert store.favorites("Sven") == {"P1": "#01"}
    assert store.favorites("Anna") == {"P1": "#02"}


def test_favorite_any_is_the_most_recently_set(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _rendered(store)
    _rendered(store, cell_id="#02")
    earlier = datetime(2026, 1, 1, tzinfo=UTC)
    later = datetime(2026, 1, 2, tzinfo=UTC)
    store.set_favorite("P1", "Sven", "#01", earlier)
    store.set_favorite("P1", "Anna", "#02", later)
    assert store.favorite_any("P1") == "#02"
    assert store.favorites_any() == {"P1": "#02"}


def test_verdicts_per_rater_are_each_raters_own(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _rendered(store)
    store.rate_cell("P1", "#01", "Sven", CellRating(taste=5), NOW)
    store.rate_cell("P1", "#01", "Anna", CellRating(taste=1), NOW)
    sven = {v.cell_id: v for v in store.verdicts("P1", rater="Sven")}
    anna = {v.cell_id: v for v in store.verdicts("P1", rater="Anna")}
    assert sven["#01"].rating is not None
    assert sven["#01"].rating.taste == 5
    assert anna["#01"].rating is not None
    assert anna["#01"].rating.taste == 1


def test_verdicts_without_a_rater_merge_every_raters_latest(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _rendered(store)
    store.rate_cell(
        "P1", "#01", "Sven", CellRating(taste=5, flaws=("cropped",), reason="sharp"), NOW
    )
    store.rate_cell(
        "P1", "#01", "Anna", CellRating(taste=1, flaws=("speckle",), reason="muddy"), NOW
    )
    merged = {v.cell_id: v for v in store.verdicts("P1")}
    rating = merged["#01"].rating
    assert rating is not None
    assert rating.taste == 3  # mean of 5 and 1
    assert set(rating.flaws) == {"cropped", "speckle"}
    assert rating.reason == "muddy / sharp"


def test_entry_counts_unrated_is_per_rater(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _rendered(store)
    store.rate_cell("P1", "#01", "Sven", CellRating(taste=5), NOW)
    by_rater = {c.entry: c for c in store.entry_counts("Sven")}
    anna_counts = {c.entry: c for c in store.entry_counts("Anna")}
    assert by_rater["P1"].unrated == 0
    assert anna_counts["P1"].unrated == 1


def test_entry_counts_without_a_rater_counts_unrated_by_anyone(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _rendered(store)
    store.rate_cell("P1", "#01", "Sven", CellRating(taste=5), NOW)
    counts = {c.entry: c for c in store.entry_counts()}
    assert counts["P1"].unrated == 0
