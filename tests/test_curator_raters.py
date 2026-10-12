"""The curator API's rater handling: required on writes, validated, scoped on reads."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from fastapi.testclient import TestClient

from stillstift.curator import create_app
from stillstift.store import Cell, Store

if TYPE_CHECKING:
    import httpx

NOW = datetime(2026, 1, 1, tzinfo=UTC)
RATERS = ("Sven", "Anna")


class _Client(Protocol):
    """The TestClient calls a test makes; typed by hand since starlette ships them untyped."""

    def get(self, url: str, *, params: dict[str, str] | None = None) -> httpx.Response: ...

    def post(
        self, url: str, *, params: dict[str, str] | None = None, json: object = None
    ) -> httpx.Response: ...

    def put(
        self, url: str, *, params: dict[str, str] | None = None, json: object = None
    ) -> httpx.Response: ...


def _client(db: Path) -> _Client:
    app = create_app(db=db, now=lambda: NOW, raters=RATERS)
    return cast("_Client", TestClient(app))


def _rendered(db: Path, entry: str = "P1", cell_id: str = "#01") -> None:
    store = Store.open(db, raters=RATERS)
    try:
        store.add_cells(
            [
                Cell(
                    entry=entry,
                    cell_id=cell_id,
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
        store.record_render(entry, cell_id, Path("render.png"), "infotext", NOW)
    finally:
        store.close()


def test_raters_route_lists_the_configured_names(tmp_path: Path) -> None:
    client = _client(tmp_path / "curator.sqlite")
    assert client.get("/api/raters").json() == ["Sven", "Anna"]


def test_rating_without_a_rater_is_rejected(tmp_path: Path) -> None:
    db = tmp_path / "curator.sqlite"
    _rendered(db)
    client = _client(db)
    response = client.post("/api/entries/P1/cells/%2301/rating", json={"taste": 5})
    assert response.status_code == 400


def test_rating_with_an_unknown_rater_is_rejected(tmp_path: Path) -> None:
    db = tmp_path / "curator.sqlite"
    _rendered(db)
    client = _client(db)
    response = client.post(
        "/api/entries/P1/cells/%2301/rating", params={"rater": "Mallory"}, json={"taste": 5}
    )
    assert response.status_code == 422


def test_each_raters_rating_is_kept_apart(tmp_path: Path) -> None:
    db = tmp_path / "curator.sqlite"
    _rendered(db)
    client = _client(db)
    client.post("/api/entries/P1/cells/%2301/rating", params={"rater": "Sven"}, json={"taste": 5})
    client.post("/api/entries/P1/cells/%2301/rating", params={"rater": "Anna"}, json={"taste": 2})

    as_sven = client.get("/api/entries/P1/cells", params={"rater": "Sven"}).json()
    assert as_sven[0]["rating"]["taste"] == 5
    assert as_sven[0]["others"] == [{"rater": "Anna", "taste": 2, "verdict": "kill"}]

    as_anna = client.get("/api/entries/P1/cells", params={"rater": "Anna"}).json()
    assert as_anna[0]["rating"]["taste"] == 2
    assert as_anna[0]["others"] == [{"rater": "Sven", "taste": 5, "verdict": "fav"}]


def test_without_a_rater_every_configured_rater_shows_as_an_other(tmp_path: Path) -> None:
    db = tmp_path / "curator.sqlite"
    _rendered(db)
    client = _client(db)
    client.post("/api/entries/P1/cells/%2301/rating", params={"rater": "Sven"}, json={"taste": 5})

    unset = client.get("/api/entries/P1/cells").json()
    assert unset[0]["rating"] is None
    assert unset[0]["others"] == [{"rater": "Sven", "taste": 5, "verdict": "fav"}]


def test_favorites_are_kept_per_rater(tmp_path: Path) -> None:
    db = tmp_path / "curator.sqlite"
    _rendered(db)
    client = _client(db)
    response = client.put(
        "/api/entries/P1/favorite", params={"rater": "Sven"}, json={"cell": "#01"}
    )
    assert response.status_code == 204

    as_sven = client.get("/api/entries/P1/cells", params={"rater": "Sven"}).json()
    as_anna = client.get("/api/entries/P1/cells", params={"rater": "Anna"}).json()
    assert as_sven[0]["favorite"] is True
    assert as_anna[0]["favorite"] is False


def test_favorite_without_a_rater_is_rejected(tmp_path: Path) -> None:
    db = tmp_path / "curator.sqlite"
    _rendered(db)
    client = _client(db)
    response = client.put("/api/entries/P1/favorite", json={"cell": "#01"})
    assert response.status_code == 400


def test_entries_unrated_count_is_scoped_to_the_rater(tmp_path: Path) -> None:
    db = tmp_path / "curator.sqlite"
    _rendered(db)
    client = _client(db)
    client.post("/api/entries/P1/cells/%2301/rating", params={"rater": "Sven"}, json={"taste": 5})

    by_sven = {e["entry"]: e for e in client.get("/api/entries", params={"rater": "Sven"}).json()}
    by_anna = {e["entry"]: e for e in client.get("/api/entries", params={"rater": "Anna"}).json()}
    assert by_sven["P1"]["unrated"] == 0
    assert by_anna["P1"]["unrated"] == 1


def test_all_cells_overview_merges_every_raters_rating(tmp_path: Path) -> None:
    db = tmp_path / "curator.sqlite"
    _rendered(db)
    client = _client(db)
    client.post("/api/entries/P1/cells/%2301/rating", params={"rater": "Sven"}, json={"taste": 5})
    client.post("/api/entries/P1/cells/%2301/rating", params={"rater": "Anna"}, json={"taste": 1})

    cells = client.get("/api/cells").json()
    assert cells[0]["rating"]["taste"] == 3
