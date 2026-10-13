r"""X2's sheets and page copies: `uv run python -m lab.x2_sheets`.

Writes D:\Stillstift\probe-2-sheet.png (X2's four arms x four subjects), probe-2-compare.png
(X1's B row above X2's arms) and copies X2's pages to D:\Stillstift\probe-2\ by arm and subject.
Reads the raw ComfyUI PNGs from STILLSTIFT_COMFY_OUTPUT (D:\Stillstift\outputs by default).
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"D:\Stillstift")
OUTPUTS = Path(os.environ.get("STILLSTIFT_COMFY_OUTPUT") or ROOT / "outputs")
SUBJECTS = ("hedgehogs", "oldtown", "turtle", "mandala")
# X2's arms in lab/x2.txt order, four cells each: (short name for files, row label).
ARMS = (
    ("BQ", "B+Q · sdxl-ax + quality tags"),
    ("KT", "K-T · Krea 2, X1 tag prompts"),
    ("K", "K · Krea 2, prose"),
    ("KQ", "K+Q · Krea 2, prose + quality"),
)
TILE_WIDTH = 384
LABEL_WIDTH = 220
HEADER = 36
BACKGROUND = (18, 17, 16)
INK = (236, 231, 225)


def page(entry: str, number: int) -> Path:
    return OUTPUTS / f"{entry}_{number:02d}_00001_.png"


def x2_rows() -> list[tuple[str, list[Path]]]:
    return [
        (label, [page("X2", arm * 4 + subject + 1) for subject in range(4)])
        for arm, (_, label) in enumerate(ARMS)
    ]


def sheet(rows: list[tuple[str, list[Path]]], out: Path) -> None:
    """Lay the rows out under one header of subjects, each row labelled on its left."""
    with Image.open(rows[0][1][0]) as first:
        tile_height = round(TILE_WIDTH * first.height / first.width)
    width = LABEL_WIDTH + TILE_WIDTH * len(SUBJECTS)
    canvas = Image.new("RGB", (width, HEADER + tile_height * len(rows)), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)
    for column, subject in enumerate(SUBJECTS, start=1):
        draw.text(
            (LABEL_WIDTH + (column - 1) * TILE_WIDTH + 8, 8), f"{column} {subject}", INK, font
        )
    for row, (label, paths) in enumerate(rows):
        top = HEADER + row * tile_height
        draw.multiline_text((8, top + 8), label.replace(" · ", "\n"), INK, font, spacing=6)
        for column, path in enumerate(paths):
            with Image.open(path) as image:
                tile = image.convert("RGB")
            tile.thumbnail((TILE_WIDTH, tile_height))
            canvas.paste(tile, (LABEL_WIDTH + column * TILE_WIDTH, top))
    canvas.save(out)
    sys.stdout.write(f"{out}\n")


def copy_pages(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for arm, (short, _) in enumerate(ARMS):
        for subject, name in enumerate(SUBJECTS):
            target = folder / f"{short}-{subject + 1}-{name}.png"
            shutil.copyfile(page("X2", arm * 4 + subject + 1), target)
    sys.stdout.write(f"{folder}: {len(ARMS) * len(SUBJECTS)} pages\n")


def main() -> int:
    rows = x2_rows()
    x1_b = ("X1 B · sdxl-ax, no quality tags", [page("X1", n) for n in range(5, 9)])
    missing = [str(p) for _, paths in [x1_b, *rows] for p in paths if not p.is_file()]
    if missing:
        sys.stderr.write(f"missing: {', '.join(missing)}\n")
        return 1
    sheet(rows, ROOT / "probe-2-sheet.png")
    sheet([x1_b, *rows], ROOT / "probe-2-compare.png")
    copy_pages(ROOT / "probe-2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
