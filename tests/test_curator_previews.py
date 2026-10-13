"""The phone-sized preview: served as a small WebP, named in the cell view, deleted with its set."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, cast

from fastapi.testclient import TestClient
from PIL import Image

from stillstift.curator import create_app
from stillstift.store import Cell, Store
from stillstift.webp import PREVIEW_WIDTH, thumb_path

if TYPE_CHECKING:
    from pathlib import Path

    import httpx

NOW = datetime(2026, 1, 1, tzinfo=UTC)
RATERS = ("Sven", "Anna")


class _Client(Protocol):
    """The TestClient calls a test makes; typed by hand since starlette ships them untyped."""

    def get(self, url: str) -> httpx.Response: ...

    def delete(self, url: str) -> httpx.Response: ...


def _rendered(tmp_path: Path, width: int) -> tuple[_Client, Path]:
    """Render P1 #01 `width` wide into a fresh store; return a curator client over it."""
    db = tmp_path / "curator.sqlite"
    render = tmp_path / "renders" / "P1" / "#01.png"
    render.parent.mkdir(parents=True)
    Image.new("RGB", (width, width * 4 // 3), "white").save(render)
    store = Store.open(db, raters=RATERS)
    try:
        store.add_cells(
            [
                Cell(
                    entry="P1",
                    cell_id="#01",
                    dimension="",
                    value="",
                    prompt="a cat",
                    negative="",
                    seed=1,
                    prediction=None,
                    prediction_reason="",
                )
            ]
        )
        store.record_render("P1", "#01", render, "infotext", NOW)
    finally:
        store.close()
    app = create_app(db=db, now=lambda: NOW, raters=RATERS)
    return cast("_Client", TestClient(app)), render


def test_the_cell_view_names_its_preview(tmp_path: Path) -> None:
    client, _ = _rendered(tmp_path, 600)
    (cell,) = client.get("/api/entries/P1/cells").json()
    assert cell["preview"].startswith("/api/entries/P1/cells/%2301/preview?v=")


def test_the_preview_is_a_webp_at_most_the_preview_width(tmp_path: Path) -> None:
    client, _ = _rendered(tmp_path, 2000)
    response = client.get("/api/entries/P1/cells/%2301/preview")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    with Image.open(io.BytesIO(response.content)) as preview:
        assert preview.width == PREVIEW_WIDTH


def test_the_preview_and_the_thumbnail_are_kept_apart(tmp_path: Path) -> None:
    client, render = _rendered(tmp_path, 2000)
    client.get("/api/entries/P1/cells/%2301/thumb")
    client.get("/api/entries/P1/cells/%2301/preview")
    assert thumb_path(render).is_file()
    assert thumb_path(render, PREVIEW_WIDTH).is_file()
    assert thumb_path(render) != thumb_path(render, PREVIEW_WIDTH)


def test_deleting_the_set_deletes_its_preview(tmp_path: Path) -> None:
    client, render = _rendered(tmp_path, 2000)
    client.get("/api/entries/P1/cells/%2301/preview")
    assert client.delete("/api/entries/P1").status_code == 204
    assert not thumb_path(render, PREVIEW_WIDTH).exists()
    assert not render.parent.exists()


def test_a_cell_without_a_render_has_no_preview(tmp_path: Path) -> None:
    client, _ = _rendered(tmp_path, 600)
    assert client.get("/api/entries/P1/cells/%2302/preview").status_code == 404
