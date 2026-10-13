r"""X3's comparison sheet and page copies: `uv run python -m lab.x3_sheets`.

Writes D:\Stillstift\probe-3-compare.png (X2's K+Q above X3's two LoRA strengths) and copies
X3's pages to D:\Stillstift\probe-3\ by strength and subject.
"""

from __future__ import annotations

import shutil
import sys

from lab.x2_sheets import ROOT, SUBJECTS, page, sheet

# (short name for files, row label, entry, first cell)
ROWS = (
    ("KQ", "X2 K+Q · no LoRA", "X2", 13),
    ("L06", "X3 · LoRA 0.6", "X3", 1),
    ("L10", "X3 · LoRA 1.0", "X3", 5),
)


def main() -> int:
    rows = [
        (label, [page(entry, first + n) for n in range(len(SUBJECTS))])
        for _, label, entry, first in ROWS
    ]
    missing = [str(p) for _, paths in rows for p in paths if not p.is_file()]
    if missing:
        sys.stderr.write(f"missing: {', '.join(missing)}\n")
        return 1
    sheet(rows, ROOT / "probe-3-compare.png")
    folder = ROOT / "probe-3"
    folder.mkdir(parents=True, exist_ok=True)
    for short, _, entry, first in ROWS[1:]:
        for n, subject in enumerate(SUBJECTS):
            shutil.copyfile(page(entry, first + n), folder / f"{short}-{n + 1}-{subject}.png")
    sys.stdout.write(f"{folder}: {2 * len(SUBJECTS)} pages\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
