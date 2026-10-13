r"""X4's picked pages on one sheet: `uv run python -m lab.x4_sheets`.

Writes D:\Stillstift\christmas-set.png: the 12 subjects, each at the seed picked in
lab/x4-notes.md, 4 columns x 3 rows, each tile labelled with its subject, cell and seed.
"""

from __future__ import annotations

import sys

from PIL import Image, ImageDraw, ImageFont

from lab.x2_sheets import BACKGROUND, INK, ROOT, page
from lab.x4_lines import SEEDS, SUBJECTS

# The seed row picked per subject, in subject order: 0 for seed 201+n, 1 for 301+n.
PICKS = (0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0)
COLUMNS = 4
TILE_WIDTH = 440
LABEL = 30


def main() -> int:
    picked = [
        (n, SEEDS[row] + n, page("X4", row * len(SUBJECTS) + n + 1)) for n, row in enumerate(PICKS)
    ]
    missing = [str(path) for _, _, path in picked if not path.is_file()]
    if missing:
        sys.stderr.write(f"missing: {', '.join(missing)}\n")
        return 1
    with Image.open(picked[0][2]) as first:
        tile_height = round(TILE_WIDTH * first.height / first.width)
    rows = -(-len(picked) // COLUMNS)
    size = (TILE_WIDTH * COLUMNS, (tile_height + LABEL) * rows)
    canvas = Image.new("RGB", size, BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)
    for index, (n, seed, path) in enumerate(picked):
        x = (index % COLUMNS) * TILE_WIDTH
        y = (index // COLUMNS) * (tile_height + LABEL)
        label = f"{n + 1:02d} {SUBJECTS[n][0]} · {path.stem.split('_')[1]} · seed {seed}"
        draw.text((x + 8, y + 6), label, INK, font)
        with Image.open(path) as image:
            tile = image.convert("RGB")
        tile.thumbnail((TILE_WIDTH, tile_height))
        canvas.paste(tile, (x, y + LABEL))
    out = ROOT / "christmas-set.png"
    canvas.save(out)
    sys.stdout.write(f"{out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
