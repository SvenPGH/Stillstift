"""Check a lab set's rendered cells against its lines.

`uv run python -m lab.store_check X4 lab/x4.txt`. For every line: the cell is in the store, its
image is on disk, and its prompt, negative, seed and profile match the line, both in the store
row and in the PNG's own infotext.
"""

from __future__ import annotations

import sys
from contextlib import closing
from pathlib import Path

from stillstift.comfy import load_profile, prompt_of
from stillstift.register import parse_infotext, parse_settings, png_infotext, read_lines
from stillstift.store import Store

USAGE_ARGS = 2


def problems(entry: str, lines: Path, store: Store) -> list[str]:
    held = {c.cell_id: c for c in store.cells(entry)}
    found: list[str] = []
    for cell, line in read_lines(entry, lines):
        stored = held.get(cell.cell_id)
        if stored is None or stored.image_path is None or not stored.image_path.is_file():
            found.append(f"{cell.cell_id}: not rendered")
            continue
        _, profile = load_profile(line.profile)
        text = png_infotext(stored.image_path.read_bytes())
        if (stored.prompt, stored.negative, stored.seed) != (cell.prompt, cell.negative, cell.seed):
            found.append(f"{cell.cell_id}: store row differs from its line")
        if parse_infotext(text) != (prompt_of(cell, profile), cell.negative, cell.seed):
            found.append(f"{cell.cell_id}: PNG infotext differs from its line")
        if dict(parse_settings(text)).get("profile") != line.profile:
            found.append(f"{cell.cell_id}: rendered with another profile")
    return found


def main(argv: list[str]) -> int:
    if len(argv) != USAGE_ARGS:
        sys.stderr.write("usage: python -m lab.store_check <entry> <lines file>\n")
        return 1
    entry, lines = argv[0], Path(argv[1])
    with closing(Store.open()) as store:
        found = problems(entry, lines, store)
    count = len(read_lines(entry, lines))
    for problem in found:
        sys.stdout.write(f"{entry} {problem}\n")
    sys.stdout.write(f"{entry}: {count} lines, {len(found)} problems\n")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
