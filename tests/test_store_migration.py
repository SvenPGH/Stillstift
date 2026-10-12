"""Opening a store from before raters existed: existing ratings and favorites are kept."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from stillstift.store import Store

if TYPE_CHECKING:
    from pathlib import Path

LEGACY_SCHEMA = """
CREATE TABLE cells (
    entry             TEXT NOT NULL,
    cell_id           TEXT NOT NULL,
    dimension         TEXT NOT NULL,
    value             TEXT NOT NULL,
    prompt            TEXT NOT NULL,
    negative          TEXT NOT NULL,
    seed              INTEGER NOT NULL,
    prediction        TEXT,
    prediction_reason TEXT NOT NULL,
    image_path        TEXT,
    infotext          TEXT,
    rendered_at       TEXT,
    intent            TEXT NOT NULL DEFAULT '',
    tags              TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (entry, cell_id)
);
CREATE TABLE ratings (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    entry     TEXT NOT NULL,
    cell_id   TEXT NOT NULL,
    taste     INTEGER NOT NULL,
    rows      TEXT NOT NULL,
    render    INTEGER,
    flaws     TEXT NOT NULL,
    book      TEXT,
    on_target TEXT,
    reason    TEXT NOT NULL,
    rated_at  TEXT NOT NULL
);
CREATE INDEX ratings_latest ON ratings (entry, cell_id, id);
CREATE TABLE favorites (
    entry   TEXT PRIMARY KEY,
    cell_id TEXT NOT NULL,
    set_at  TEXT NOT NULL
);
CREATE TABLE sets (
    entry TEXT PRIMARY KEY,
    name  TEXT NOT NULL DEFAULT '',
    date  TEXT NOT NULL DEFAULT '',
    tests TEXT NOT NULL DEFAULT ''
);
"""


def _legacy_db(path: Path) -> None:
    """Build a pre-rater store directly, the shape a real one would have from before."""
    db = sqlite3.connect(path)
    with db:
        db.executescript(LEGACY_SCHEMA)
        db.execute(
            "INSERT INTO cells (entry, cell_id, dimension, value, prompt, negative, seed,"
            " prediction_reason, rendered_at) VALUES ('P1', '#01', '', '', 'a cat', '', 1, '',"
            " '2026-01-01T00:00:00+00:00')"
        )
        db.execute(
            "INSERT INTO ratings (entry, cell_id, taste, rows, render, flaws, book, on_target,"
            " reason, rated_at) VALUES ('P1', '#01', 4, '{}', NULL, '[]', NULL, NULL, '',"
            " '2026-01-01T00:00:00+00:00')"
        )
        db.execute(
            "INSERT INTO favorites (entry, cell_id, set_at) VALUES ('P1', '#01',"
            " '2026-01-01T00:00:00+00:00')"
        )
    db.close()


def test_legacy_ratings_and_favorites_go_to_the_first_configured_rater(tmp_path: Path) -> None:
    path = tmp_path / "curator.sqlite"
    _legacy_db(path)
    store = Store.open(path, raters=("Sven", "Anna"))
    rating = store.rating("P1", "#01", "Sven")
    assert rating is not None
    assert rating.rating.taste == 4
    assert store.rating("P1", "#01", "Anna") is None
    assert store.favorite("P1", "Sven") == "#01"
    assert store.favorite("P1", "Anna") is None


def test_legacy_ratings_latest_index_is_rebuilt_with_the_rater_column(tmp_path: Path) -> None:
    path = tmp_path / "curator.sqlite"
    _legacy_db(path)
    Store.open(path, raters=("Sven", "Anna")).close()
    db = sqlite3.connect(path)
    try:
        columns = [str(row[2]) for row in db.execute("PRAGMA index_info('ratings_latest')")]
    finally:
        db.close()
    assert columns == ["entry", "cell_id", "rater", "id"]


def test_opening_a_legacy_store_without_raters_configured_fails(tmp_path: Path) -> None:
    path = tmp_path / "curator.sqlite"
    _legacy_db(path)
    with pytest.raises(ValueError, match="STILLSTIFT_RATERS"):
        Store.open(path, raters=())


def test_opening_a_migrated_store_again_is_a_no_op(tmp_path: Path) -> None:
    path = tmp_path / "curator.sqlite"
    _legacy_db(path)
    Store.open(path, raters=("Sven", "Anna")).close()
    store = Store.open(path, raters=())
    assert store.rating("P1", "#01", "Sven") is not None


def test_a_fresh_store_needs_no_raters_to_open(tmp_path: Path) -> None:
    store = Store.open(tmp_path / "curator.sqlite", raters=())
    assert store.entry_counts() == []
