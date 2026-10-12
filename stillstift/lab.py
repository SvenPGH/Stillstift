"""`just lab <X|T> "<name>" --tests "<what>"`: create an experiment or a test and print its id.

On the hosted curator when one is set up, in the local store otherwise, with the next id of the
kind, as the Experiments page would.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from contextlib import closing
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from stillstift.curator import CuratorClient, CuratorError
from stillstift.store import DEFAULT_PATH, Store

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def create(kind: Literal["X", "T"], name: str, tests: str, db: Path) -> tuple[str, str]:
    """Create the set; return its id and where it was created."""
    client = CuratorClient.from_env()
    if client is None:
        with closing(Store.open(db)) as store:
            return store.create_set(kind, name, tests, datetime.now(UTC).date()), "the local store"
    with closing(client):
        return client.create_set(kind, name, tests), client.base_url


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="just lab", description=__doc__)
    parser.add_argument("kind", choices=["X", "T"], help="X an experiment, T a test")
    parser.add_argument("name", help="the set's name, e.g. 'Thicker outlines'")
    parser.add_argument("--tests", required=True, help="what it tests, in one line")
    return parser


def main(argv: Sequence[str] | None = None, db: Path = DEFAULT_PATH) -> int:
    args = _parser().parse_args(argv)
    kind: Literal["X", "T"] = "X" if args.kind == "X" else "T"
    name, tests = str(args.name).strip(), str(args.tests).strip()
    if not name:
        sys.stderr.write("lab: a set needs a name\n")
        return 1
    try:
        entry, where = create(kind, name, tests, db)
    except (OSError, sqlite3.Error, CuratorError) as error:
        sys.stderr.write(f"lab: {error}\n")
        return 1
    lines = f"lab/{entry.lower()}.txt"
    sys.stdout.write(
        f"{entry} · {name} → {where}\n"
        f"next: write {lines}, one --prompt … --negative_prompt … --seed … line per cell, "
        f"then just render {entry} --lines {lines}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
