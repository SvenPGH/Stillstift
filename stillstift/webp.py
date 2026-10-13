"""Thumbnails for grids and pickers, and previews for phones: WebPs cached beside each render.

Renders themselves stay lossless PNG: a page is line art and goes to print. A preview is the page
at phone-screen size, a fraction of the PNG's bytes on mobile data.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

THUMB_WIDTH = 480
PREVIEW_WIDTH = 1080
WIDTHS = (THUMB_WIDTH, PREVIEW_WIDTH)
THUMB_QUALITY = 80


def thumb_path(image: Path, width: int = THUMB_WIDTH) -> Path:
    """Return where a render's WebP lives: `thumbs/<cell>.webp`, `thumbs/<cell>.<width>.webp`."""
    name = image.stem if width == THUMB_WIDTH else f"{image.stem}.{width}"
    return image.parent / "thumbs" / f"{name}.webp"


def thumb_of(image: Path, width: int = THUMB_WIDTH) -> Path:
    """Return the render's WebP at most `width` wide, made first when missing or stale."""
    thumb = thumb_path(image, width)
    if thumb.is_file() and thumb.stat().st_mtime_ns >= image.stat().st_mtime_ns:
        return thumb
    thumb.parent.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=thumb.parent, suffix=".webp", delete=False) as out:
        made = Path(out.name)
        try:
            with Image.open(image) as source:
                small = source.convert("RGB")
            small.thumbnail((width, width * 4))
            small.save(out, format="WEBP", quality=THUMB_QUALITY, method=4)
        except OSError:
            made.unlink()
            raise
    return made.replace(thumb)
