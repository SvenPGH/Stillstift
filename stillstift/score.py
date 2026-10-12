"""`just score <entry>`: write ratings back to register/predictions.csv and report recall."""

from __future__ import annotations

import argparse
import csv
import sys
from contextlib import closing
from typing import TYPE_CHECKING

from stillstift.curator import CuratorError, open_source
from stillstift.register import PREDICTION_CODES, PREDS, RegisterError
from stillstift.scoring import Recall, hits, recall

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from stillstift.ratings import CellRating
    from stillstift.store import ScoredCell, Source

VERDICT_CODES = {verdict: code for code, verdict in PREDICTION_CODES.items()}
RATING_COLUMNS = ("taste", "rows", "render", "flaws", "book", "on_target", "favorite")
SCORE_COLUMNS = ("verdict", "reason", "taste_hit", "fav_hit", "issue_hit", *RATING_COLUMNS)
LAST = 30


def score_entry(entry: str, source: Source, preds: Path = PREDS) -> None:
    """Fill the set's score columns from its latest ratings; unrated cells are left blank.

    A file without the rating columns gains them, blank for every other set.
    """
    scored = {s.cell_id: s for s in source.scored_cells(entry=entry)}
    with preds.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    fields += [column for column in SCORE_COLUMNS if column not in fields]
    for row in rows:
        if row["entry"] == entry:
            row.update(_score_columns(scored.get(row["cell"])))
    with preds.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def report(entry: str, source: Source, last: int = LAST) -> str:
    entry_pairs = [(s.prediction, s.verdict) for s in source.scored_cells(entry=entry)]
    all_pairs = [(s.prediction, s.verdict) for s in source.scored_cells()]
    issue_hits = [hits(p, v).issue for p, v in entry_pairs]
    recent_issue_hits = [hits(p, v).issue for p, v in all_pairs[-last:]]
    return "\n".join(
        [
            f"{entry}: {_line(recall(entry_pairs), sum(issue_hits))}",
            f"last {last}: {_line(recall(all_pairs, last=last), sum(recent_issue_hits))}",
        ]
    )


def _score_columns(cell: ScoredCell | None) -> dict[str, str]:
    if cell is None:
        return dict.fromkeys(SCORE_COLUMNS, "")
    hit = hits(cell.prediction, cell.verdict)
    return {
        "verdict": VERDICT_CODES[cell.verdict],
        "reason": cell.reason,
        "taste_hit": str(int(hit.taste)),
        "fav_hit": str(int(hit.fav)),
        "issue_hit": str(int(hit.issue)),
        **_rating_columns(cell.rating),
        "favorite": "1" if cell.favorite else "",
    }


def _rating_columns(rating: CellRating | None) -> dict[str, str]:
    """Write a rating as CSV cells: rows as `lines:5 detail:4`, flaws joined by `;`."""
    if rating is None:
        return dict.fromkeys(RATING_COLUMNS, "")
    return {
        "taste": str(rating.taste),
        "rows": " ".join(f"{row}:{stars}" for row, stars in rating.rows.items()),
        "render": _text(rating.render),
        "flaws": ";".join(rating.flaws),
        "book": _text(rating.book),
        "on_target": _text(rating.on_target),
    }


def _text(value: object) -> str:
    return "" if value is None else str(value)


def _line(result: Recall, issue_hits: int) -> str:
    kills = _ratio(result.kills_called, result.kills, "kills")
    favs = _ratio(result.favs_called, result.favs, "favs")
    return (
        f"{result.scored} scored · kill recall {kills} · fav recall {favs}"
        f" · issue hits {issue_hits}"
    )


def _ratio(called: int, total: int, noun: str) -> str:
    if not total:
        return f"— (no {noun})"
    return f"{called}/{total} ({round(100 * called / total)}%)"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="just score", description=__doc__)
    parser.add_argument("entry", help="a page set, e.g. P3")
    args = parser.parse_args(argv)
    try:
        with closing(open_source()) as source:
            score_entry(args.entry, source)
            sys.stdout.write(report(args.entry, source) + "\n")
    except (CuratorError, RegisterError, OSError) as error:
        sys.stderr.write(f"score: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
