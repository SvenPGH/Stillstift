r"""X5's picked pages, and X4's picks next to them: `uv run python -m lab.x5_sheets`.

Writes D:\Stillstift\christmas-set-x5.png (the 12 X5 picks, 4 x 3) and
D:\Stillstift\christmas-x4-vs-x5.png (each subject's X4 pick beside its X5 pick, three subjects
per row).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lab import x4_lines, x4_sheets, x5_lines
from lab.x2_sheets import ROOT, page
from lab.x4_sheets import COLUMNS, grid, picked
from stillstift.register import parse_line

if TYPE_CHECKING:
    from pathlib import Path

# The (set, cell) picked per subject, in subject order (see lab/x5-notes.md). The polar bear
# stays X4's #27: both X5 polar bears fill the igloo door solid grey.
PICKS = (
    ("X5", 13),
    ("X5", 2),
    ("X5", 15),
    ("X5", 4),
    ("X5", 17),
    ("X5", 18),
    ("X5", 19),
    ("X5", 20),
    ("X5", 9),
    ("X5", 22),
    ("X5", 11),
    ("X4", 27),
)
PAIRS_PER_ROW = 3


def main() -> int:
    names = [name for name, _ in x5_lines.SUBJECTS]
    seeds = {
        "X4": [parse_line(text).seed for text in x4_lines.lines()],
        "X5": [parse_line(text).seed for text in x5_lines.lines()],
    }
    x4 = picked("X4", x4_sheets.PICKS, names, seeds["X4"])
    x5: list[tuple[str, Path]] = [
        (
            f"{n + 1:02d} {names[n]} · {entry} #{cell:02d} · seed {seeds[entry][cell - 1]}",
            page(entry, cell),
        )
        for n, (entry, cell) in enumerate(PICKS)
    ]
    failed = grid(x5, COLUMNS, ROOT / "christmas-set-x5.png")
    pairs = [tile for pair in zip(x4, x5, strict=True) for tile in pair]
    return failed or grid(pairs, 2 * PAIRS_PER_ROW, ROOT / "christmas-x4-vs-x5.png")


if __name__ == "__main__":
    raise SystemExit(main())
