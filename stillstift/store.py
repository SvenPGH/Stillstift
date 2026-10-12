"""SQLite store of sets, cells, renders, ratings and favorites."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, Self, cast

from stillstift.kinds import Kind, kind_of, next_id
from stillstift.ratings import CellRating, Flag, OnTarget, Verdict, verdict_of

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

DATA_ENV = "STILLSTIFT_DATA"

SCHEMA = """
CREATE TABLE IF NOT EXISTS cells (
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
CREATE TABLE IF NOT EXISTS ratings (
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
    rated_at  TEXT NOT NULL,
    FOREIGN KEY (entry, cell_id) REFERENCES cells (entry, cell_id)
);
CREATE INDEX IF NOT EXISTS ratings_latest ON ratings (entry, cell_id, id);
CREATE TABLE IF NOT EXISTS favorites (
    entry   TEXT PRIMARY KEY,
    cell_id TEXT NOT NULL,
    set_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sets (
    entry TEXT PRIMARY KEY,
    name  TEXT NOT NULL DEFAULT '',
    date  TEXT NOT NULL DEFAULT '',
    tests TEXT NOT NULL DEFAULT ''
);
"""
# Every write to a watched table moves the change stamp, so open pages know to refresh.
STAMP = """
CREATE TABLE IF NOT EXISTS stamp (n INTEGER NOT NULL);
INSERT INTO stamp (n) SELECT 0 WHERE NOT EXISTS (SELECT 1 FROM stamp);
CREATE TRIGGER IF NOT EXISTS stamp_cells_insert AFTER INSERT ON cells
    BEGIN UPDATE stamp SET n = n + 1; END;
CREATE TRIGGER IF NOT EXISTS stamp_cells_update AFTER UPDATE ON cells
    BEGIN UPDATE stamp SET n = n + 1; END;
CREATE TRIGGER IF NOT EXISTS stamp_cells_delete AFTER DELETE ON cells
    BEGIN UPDATE stamp SET n = n + 1; END;
CREATE TRIGGER IF NOT EXISTS stamp_ratings_insert AFTER INSERT ON ratings
    BEGIN UPDATE stamp SET n = n + 1; END;
CREATE TRIGGER IF NOT EXISTS stamp_ratings_update AFTER UPDATE ON ratings
    BEGIN UPDATE stamp SET n = n + 1; END;
CREATE TRIGGER IF NOT EXISTS stamp_ratings_delete AFTER DELETE ON ratings
    BEGIN UPDATE stamp SET n = n + 1; END;
CREATE TRIGGER IF NOT EXISTS stamp_favorites_insert AFTER INSERT ON favorites
    BEGIN UPDATE stamp SET n = n + 1; END;
CREATE TRIGGER IF NOT EXISTS stamp_favorites_update AFTER UPDATE ON favorites
    BEGIN UPDATE stamp SET n = n + 1; END;
CREATE TRIGGER IF NOT EXISTS stamp_favorites_delete AFTER DELETE ON favorites
    BEGIN UPDATE stamp SET n = n + 1; END;
CREATE TRIGGER IF NOT EXISTS stamp_sets_insert AFTER INSERT ON sets
    BEGIN UPDATE stamp SET n = n + 1; END;
CREATE TRIGGER IF NOT EXISTS stamp_sets_update AFTER UPDATE ON sets
    BEGIN UPDATE stamp SET n = n + 1; END;
CREATE TRIGGER IF NOT EXISTS stamp_sets_delete AFTER DELETE ON sets
    BEGIN UPDATE stamp SET n = n + 1; END;
"""


def data_dir(env: Mapping[str, str] = os.environ) -> Path:
    """Return the folder of the SQLite file, renders and sheets: $STILLSTIFT_DATA, else data."""
    return Path(env.get(DATA_ENV, "data"))


DEFAULT_PATH = data_dir() / "curator.sqlite"


def natural_key(text: str) -> tuple[tuple[str | int, ...], str]:
    """Sort key putting digit runs in numeric order (#2 < #10); the raw text breaks ties."""
    parts = re.split(r"([0-9]+)", text)
    return tuple(int(p) if i % 2 else p for i, p in enumerate(parts)), text


@dataclass(frozen=True)
class Cell:
    entry: str
    cell_id: str
    dimension: str
    value: str
    prompt: str
    negative: str
    seed: int
    prediction: Verdict | None
    prediction_reason: str
    image_path: Path | None = None
    infotext: str | None = None
    rendered_at: datetime | None = None
    intent: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class StoredRating:
    rating: CellRating
    rated_at: datetime


@dataclass(frozen=True)
class ScoredCell:
    """A predicted cell's latest rating and the verdict it maps to."""

    entry: str
    cell_id: str
    prediction: Verdict
    verdict: Verdict
    reason: str
    rated_at: datetime
    rating: CellRating | None = None
    favorite: bool = False


@dataclass(frozen=True)
class CellVerdict:
    """A cell's latest rating, predicted or not, and the verdict it maps to."""

    entry: str
    cell_id: str
    verdict: Verdict
    reason: str
    rated_at: datetime
    rating: CellRating | None = None
    favorite: bool = False


@dataclass(frozen=True)
class SheetCell:
    """What a contact sheet needs of a cell: its verdict and its image, if it has one."""

    cell_id: str
    verdict: Verdict | None
    image: bytes | None
    taste: int | None = None


@dataclass(frozen=True)
class EntryCounts:
    entry: str
    rendered: int
    unrated: int
    cells: int
    name: str = ""
    date: str = ""
    tests: str = ""


@dataclass(frozen=True)
class SetName:
    """A set's name and date as its index line gives them."""

    name: str
    date: str


@dataclass(frozen=True)
class Prediction:
    entry: str
    cell_id: str
    verdict: Verdict


class Source(Protocol):
    """Where `just score` and `just sheet` read from: the local store or the hosted curator."""

    def scored_cells(self, entry: str | None = None) -> list[ScoredCell]: ...

    def sheet_cells(self, entry: str) -> list[SheetCell]: ...

    def close(self) -> None: ...


class Store:
    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    @classmethod
    def open(cls, path: Path = DEFAULT_PATH) -> Self:
        path.parent.mkdir(parents=True, exist_ok=True)
        # One connection per request, used in sequence, but FastAPI moves it between threads.
        db = sqlite3.connect(path, check_same_thread=False)
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript(SCHEMA)
        db.executescript(STAMP)
        return cls(db)

    def close(self) -> None:
        self._db.close()

    def stamp(self) -> int:
        """Return the change stamp: it moves on every write, through the API or a local CLI."""
        return int(self._db.execute("SELECT n FROM stamp").fetchone()[0])

    def add_cells(self, cells: Iterable[Cell]) -> None:
        with self._db:
            self._db.executemany(
                """
                INSERT INTO cells (entry, cell_id, dimension, value, prompt, negative, seed,
                                   prediction, prediction_reason, intent, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (entry, cell_id) DO UPDATE SET
                    dimension = excluded.dimension, value = excluded.value,
                    prompt = excluded.prompt, negative = excluded.negative, seed = excluded.seed,
                    prediction = coalesce(excluded.prediction, cells.prediction),
                    prediction_reason = CASE WHEN excluded.prediction IS NULL
                        THEN cells.prediction_reason ELSE excluded.prediction_reason END,
                    intent = excluded.intent, tags = excluded.tags
                """,
                [
                    (
                        c.entry,
                        c.cell_id,
                        c.dimension,
                        c.value,
                        c.prompt,
                        c.negative,
                        c.seed,
                        None if c.prediction is None else c.prediction.value,
                        c.prediction_reason,
                        c.intent,
                        json.dumps(list(c.tags)),
                    )
                    for c in cells
                ],
            )

    def entry_counts(self) -> list[EntryCounts]:
        """Per set, newest first: its rendered cells, those not rated yet and all its cells.

        Each with its name and date: the index's, else the day of its first render.
        """
        rows = self._db.execute(
            """
            WITH counted AS (
                SELECT c.entry,
                       count(c.rendered_at) AS rendered,
                       coalesce(sum(c.rendered_at IS NOT NULL AND r.cell_id IS NULL), 0) AS unrated,
                       count(*) AS cells,
                       substr(min(c.rendered_at), 1, 10) AS first
                FROM cells c
                LEFT JOIN (SELECT DISTINCT entry, cell_id FROM ratings) r USING (entry, cell_id)
                GROUP BY c.entry
            )
            SELECT e.entry, coalesce(k.rendered, 0), coalesce(k.unrated, 0), coalesce(k.cells, 0),
                   coalesce(s.name, ''), coalesce(nullif(s.date, ''), k.first, ''),
                   coalesce(s.tests, '')
            FROM (SELECT entry FROM cells UNION
                  SELECT entry FROM sets WHERE entry GLOB 'X[0-9]*' OR entry GLOB 'T[0-9]*') e
            LEFT JOIN counted k USING (entry)
            LEFT JOIN sets s USING (entry)
            """
        )
        counts = [
            EntryCounts(str(e), int(rendered), int(unrated), int(cells), str(n), str(d), str(t))
            for e, rendered, unrated, cells, n, d, t in rows
        ]
        return sorted(counts, key=lambda c: natural_key(c.entry), reverse=True)

    def put_set_names(self, names: Mapping[str, SetName]) -> int:
        """Keep each set's name and date from the index; return how many were given."""
        with self._db:
            self._db.executemany(
                """
                INSERT INTO sets (entry, name, date) VALUES (?, ?, ?)
                ON CONFLICT (entry) DO UPDATE SET name = excluded.name, date = excluded.date
                """,
                [(entry, n.name, n.date) for entry, n in names.items()],
            )
        return len(names)

    def create_set(self, kind: Kind, name: str, tests: str, on: date) -> str:
        """Create the next set of the kind, with its name and what it tests; return its id."""
        with self._db:
            taken = [
                str(row[0])
                for row in self._db.execute("SELECT entry FROM cells UNION SELECT entry FROM sets")
            ]
            entry = next_id(kind, taken)
            self._db.execute(
                "INSERT INTO sets (entry, name, date, tests) VALUES (?, ?, ?, ?)",
                (entry, name, on.isoformat(), tests),
            )
        return entry

    def put_predictions(self, predictions: Iterable[Prediction]) -> int:
        """Set the blind predictions of the cells the store holds; return how many it set."""
        with self._db:
            return sum(
                self._db.execute(
                    "UPDATE cells SET prediction = ? WHERE entry = ? AND cell_id = ?",
                    (p.verdict.value, p.entry, p.cell_id),
                ).rowcount
                for p in predictions
            )

    def rendered_cells(self) -> list[Cell]:
        """Every rendered cell of every set: newest set first, each in cell order."""
        rows = self._db.execute(
            """
            SELECT entry, cell_id, dimension, value, prompt, negative, seed, prediction,
                   prediction_reason, image_path, infotext, rendered_at, intent, tags
            FROM cells WHERE rendered_at IS NOT NULL
            """
        )
        cells = sorted((_cell(row) for row in rows), key=lambda c: natural_key(c.cell_id))
        return sorted(cells, key=lambda c: natural_key(c.entry), reverse=True)

    def cells(self, entry: str) -> list[Cell]:
        rows = self._db.execute(
            """
            SELECT entry, cell_id, dimension, value, prompt, negative, seed, prediction,
                   prediction_reason, image_path, infotext, rendered_at, intent, tags
            FROM cells WHERE entry = ?
            """,
            (entry,),
        )
        return sorted((_cell(row) for row in rows), key=lambda c: natural_key(c.cell_id))

    def cell(self, entry: str, cell_id: str) -> Cell | None:
        row = self._db.execute(
            """
            SELECT entry, cell_id, dimension, value, prompt, negative, seed, prediction,
                   prediction_reason, image_path, infotext, rendered_at, intent, tags
            FROM cells WHERE entry = ? AND cell_id = ?
            """,
            (entry, cell_id),
        ).fetchone()
        return None if row is None else _cell(row)

    def unrated_cells(self, entry: str) -> list[Cell]:
        rows = self._db.execute("SELECT cell_id FROM ratings WHERE entry = ?", (entry,))
        rated = {str(row[0]) for row in rows}
        return [c for c in self.cells(entry) if c.cell_id not in rated]

    def record_render(
        self, entry: str, cell_id: str, image_path: Path, infotext: str, rendered_at: datetime
    ) -> None:
        with self._db:
            updated = self._db.execute(
                """
                UPDATE cells SET image_path = ?, infotext = ?, rendered_at = ?
                WHERE entry = ? AND cell_id = ?
                """,
                (str(image_path), infotext, rendered_at.isoformat(), entry, cell_id),
            ).rowcount
        if not updated:
            raise KeyError((entry, cell_id))

    def clear_ratings(self, entry: str, cell_id: str) -> None:
        """Drop the cell's ratings and favorite mark, so a new render is rated afresh."""
        with self._db:
            self._db.execute(
                "DELETE FROM ratings WHERE entry = ? AND cell_id = ?", (entry, cell_id)
            )
            self._db.execute(
                "DELETE FROM favorites WHERE entry = ? AND cell_id = ?", (entry, cell_id)
            )

    def delete_entry(self, entry: str) -> list[Path] | None:
        """Delete the set's cells, ratings, favorite and name; return its renders' paths.

        None when the store holds no such set.
        """
        cells = self.cells(entry)
        if not cells:
            return None
        with self._db:
            self._db.execute("DELETE FROM ratings WHERE entry = ?", (entry,))
            self._db.execute("DELETE FROM favorites WHERE entry = ?", (entry,))
            self._db.execute("DELETE FROM cells WHERE entry = ?", (entry,))
            self._db.execute("DELETE FROM sets WHERE entry = ?", (entry,))
        return [c.image_path for c in cells if c.image_path is not None]

    def rate_cell(self, entry: str, cell_id: str, rating: CellRating, rated_at: datetime) -> None:
        self._require(entry, cell_id)
        with self._db:
            self._db.execute(
                """
                INSERT INTO ratings (entry, cell_id, taste, rows, render, flaws, book, on_target,
                                     reason, rated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (entry, cell_id, *_rating_values(rating), rated_at.isoformat()),
            )

    def rating(self, entry: str, cell_id: str) -> StoredRating | None:
        row = self._db.execute(
            "SELECT taste, rows, render, flaws, book, on_target, reason, rated_at"
            " FROM ratings WHERE entry = ? AND cell_id = ? ORDER BY id DESC LIMIT 1",
            (entry, cell_id),
        ).fetchone()
        return None if row is None else _stored(row)

    def unrate(self, entry: str, cell_id: str) -> CellRating | None:
        """Delete the cell's latest rating and return it; the one before, if any, counts again."""
        row = self._db.execute(
            "SELECT id, taste, rows, render, flaws, book, on_target, reason, rated_at"
            " FROM ratings WHERE entry = ? AND cell_id = ? ORDER BY id DESC LIMIT 1",
            (entry, cell_id),
        ).fetchone()
        if row is None:
            return None
        with self._db:
            self._db.execute("DELETE FROM ratings WHERE id = ?", (row[0],))
        return _stored(row[1:]).rating

    def favorites(self) -> dict[str, str]:
        """Every set's favorite cell, by set."""
        return {
            str(r[0]): str(r[1]) for r in self._db.execute("SELECT entry, cell_id FROM favorites")
        }

    def favorite(self, entry: str) -> str | None:
        row = self._db.execute("SELECT cell_id FROM favorites WHERE entry = ?", (entry,)).fetchone()
        return None if row is None else str(row[0])

    def set_favorite(self, entry: str, cell_id: str | None, set_at: datetime) -> None:
        """Make the cell the set's one favorite; None clears it."""
        if cell_id is None:
            with self._db:
                self._db.execute("DELETE FROM favorites WHERE entry = ?", (entry,))
            return
        self._require(entry, cell_id)
        with self._db:
            self._db.execute(
                """
                INSERT INTO favorites (entry, cell_id, set_at) VALUES (?, ?, ?)
                ON CONFLICT (entry) DO UPDATE SET cell_id = excluded.cell_id,
                                                  set_at = excluded.set_at
                """,
                (entry, cell_id, set_at.isoformat()),
            )

    def scored_cells(self, entry: str | None = None) -> list[ScoredCell]:
        """Predicted page cells with a rating, oldest rating first, paired with the prediction."""
        rows = self._db.execute(
            "SELECT entry, cell_id, prediction FROM cells"
            " WHERE prediction IS NOT NULL AND (? IS NULL OR entry = ?)",
            (entry, entry),
        )
        predictions = {(str(r[0]), str(r[1])): Verdict(str(r[2])) for r in rows}
        return [
            ScoredCell(
                v.entry,
                v.cell_id,
                predictions[(v.entry, v.cell_id)],
                v.verdict,
                v.reason,
                v.rated_at,
                v.rating,
                v.favorite,
            )
            for v in self.verdicts(entry)
            if (v.entry, v.cell_id) in predictions and kind_of(v.entry) == "P"
        ]

    def verdicts(self, entry: str | None = None) -> list[CellVerdict]:
        """Every rated cell's latest rating and its verdict, oldest first."""
        rows = self._db.execute(
            """
            SELECT r.entry, r.cell_id, r.taste, r.rows, r.render, r.flaws, r.book, r.on_target,
                   r.reason, r.rated_at
            FROM ratings r
            WHERE r.id = (SELECT max(id) FROM ratings s
                          WHERE s.entry = r.entry AND s.cell_id = r.cell_id)
              AND (? IS NULL OR r.entry = ?)
            """,
            (entry, entry),
        )
        favorites = self.favorites()
        latest: list[CellVerdict] = []
        for row in rows:
            entry_id, cell_id, stored = str(row[0]), str(row[1]), _stored(row[2:])
            rating = stored.rating
            latest.append(
                CellVerdict(
                    entry_id,
                    cell_id,
                    verdict_of(rating),
                    rating.reason,
                    stored.rated_at,
                    rating,
                    favorites.get(entry_id) == cell_id,
                )
            )
        return sorted(latest, key=lambda v: (v.rated_at, v.entry, v.cell_id))

    def sheet_cells(self, entry: str) -> list[SheetCell]:
        """Return the set's cells in order, each with its verdict, Liked stars and image."""
        judged = {v.cell_id: v for v in self.verdicts(entry)}
        sheet: list[SheetCell] = []
        for cell in self.cells(entry):
            found = judged.get(cell.cell_id)
            path = cell.image_path
            image = path.read_bytes() if path is not None and path.is_file() else None
            verdict = None if found is None else found.verdict
            taste = None if found is None or found.rating is None else found.rating.taste
            sheet.append(SheetCell(cell.cell_id, verdict, image, taste))
        return sheet

    def _require(self, entry: str, cell_id: str) -> None:
        found = self._db.execute(
            "SELECT 1 FROM cells WHERE entry = ? AND cell_id = ?", (entry, cell_id)
        ).fetchone()
        if found is None:
            raise KeyError((entry, cell_id))


def _cell(row: tuple[object, ...]) -> Cell:
    (
        entry,
        cell_id,
        dimension,
        value,
        prompt,
        negative,
        seed,
        prediction,
        prediction_reason,
        image_path,
        infotext,
        rendered_at,
        intent,
        tags,
    ) = row
    return Cell(
        entry=str(entry),
        cell_id=str(cell_id),
        dimension=str(dimension),
        value=str(value),
        prompt=str(prompt),
        negative=str(negative),
        seed=int(str(seed)),
        prediction=None if prediction is None else Verdict(str(prediction)),
        prediction_reason=str(prediction_reason),
        image_path=None if image_path is None else Path(str(image_path)),
        infotext=None if infotext is None else str(infotext),
        rendered_at=None if rendered_at is None else datetime.fromisoformat(str(rendered_at)),
        intent=str(intent),
        tags=tuple(str(t) for t in cast("list[str]", json.loads(str(tags)))),
    )


def _rating_values(rating: CellRating) -> tuple[object, ...]:
    def text(value: Flag | OnTarget | None) -> str | None:
        return None if value is None else value.value

    return (
        rating.taste,
        json.dumps(rating.rows),
        rating.render,
        json.dumps(list(rating.flaws)),
        text(rating.book),
        text(rating.on_target),
        rating.reason,
    )


def _stored(row: Sequence[object]) -> StoredRating:
    taste, rows, render, flaws, book, on_target, reason, rated_at = row
    set_rows = cast("dict[str, int]", json.loads(str(rows)))
    return StoredRating(
        CellRating(
            taste=int(str(taste)),
            rows={str(k): int(v) for k, v in set_rows.items()},
            render=None if render is None else int(str(render)),
            flaws=tuple(str(f) for f in cast("list[str]", json.loads(str(flaws)))),
            book=None if book is None else Flag(str(book)),
            on_target=None if on_target is None else OnTarget(str(on_target)),
            reason=str(reason),
        ),
        datetime.fromisoformat(str(rated_at)),
    )
