"""`just sheet <entry>`: one labelled contact sheet of an entry's cells, read after rating."""

from __future__ import annotations

import argparse
import io
import math
import sys
from contextlib import closing
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from stillstift.curator import CuratorError, open_source
from stillstift.store import Verdict, data_dir

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from stillstift.store import Source

LONG_SIDE = 1568
LABEL_HEIGHT = 28
DEFAULT_ASPECT = 4 / 3
SHEETS = data_dir() / "sheets"
BACKGROUND = (18, 17, 16)
BANDS: dict[Verdict | None, tuple[int, int, int]] = {
    Verdict.FAV: (232, 182, 76),
    Verdict.KEEP: (127, 181, 138),
    Verdict.ISSUE: (217, 137, 74),
    Verdict.KILL: (210, 95, 95),
    None: (70, 66, 62),
}


@dataclass(frozen=True)
class Grid:
    columns: int
    rows: int
    tile_width: int
    tile_height: int

    @property
    def width(self) -> int:
        return self.columns * self.tile_width

    @property
    def height(self) -> int:
        return self.rows * (self.tile_height + LABEL_HEIGHT)


def grid(count: int, aspect: float = DEFAULT_ASPECT) -> Grid:
    """Pick the column count that gives the largest tiles within LONG_SIDE."""
    best: Grid | None = None
    for columns in range(1, count + 1):
        rows = math.ceil(count / columns)
        tile_width = math.floor(
            min(LONG_SIDE / columns, (LONG_SIDE / rows - LABEL_HEIGHT) / aspect)
        )
        if tile_width > 0 and (best is None or tile_width > best.tile_width):
            best = Grid(columns, rows, tile_width, math.floor(tile_width * aspect))
    if best is None:
        msg = f"{count} cells don't fit a {LONG_SIDE}px sheet"
        raise ValueError(msg)
    return best


def tile_label(
    cell_id: str, verdict: Verdict | None, *, rendered: bool, taste: int | None = None
) -> str:
    if not rendered:
        return f"{cell_id} · not rendered"
    if verdict is None:
        return f"{cell_id} · unrated"
    liked = "" if taste is None else f"Liked {taste} · "
    return f"{cell_id} · {liked}{verdict.value.upper()}"


def make_sheet(entry: str, source: Source, out_dir: Path = SHEETS) -> Path:
    cells = source.sheet_cells(entry)
    if not cells:
        raise KeyError(entry)
    images = [c.image for c in cells if c.image is not None]
    aspect = DEFAULT_ASPECT
    if images:
        with Image.open(io.BytesIO(images[0])) as first:
            aspect = first.height / first.width
    layout = grid(len(cells), aspect)
    sheet = Image.new("RGB", (layout.width, layout.height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=LABEL_HEIGHT - 10)
    for index, cell in enumerate(cells):
        x = (index % layout.columns) * layout.tile_width
        y = (index // layout.columns) * (layout.tile_height + LABEL_HEIGHT)
        rendered = cell.image is not None
        if cell.image is not None:
            with Image.open(io.BytesIO(cell.image)) as image:
                tile = image.convert("RGB")
                tile.thumbnail((layout.tile_width, layout.tile_height))
                offset = (
                    x + (layout.tile_width - tile.width) // 2,
                    y + (layout.tile_height - tile.height) // 2,
                )
                sheet.paste(tile, offset)
        verdict = cell.verdict
        band_top = y + layout.tile_height
        draw.rectangle(
            (x, band_top, x + layout.tile_width - 1, band_top + LABEL_HEIGHT - 1),
            fill=BANDS[verdict],
        )
        draw.text(
            (x + 6, band_top + 4),
            tile_label(cell.cell_id, verdict, rendered=rendered, taste=cell.taste),
            fill=BACKGROUND if verdict else (236, 231, 225),
            font=font,
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{entry}.png"
    sheet.save(out)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="just sheet", description=__doc__)
    parser.add_argument("entry", help="register entry, e.g. P3")
    args = parser.parse_args(argv)
    try:
        with closing(open_source()) as source:
            out = make_sheet(args.entry, source)
    except KeyError:
        sys.stderr.write(f"sheet: {args.entry} has no cells\n")
        return 1
    except CuratorError as error:
        sys.stderr.write(f"sheet: {error}\n")
        return 1
    sys.stdout.write(f"{out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
