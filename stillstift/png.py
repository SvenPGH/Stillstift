"""Minimal PNG text-chunk writing, so a render keeps its infotext without an image library."""

from __future__ import annotations

import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
TEXT_CHUNKS = (b"tEXt", b"iTXt", b"zTXt")


def with_parameters(png: bytes, infotext: str) -> bytes:
    """Add a `parameters` iTXt chunk (the usual infotext key) unless the PNG already has one."""
    if not png.startswith(SIGNATURE):
        msg = "not a PNG"
        raise ValueError(msg)
    chunks = list(_chunks(png))
    if any(kind in TEXT_CHUNKS and data.startswith(b"parameters\0") for kind, data in chunks):
        return png
    text = b"parameters\0" + b"\0\0" + b"\0" + b"\0" + infotext.encode()
    out = [SIGNATURE]
    for kind, data in chunks:
        if kind == b"IDAT" and text:
            out.append(_chunk(b"iTXt", text))
            text = b""
        out.append(_chunk(kind, data))
    return b"".join(out)


def only_parameters(png: bytes, infotext: str) -> bytes:
    """Drop every text chunk the renderer wrote and keep only our own `parameters` chunk."""
    if not png.startswith(SIGNATURE):
        msg = "not a PNG"
        raise ValueError(msg)
    bare = SIGNATURE + b"".join(
        _chunk(kind, data) for kind, data in _chunks(png) if kind not in TEXT_CHUNKS
    )
    return with_parameters(bare, infotext)


def _chunks(png: bytes) -> list[tuple[bytes, bytes]]:
    chunks: list[tuple[bytes, bytes]] = []
    pos = len(SIGNATURE)
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos : pos + 4])
        chunks.append((png[pos + 4 : pos + 8], png[pos + 8 : pos + 8 + length]))
        pos += 12 + length
    return chunks


def _chunk(kind: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(kind + data)
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)
