"""Frame two X24 pages as finished-look mocks and add them to the set: `python -m lab.x24_mocks`.

#01 (bold) becomes day 2 and #12 (finer) day 24, so both line weights show in the frame. Each
mock keeps its source cell's infotext, so the curator files it under the same prompt and seed,
and goes up as #13 and #14 with an intent naming its source. The art is only Lanczos-scaled and
thresholded here; the print run puts the upscaler in front.
"""

from __future__ import annotations

import dataclasses
import io
import sys
from contextlib import closing
from pathlib import Path

from PIL import Image

from stillstift.curator import CuratorClient, CuratorError, HostedSource
from stillstift.frame import DPI, framed
from stillstift.png import only_parameters
from stillstift.register import RegisterError, cell_from_infotext, png_infotext

ENTRY = "X24"
OUT = Path("D:/Stillstift/X24")
# (source cell, day, mock cell)
MOCKS = (("#01", 2, "#13"), ("#12", 24, "#14"))


def main() -> int:
    client = CuratorClient.from_env()
    if client is None:
        sys.stderr.write("mocks: set STILLSTIFT_CURATOR_URL, _USER and _PASSWORD\n")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        with closing(client):
            cells = HostedSource(client).sheet_cells(ENTRY)
            images = {c.cell_id: c.image for c in cells}
            for source, day, mock in MOCKS:
                png = images.get(source)
                if png is None:
                    sys.stderr.write(f"mocks: {ENTRY} {source} has no image\n")
                    return 1
                infotext = png_infotext(png)
                with Image.open(io.BytesIO(png)) as art:
                    page = framed(art, day)
                buffer = io.BytesIO()
                page.save(buffer, format="PNG", dpi=(DPI, DPI))
                out = OUT / f"framed-day{day:02d}.png"
                out.write_bytes(buffer.getvalue())
                cell = dataclasses.replace(
                    cell_from_infotext(ENTRY, mock, infotext),
                    intent=f"Framed mock: {source} as day {day}, 8.5x11 in at 300 dpi",
                )
                client.upload(cell, only_parameters(buffer.getvalue(), infotext))
                sys.stdout.write(f"{ENTRY} {mock} ← {source} day {day} · {out}\n")
    except (CuratorError, RegisterError, OSError) as error:
        sys.stderr.write(f"mocks: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
