"""A set's kind, read from its id, and the ids of its cells.

`P3` a page set, `X2` an experiment, `T4` a test; cells are `#01`, `#02`… and a cell is cited as
`P3-#02`.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable

Kind = Literal["P", "X", "T"]
KINDS: dict[str, Kind] = {"P": "P", "X": "X", "T": "T"}
LAB: tuple[Kind, ...] = ("X", "T")
ENTRY = re.compile(r"(P|X|T)[0-9]+[a-z]?")
CELL = re.compile(r"#[0-9]{2,3}")
CELL_ARG = re.compile(r"#?([0-9]{1,3})")
NUMBER = re.compile(r"([0-9]+)")
REF = re.compile(r"((?:P|X|T)[0-9]+[a-z]?)-(#[0-9]{2,3})")


def kind_of(entry: str) -> Kind | None:
    """Return the set's kind, or None for an id of no kind."""
    found = ENTRY.fullmatch(entry)
    return None if found is None else KINDS[found[1]]


def is_lab(entry: str) -> bool:
    """Say whether the set is an experiment or a test: rated, never scored or counted."""
    return kind_of(entry) in LAB


def next_id(kind: Kind, taken: Iterable[str]) -> str:
    """Return the next id of the kind: the highest of that kind among `taken`, plus one."""
    numbers = [int(found[1]) for e in taken if kind_of(e) == kind and (found := NUMBER.search(e))]
    return f"{kind}{max(numbers, default=0) + 1}"


def valid_cell(cell: str) -> bool:
    return CELL.fullmatch(cell) is not None


def cell_id(number: int) -> str:
    """Return the id of the set's cell number `number`, counted from 1: `#01`."""
    return f"#{number:02d}"


def cell_arg(text: str) -> str | None:
    """Read a cell as typed on a command line, `3`, `03` or `#03`, as its id; None if not one."""
    found = CELL_ARG.fullmatch(text.strip())
    return None if found is None else cell_id(int(found[1]))


def cell_ref(text: str) -> tuple[str, str] | None:
    """Read a cited cell, `P3-#02`, as (entry, cell); None when the text cites none."""
    found = REF.fullmatch(text.strip())
    return None if found is None else (found[1], found[2])
