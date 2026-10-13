r"""Theme sets X6-X15 (lab/themes.yaml): write a set's lines, or its sheet of picks.

`uv run python -m lab.themes lines X6 lab/x6.txt` writes the 24 cell lines in X5's recipe: X4's
style block and negative (`lab.x4_lines.line`) with the set's theme word.
`uv run python -m lab.themes sheet X6` writes D:\Stillstift\set-X6.png from the set's picks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, TypeAdapter

from lab.x2_sheets import ROOT
from lab.x4_lines import line
from lab.x4_sheets import COLUMNS, grid, picked

THEMES = Path(__file__).with_name("themes.yaml")
SECOND_SEED = 100
USAGE = (
    "usage: python -m lab.themes lines <set> <out file>\n       python -m lab.themes sheet <set>\n"
)


class Theme(BaseModel):
    theme: str
    name: str
    subjects: list[tuple[str, str]]
    picks: list[int] = []


def themes() -> dict[str, Theme]:
    raw = yaml.safe_load(THEMES.read_text(encoding="utf-8"))
    return TypeAdapter(dict[str, Theme]).validate_python(raw)


def seeds(entry: str) -> list[int]:
    """Every cell's seed: 01-12 at <n>001+i, 13-24 at <n>101+i, for set X<n>."""
    first = int(entry.removeprefix("X")) * 1000 + 1
    count = len(themes()[entry].subjects)
    return [base + i for base in (first, first + SECOND_SEED) for i in range(count)]


def lines(entry: str) -> list[str]:
    theme = themes()[entry]
    texts = [text for _, text in theme.subjects] * 2
    return [line(text, seed, theme.theme) for text, seed in zip(texts, seeds(entry), strict=True)]


def sheet(entry: str) -> int:
    theme = themes()[entry]
    if len(theme.picks) != len(theme.subjects):
        sys.stderr.write(f"{entry}: picks has {len(theme.picks)} cells, not one per subject\n")
        return 1
    names = [name for name, _ in theme.subjects]
    tiles = picked(entry, tuple(theme.picks), names, seeds(entry))
    return grid(tiles, COLUMNS, ROOT / f"set-{entry}.png")


def main(argv: list[str]) -> int:
    match argv:
        case ["lines", entry, out]:
            written = lines(entry)
            Path(out).write_text("\n".join(written) + "\n", encoding="utf-8")
            sys.stdout.write(f"{len(written)} lines -> {out}\n")
            return 0
        case ["sheet", entry]:
            return sheet(entry)
        case _:
            sys.stderr.write(USAGE)
            return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
