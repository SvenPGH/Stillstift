r"""X4's picked pages on one sheet: `uv run python -m lab.x4_sheets`.

Writes D:\Stillstift\christmas-set.png: the 12 subjects, each at the cell picked in
lab/x4-notes.md, 4 columns x 3 rows, each tile labelled with its subject, cell and seed.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from lab.x2_sheets import BACKGROUND, INK, ROOT, page
from lab.x4_lines import SUBJECTS, lines
from stillstift.register import parse_line

if TYPE_CHECKING:
    from pathlib import Path

# The cell picked per subject, in subject order (see lab/x4-notes.md).
PICKS = (1, 2, 15, 4, 5, 6, 7, 20, 9, 10, 11, 27)
COLUMNS = 4
TILE_WIDTH = 440
LABEL = 30


def grid(tiles: list[tuple[str, Path]], columns: int, out: Path) -> int:
    """Lay labelled pages out row by row; 1 when a page is missing."""
    missing = [str(path) for _, path in tiles if not path.is_file()]
    if missing:
        sys.stderr.write(f"missing: {', '.join(missing)}\n")
        return 1
    with Image.open(tiles[0][1]) as first:
        tile_height = round(TILE_WIDTH * first.height / first.width)
    rows = -(-len(tiles) // columns)
    canvas = Image.new("RGB", (TILE_WIDTH * columns, (tile_height + LABEL) * rows), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)
    for index, (label, path) in enumerate(tiles):
        x = (index % columns) * TILE_WIDTH
        y = (index // columns) * (tile_height + LABEL)
        draw.text((x + 8, y + 6), label, INK, font)
        with Image.open(path) as image:
            tile = image.convert("RGB")
        tile.thumbnail((TILE_WIDTH, tile_height))
        canvas.paste(tile, (x, y + LABEL))
    canvas.save(out)
    sys.stdout.write(f"{out}\n")
    return 0


def picked(
    entry: str, picks: tuple[int, ...], names: list[str], seeds: list[int]
) -> list[tuple[str, Path]]:
    """Label each subject's picked cell: `<nn> <subject> · <entry> #<cell> · seed <seed>`."""
    return [
        (
            f"{n + 1:02d} {names[n]} · {entry} #{cell:02d} · seed {seeds[cell - 1]}",
            page(entry, cell),
        )
        for n, cell in enumerate(picks)
    ]


def main() -> int:
    seeds = [parse_line(text).seed for text in lines()]
    names = [name for name, _ in SUBJECTS]
    return grid(picked("X4", PICKS, names, seeds), COLUMNS, ROOT / "christmas-set.png")


if __name__ == "__main__":
    raise SystemExit(main())
