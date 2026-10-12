"""Thumbnails for grids and pickers: a small WebP cached beside each render.

Renders themselves stay lossless PNG: a page is line art and goes to print.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

THUMB_WIDTH = 480
THUMB_QUALITY = 80


def thumb_path(image: Path) -> Path:
    """Return where a render's thumbnail lives: `thumbs/<cell>.webp` beside it."""
    return image.parent / "thumbs" / f"{image.stem}.webp"


def thumb_of(image: Path) -> Path:
    """Return the render's thumbnail, made first when it is missing or older than the render."""
    thumb = thumb_path(image)
    if thumb.is_file() and thumb.stat().st_mtime_ns >= image.stat().st_mtime_ns:
        return thumb
    thumb.parent.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=thumb.parent, suffix=".webp", delete=False) as out:
        made = Path(out.name)
        try:
            with Image.open(image) as source:
                small = source.convert("RGB")
            small.thumbnail((THUMB_WIDTH, THUMB_WIDTH * 4))
            small.save(out, format="WEBP", quality=THUMB_QUALITY, method=4)
        except OSError:
            made.unlink()
            raise
    return made.replace(thumb)
