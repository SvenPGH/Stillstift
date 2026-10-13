"""The rating app: `just curate` on 127.0.0.1, or the hosted curator behind basic auth."""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, Self
from urllib.parse import quote

import httpx
import uvicorn
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

from stillstift.kinds import Kind, is_lab, kind_of, valid_cell
from stillstift.ratings import FLAWS, ROWS, CellRating, Flag, OnTarget, Verdict, misfits
from stillstift.register import (
    PREDS,
    RENDERS,
    RegisterError,
    Render,
    cell_from_infotext,
    delete_entry,
    image_url,
    parse_settings,
    parse_tags,
    png_infotext,
    preview_url,
    read_predictions,
    register_render,
    thumb_url,
)
from stillstift.store import (
    DEFAULT_PATH,
    RATERS_ENV,
    Cell,
    CellVerdict,
    Prediction,
    ScoredCell,
    SetName,
    SheetCell,
    Source,
    Store,
    raters_from_env,
)
from stillstift.webp import PREVIEW_WIDTH, THUMB_WIDTH, thumb_of

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence

    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.types import ASGIApp, Scope

STATIC = Path(__file__).parent / "static"
HOST = "127.0.0.1"
PORT = 8765
REVALIDATE = {"Cache-Control": "no-cache"}
PAGE_FILES = {
    "/": "index.html",
    "/dashboard": "dashboard.html",
    "/images": "images.html",
    "/experiments": "lab.html",
    "/tests": "lab.html",
}
AUTH_ENV = ("STILLSTIFT_AUTH_USER", "STILLSTIFT_AUTH_PASSWORD")
CURATOR_ENV = ("STILLSTIFT_CURATOR_URL", "STILLSTIFT_CURATOR_USER", "STILLSTIFT_CURATOR_PASSWORD")
LOOPBACK = ("127.0.0.1", "localhost", "::1")
TRUE_VALUES = ("1", "true")
BACKOFF = (1.0, 2.0, 4.0, 8.0)
REQUEST_TIMEOUT = 60.0
USER_AGENT = "stillstift-client"
IMAGE_TYPES = {".png": "image/png", ".webp": "image/webp"}


@dataclass(frozen=True)
class Credentials:
    user: str
    password: str


def credentials_from_env(env: Mapping[str, str] = os.environ) -> Credentials | None:
    """Return the basic-auth login from the environment, or None when neither variable is set."""
    user, password = (env.get(name) for name in AUTH_ENV)
    if user is None and password is None:
        return None
    if not user or not password:
        msg = f"set both {AUTH_ENV[0]} and {AUTH_ENV[1]} to non-empty values, or neither"
        raise ValueError(msg)
    return Credentials(user, password)


def _authorized(header: str | None, credentials: Credentials) -> bool:
    scheme, _, encoded = (header or "").partition(" ")
    if scheme.lower() != "basic":
        return False
    try:
        decoded = base64.b64decode(encoded, validate=True).decode()
    except ValueError:
        return False
    user, colon, password = decoded.partition(":")
    user_ok = secrets.compare_digest(user.encode(), credentials.user.encode())
    password_ok = secrets.compare_digest(password.encode(), credentials.password.encode())
    return bool(colon) and user_ok and password_ok


class BasicAuth(BaseHTTPMiddleware):
    """Answer 401 to every request without the right login, static files included."""

    def __init__(self, app: ASGIApp, credentials: Credentials) -> None:
        super().__init__(app)
        self._credentials = credentials

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if _authorized(request.headers.get("authorization"), self._credentials):
            return await call_next(request)
        return Response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": 'Basic realm="Stillstift"'},
        )


class EntrySummary(BaseModel):
    entry: str
    kind: Kind | None
    name: str
    date: str
    tests: str
    rendered: int
    unrated: int
    cells: int


class SetNameBody(BaseModel):
    """A set's name and date from its index line."""

    model_config = ConfigDict(extra="forbid")

    name: str
    date: str = ""


class NewSetBody(BaseModel):
    """An experiment or a test as the Experiments page creates it."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["X", "T"]
    name: str
    tests: str = ""


class NewSetOut(BaseModel):
    entry: str


class PredictionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry: str
    cell: str
    prediction: Verdict


class Counted(BaseModel):
    """How many of what was sent the curator kept."""

    count: int


class Changes(BaseModel):
    """The store's change stamp: a page refreshes when it moves."""

    stamp: int


Stars = Annotated[int, Field(ge=1, le=5)]


class Flags(BaseModel):
    model_config = ConfigDict(extra="forbid")

    book: Flag | None = None


def _known(given: Iterable[str], known: tuple[str, ...], what: str) -> None:
    unknown = sorted(set(given) - set(known))
    if unknown:
        msg = f"unknown {what}: {', '.join(unknown)}"
        raise ValueError(msg)


class RatingBody(BaseModel):
    """A rating as the page sends it and the API returns it; blank rows are left out."""

    model_config = ConfigDict(extra="forbid")

    taste: Stars
    rows: dict[str, Stars | None] = Field(default_factory=dict[str, int | None])
    render: Stars | None = None
    flaws: list[str] = Field(default_factory=list[str])
    flags: Flags = Field(default_factory=Flags)
    on_target: OnTarget | None = None
    reason: str = ""

    @field_validator("rows")
    @classmethod
    def _known_rows(cls, rows: dict[str, int | None]) -> dict[str, int | None]:
        _known(rows, ROWS, "rows")
        return rows

    @field_validator("flaws")
    @classmethod
    def _known_flaws(cls, flaws: list[str]) -> list[str]:
        _known(flaws, FLAWS, "flaws")
        return flaws

    @classmethod
    def of(cls, rating: CellRating) -> Self:
        rows: dict[str, int | None] = dict(rating.rows)
        return cls(
            taste=rating.taste,
            rows=rows,
            render=rating.render,
            flaws=list(rating.flaws),
            flags=Flags(book=rating.book),
            on_target=rating.on_target,
            reason=rating.reason,
        )

    def rating(self) -> CellRating:
        return CellRating(
            taste=self.taste,
            rows={row: stars for row in ROWS if (stars := self.rows.get(row)) is not None},
            render=self.render,
            flaws=tuple(f for f in FLAWS if f in self.flaws),
            book=self.flags.book,
            on_target=self.on_target,
            reason=self.reason.strip(),
        )


class FavoriteBody(BaseModel):
    cell: str | None


class OtherRating(BaseModel):
    """Another rater's own taste and verdict of a cell, shown small and read-only."""

    rater: str
    taste: Stars
    verdict: Verdict


class CellView(BaseModel):
    """A rendered cell as the rating page sees it: its prediction only once it is rated.

    `rating` and `verdict` are the picked rater's own; `others` is every other configured
    rater's taste and verdict, for the cells they have rated.
    """

    cell_id: str
    image: str
    thumb: str
    preview: str
    download: str
    prompt: str
    negative: str
    settings: list[tuple[str, str]]
    intent: str
    tags: list[str]
    verdict: Verdict | None
    rating: RatingBody | None
    favorite: bool
    others: list[OtherRating] = Field(default_factory=list[OtherRating])
    prediction: Verdict | None = None


class CellRow(BaseModel):
    """A rendered cell of any set as the overview pages list it; its prediction once rated."""

    entry: str
    kind: Kind | None
    cell_id: str
    image: str
    thumb: str
    download: str
    rendered_at: datetime
    rating: RatingBody | None
    verdict: Verdict | None
    prediction: Verdict | None
    favorite: bool


class CellMeta(BaseModel):
    """What the store holds of a render's generation: never its prediction."""

    dimension: str
    value: str
    prompt: str
    negative: str
    seed: int
    infotext: str | None
    rendered_at: datetime
    intent: str = ""
    tags: list[str] = Field(default_factory=list[str])


class CellExport(BaseModel):
    cell: str
    verdict: Verdict | None
    reason: str | None
    rated_at: datetime | None
    image: str
    meta: CellMeta
    rating: RatingBody | None = None


class EntryExport(BaseModel):
    entry: str
    cells: list[CellExport]
    favorite: str | None = None


class VerdictOut(BaseModel):
    """A cell's latest rating and the verdict it maps to."""

    entry: str
    cell: str
    verdict: Verdict
    reason: str
    rated_at: datetime
    rating: RatingBody | None = None
    favorite: bool = False

    @classmethod
    def of(cls, judged: CellVerdict) -> Self:
        rating = None if judged.rating is None else RatingBody.of(judged.rating)
        return cls(
            entry=judged.entry,
            cell=judged.cell_id,
            verdict=judged.verdict,
            reason=judged.reason,
            rated_at=judged.rated_at,
            rating=rating,
            favorite=judged.favorite,
        )


class UploadOut(BaseModel):
    entry: str
    cell: str
    replaced: bool


@dataclass(frozen=True)
class Upload:
    cell: Cell
    render: Render
    replace: bool


FormText = Annotated[str | None, Form()]
FormImage = Annotated[UploadFile | None, File()]
CELL_VIEWS = TypeAdapter(list[CellView])
VERDICTS = TypeAdapter(list[VerdictOut])


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail)


@dataclass(frozen=True)
class Described:
    """What the uploader says of a cell beside its PNG: intent, tags and dimension."""

    intent: str
    tags: tuple[str, ...]
    dimension: str


def _described(
    intent: FormText = None, tags: FormText = None, dimension: FormText = None
) -> Described:
    try:
        tagged = parse_tags(tags or "")
    except RegisterError as error:
        raise _bad_request(str(error)) from None
    return Described((intent or "").strip(), tagged, (dimension or "").strip())


DescribedDep = Annotated[Described, Depends(_described)]


def _upload_form(
    described: DescribedDep,
    entry: FormText = None,
    cell: FormText = None,
    replace: FormText = None,
    image: FormImage = None,
) -> Upload:
    """Read the upload form: the ids, the PNG, and the cell its metadata and description give."""
    if entry is None or cell is None or image is None:
        msg = "entry, cell and image are required"
        raise _bad_request(msg)
    if kind_of(entry) is None or not valid_cell(cell):
        msg = "entry is a set like P3, X2 or T4, and cell is like #01"
        raise _bad_request(msg)
    png = image.file.read()
    try:
        infotext = png_infotext(png)
        parsed = cell_from_infotext(entry, cell, infotext)
    except RegisterError as error:
        raise _bad_request(str(error)) from None
    full = Cell(
        entry=parsed.entry,
        cell_id=parsed.cell_id,
        dimension=described.dimension,
        value=parsed.value,
        prompt=parsed.prompt,
        negative=parsed.negative,
        seed=parsed.seed,
        prediction=None,
        prediction_reason="",
        intent=described.intent,
        tags=described.tags,
    )
    asked = (replace or "").lower() in TRUE_VALUES
    return Upload(full, Render(png, infotext), asked)


UploadDep = Annotated[Upload, Depends(_upload_form)]


def _rating_of(found: CellVerdict | None) -> RatingBody | None:
    return None if found is None or found.rating is None else RatingBody.of(found.rating)


def _download(cell: Cell) -> str:
    """Name the file a download of the render saves as, with its render's extension."""
    suffix = ".png" if cell.image_path is None else cell.image_path.suffix
    return f"{cell.entry}-{cell.cell_id}{suffix}"


def _others(
    store: Store, entry: str, raters: Sequence[str], rater: str | None
) -> dict[str, list[OtherRating]]:
    """Every configured rater but `rater`'s own rating of the set's cells, by cell id.

    Cheap because there are only a few raters: one extra query per other rater.
    """
    others: dict[str, list[OtherRating]] = {}
    for name in raters:
        if name == rater:
            continue
        for v in store.verdicts(entry, rater=name):
            if v.rating is None:
                continue
            others.setdefault(v.cell_id, []).append(
                OtherRating(rater=name, taste=v.rating.taste, verdict=v.verdict)
            )
    return others


def _cell_views(
    store: Store, entry: str, raters: Sequence[str], rater: str | None
) -> list[CellView]:
    """Every rendered cell of the set in cell order, with `rater`'s own rating and settings.

    `rater` is None before a rater is picked: no own rating, and every configured rater shows
    as an "other".
    """
    judged = {} if rater is None else {v.cell_id: v for v in store.verdicts(entry, rater=rater)}
    favorite = None if rater is None else store.favorite(entry, rater)
    others = _others(store, entry, raters, rater)
    views: list[CellView] = []
    for c in store.cells(entry):
        if c.rendered_at is None:
            continue
        found = judged.get(c.cell_id)
        views.append(
            CellView(
                cell_id=c.cell_id,
                image=image_url(c.entry, c.cell_id, c.rendered_at),
                thumb=thumb_url(c.entry, c.cell_id, c.rendered_at),
                preview=preview_url(c.entry, c.cell_id, c.rendered_at),
                download=_download(c),
                prompt=c.prompt,
                negative=c.negative,
                settings=parse_settings(c.infotext or ""),
                intent=c.intent,
                tags=list(c.tags),
                verdict=None if found is None or found.rating is not None else found.verdict,
                rating=_rating_of(found),
                favorite=c.cell_id == favorite,
                others=others.get(c.cell_id, []),
                prediction=None if found is None else c.prediction,
            )
        )
    return views


def _cell_rows(store: Store) -> list[CellRow]:
    """Every rendered cell of every set, newest set first, with its merged rating.

    Merged over every rater who has rated it; see `Store.verdicts`.
    """
    judged = {(v.entry, v.cell_id): v for v in store.verdicts()}
    favorites = store.favorites_any()
    rows: list[CellRow] = []
    for c in store.rendered_cells():
        if c.rendered_at is None:
            continue
        found = judged.get((c.entry, c.cell_id))
        rows.append(
            CellRow(
                entry=c.entry,
                kind=kind_of(c.entry),
                cell_id=c.cell_id,
                image=image_url(c.entry, c.cell_id, c.rendered_at),
                thumb=thumb_url(c.entry, c.cell_id, c.rendered_at),
                download=_download(c),
                rendered_at=c.rendered_at,
                rating=_rating_of(found),
                verdict=None if found is None or is_lab(c.entry) else found.verdict,
                prediction=None if found is None else c.prediction,
                favorite=favorites.get(c.entry) == c.cell_id,
            )
        )
    return rows


def _export_entry(store: Store, entry: str) -> EntryExport:
    """Every rendered cell of the set in cell order, its rating and generation metadata."""
    cells = store.cells(entry)
    if not cells:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown set")
    judged = {v.cell_id: v for v in store.verdicts(entry)}
    exported: list[CellExport] = []
    for c in cells:
        if c.rendered_at is None:
            continue
        found = judged.get(c.cell_id)
        meta = CellMeta(
            dimension=c.dimension,
            value=c.value,
            prompt=c.prompt,
            negative=c.negative,
            seed=c.seed,
            infotext=c.infotext,
            rendered_at=c.rendered_at,
            intent=c.intent,
            tags=list(c.tags),
        )
        exported.append(
            CellExport(
                cell=c.cell_id,
                verdict=None if found is None else found.verdict,
                reason=None if found is None else found.reason,
                rated_at=None if found is None else found.rated_at,
                image=f"/api/image/{entry}/{quote(c.cell_id, safe='')}",
                meta=meta,
                rating=_rating_of(found),
            )
        )
    return EntryExport(entry=entry, cells=exported, favorite=store.favorite_any(entry))


def _image_file(store: Store, entry: str, cell_id: str, request: Request) -> Response:
    """Serve the cell's render; a set rendered again under its id must never show a cached one."""
    cell = store.cell(entry, cell_id)
    if cell is None or cell.image_path is None or not cell.image_path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no render for this cell")
    media = IMAGE_TYPES.get(cell.image_path.suffix, "image/png")
    return _revalidated(cell.image_path, media, request)


def _thumb_file(
    store: Store, entry: str, cell_id: str, request: Request, width: int = THUMB_WIDTH
) -> Response:
    """Serve the render as a WebP at most `width` wide; the render itself when one can't be made."""
    cell = store.cell(entry, cell_id)
    path = None if cell is None else cell.image_path
    if path is None or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no render for this cell")
    try:
        thumb = thumb_of(path, width)
    except OSError:
        return _image_file(store, entry, cell_id, request)
    return _revalidated(thumb, "image/webp", request)


def _revalidated(path: Path, media_type: str, request: Request) -> Response:
    """Serve the file for the browser to revalidate on every use: a 304 while it is unchanged."""
    found = FileResponse(path, media_type=media_type, headers=REVALIDATE, stat_result=path.stat())
    etag = found.headers["etag"]
    asked = request.headers.get("if-none-match", "")
    if etag in (tag.strip().removeprefix("W/") for tag in asked.split(",")):
        return Response(
            status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag, **REVALIDATE}
        )
    return found


def _page(name: str) -> Callable[[Request], Response]:
    """Serve one of the curator's pages, revalidated on every load like its scripts."""

    def page(request: Request) -> Response:
        return _revalidated(STATIC / name, "text/html", request)

    return page


class _RevalidatedStatic(StaticFiles):
    """The pages' scripts and styles, revalidated on every load so a deploy shows at once."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers.update(REVALIDATE)
        return response


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _open_store(request: Request) -> Iterator[Store]:
    store = Store.open(request.app.state.db, request.app.state.raters)
    try:
        yield store
    finally:
        store.close()


StoreDep = Annotated[Store, Depends(_open_store)]


def _optional_rater(request: Request, rater: str | None = None) -> str | None:
    """Read the `rater` query param, checked against STILLSTIFT_RATERS; None when not given."""
    if rater is not None and rater not in request.app.state.raters:
        msg = f"unknown rater: {rater}"
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, msg)
    return rater


OptionalRaterDep = Annotated[str | None, Depends(_optional_rater)]


def _required_rater(rater: OptionalRaterDep) -> str:
    """Require the `rater` query param: a write must know who is rating."""
    if rater is None:
        msg = "a rater is required"
        raise _bad_request(msg)
    return rater


RaterDep = Annotated[str, Depends(_required_rater)]


def _register_upload(store: Store, form: Upload, renders: Path, rendered_at: datetime) -> UploadOut:
    """Register the upload; a rendered cell is refused with a 409 unless asked to replace."""
    cell = form.cell
    found = store.cell(cell.entry, cell.cell_id)
    replaced = found is not None and found.rendered_at is not None
    if replaced and not form.replace:
        msg = f"{cell.entry} {cell.cell_id} is already rendered; send replace=1 to replace it"
        raise HTTPException(status.HTTP_409_CONFLICT, msg)
    register_render(store, cell, form.render, renders, rendered_at)
    if replaced:
        store.clear_ratings(cell.entry, cell.cell_id)
    return UploadOut(entry=cell.entry, cell=cell.cell_id, replaced=replaced)


def _add_upload_route(app: FastAPI, renders: Path, now: Callable[[], datetime]) -> None:
    @app.post("/api/upload", status_code=status.HTTP_201_CREATED)
    def upload(response: Response, store: StoreDep, form: UploadDep) -> UploadOut:
        uploaded = _register_upload(store, form, renders, now())
        if uploaded.replaced:
            response.status_code = status.HTTP_200_OK
        return uploaded


def _add_export_routes(app: FastAPI) -> None:
    @app.get("/api/entries/{entry}")
    def export(entry: str, store: StoreDep) -> EntryExport:
        return _export_entry(store, entry)

    @app.get("/api/image/{entry}/{cell_id}")
    def exported_image(entry: str, cell_id: str, store: StoreDep, request: Request) -> Response:
        return _image_file(store, entry, cell_id, request)

    @app.get("/api/verdicts")
    def verdicts(store: StoreDep, entry: str | None = None) -> list[VerdictOut]:
        """Every page set's latest ratings, oldest first: what `just score` reads."""
        return [VerdictOut.of(v) for v in store.verdicts(entry) if kind_of(v.entry) == "P"]


def _add_rating_routes(app: FastAPI, now: Callable[[], datetime]) -> None:
    @app.post("/api/entries/{entry}/cells/{cell_id}/rating", status_code=204)
    def rate(
        entry: str, cell_id: str, body: RatingBody, store: StoreDep, rater: RaterDep
    ) -> Response:
        rating = body.rating()
        extra = misfits(kind_of(entry), rating)
        if extra:
            msg = f"{entry} takes no {', '.join(extra)}"
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, msg)
        try:
            store.rate_cell(entry, cell_id, rater, rating, now())
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown cell") from None
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.delete("/api/entries/{entry}/cells/{cell_id}/rating")
    def undo(entry: str, cell_id: str, store: StoreDep, rater: RaterDep) -> RatingBody:
        removed = store.unrate(entry, cell_id, rater)
        if removed is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "nothing to undo")
        return RatingBody.of(removed)

    @app.delete("/api/entries/{entry}", status_code=204)
    def delete(entry: str, store: StoreDep) -> Response:
        if not delete_entry(store, entry):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no such set")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.put("/api/entries/{entry}/favorite", status_code=204)
    def favorite(entry: str, body: FavoriteBody, store: StoreDep, rater: RaterDep) -> Response:
        if is_lab(entry):
            msg = f"{entry} is a lab set: it has no favorite"
            raise _bad_request(msg)
        try:
            store.set_favorite(entry, rater, body.cell, now())
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown cell") from None
        return Response(status_code=status.HTTP_204_NO_CONTENT)


def _add_set_routes(app: FastAPI, now: Callable[[], datetime]) -> None:
    @app.put("/api/sets")
    def set_names(body: dict[str, SetNameBody], store: StoreDep) -> Counted:
        unknown = sorted(entry for entry in body if kind_of(entry) is None)
        if unknown:
            msg = f"not a set: {', '.join(unknown)}"
            raise _bad_request(msg)
        names = {entry: SetName(n.name.strip(), n.date.strip()) for entry, n in body.items()}
        return Counted(count=store.put_set_names(names))

    @app.post("/api/sets", status_code=201)
    def create_set(body: NewSetBody, store: StoreDep) -> NewSetOut:
        name = body.name.strip()
        if not name:
            msg = "a set needs a name"
            raise _bad_request(msg)
        return NewSetOut(entry=store.create_set(body.kind, name, body.tests.strip(), now().date()))

    @app.put("/api/predictions")
    def predictions(body: list[PredictionBody], store: StoreDep) -> Counted:
        sent = [Prediction(p.entry, p.cell, p.prediction) for p in body]
        return Counted(count=store.put_predictions(sent))


def create_app(
    db: Path = DEFAULT_PATH,
    now: Callable[[], datetime] = _utc_now,
    credentials: Credentials | None = None,
    renders: Path = RENDERS,
    raters: tuple[str, ...] = (),
) -> FastAPI:
    app = FastAPI(title="Stillstift curator")
    app.state.db = db
    app.state.raters = raters
    if credentials is not None:
        app.add_middleware(BasicAuth, credentials=credentials)
    _add_upload_route(app, renders, now)
    _add_export_routes(app)
    _add_rating_routes(app, now)
    _add_set_routes(app, now)

    for path, name in PAGE_FILES.items():
        app.add_api_route(path, _page(name), methods=["GET"], include_in_schema=False)

    @app.get("/api/changes")
    def changes(store: StoreDep) -> Changes:
        return Changes(stamp=store.stamp())

    @app.get("/api/raters")
    def raters_route(request: Request) -> list[str]:
        return list(request.app.state.raters)

    @app.get("/api/entries")
    def entries(store: StoreDep, rater: OptionalRaterDep) -> list[EntrySummary]:
        return [
            EntrySummary(
                entry=c.entry,
                kind=kind_of(c.entry),
                name=c.name,
                date=c.date,
                tests=c.tests,
                rendered=c.rendered,
                unrated=c.unrated,
                cells=c.cells,
            )
            for c in store.entry_counts(rater)
        ]

    @app.get("/api/cells")
    def all_cells(store: StoreDep) -> list[CellRow]:
        return _cell_rows(store)

    @app.get("/api/entries/{entry}/cells")
    def cells(
        entry: str, store: StoreDep, request: Request, rater: OptionalRaterDep
    ) -> list[CellView]:
        return _cell_views(store, entry, request.app.state.raters, rater)

    @app.get("/api/entries/{entry}/cells/{cell_id}/image")
    def image(entry: str, cell_id: str, store: StoreDep, request: Request) -> Response:
        return _image_file(store, entry, cell_id, request)

    @app.get("/api/entries/{entry}/cells/{cell_id}/thumb")
    def thumb(entry: str, cell_id: str, store: StoreDep, request: Request) -> Response:
        return _thumb_file(store, entry, cell_id, request)

    @app.get("/api/entries/{entry}/cells/{cell_id}/preview")
    def preview(entry: str, cell_id: str, store: StoreDep, request: Request) -> Response:
        return _thumb_file(store, entry, cell_id, request, PREVIEW_WIDTH)

    app.mount("/static", _RevalidatedStatic(directory=STATIC), name="static")
    return app


class CuratorError(RuntimeError):
    pass


def _login(env: Mapping[str, str]) -> httpx.BasicAuth | None:
    user, password = (env.get(name) for name in CURATOR_ENV[1:])
    if user is None and password is None:
        return None
    if not user or not password:
        msg = f"set both {CURATOR_ENV[1]} and {CURATOR_ENV[2]} to non-empty values, or neither"
        raise CuratorError(msg)
    return httpx.BasicAuth(user, password)


def _check(response: httpx.Response, what: str) -> httpx.Response:
    if response.is_success:
        return response
    hint = ""
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        hint = f" — check {CURATOR_ENV[1]} and {CURATOR_ENV[2]}"
    msg = f"{what}: HTTP {response.status_code} {response.text[:300]}{hint}"
    raise CuratorError(msg)


class CuratorClient:
    """The hosted curator over HTTP; every request retries on a transport error or a 5xx."""

    def __init__(self, http: httpx.Client, sleep: Callable[[float], None] = time.sleep) -> None:
        self._http = http
        self._sleep = sleep

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] = os.environ,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> Self | None:
        """Connect as STILLSTIFT_CURATOR_URL, _USER and _PASSWORD say; None when no URL is set."""
        url = env.get(CURATOR_ENV[0])
        if not url:
            return None
        http = httpx.Client(
            base_url=url,
            auth=_login(env),
            headers={"User-Agent": USER_AGENT},
            transport=transport,
            timeout=REQUEST_TIMEOUT,
        )
        return cls(http, sleep)

    @property
    def base_url(self) -> str:
        return str(self._http.base_url)

    def close(self) -> None:
        self._http.close()

    def upload(self, cell: Cell, png: bytes, *, replace: bool = False) -> bool:
        """Send a cell's PNG with its intent, tags and dimension; True on a replace."""
        entry, cell_id = cell.entry, cell.cell_id
        fields = {
            "entry": entry,
            "cell": cell_id,
            "intent": cell.intent,
            "tags": "; ".join(cell.tags),
            "dimension": cell.dimension,
            "replace": "1" if replace else "",
        }
        request = partial(
            self._http.build_request,
            "POST",
            "/api/upload",
            data=fields,
            files={"image": (f"{cell_id}.png", png, "image/png")},
        )
        response = _check(self._send(request), f"upload {entry} {cell_id}")
        return response.status_code == HTTPStatus.OK

    def create_set(self, kind: Literal["X", "T"], name: str, tests: str) -> str:
        """Create the next experiment or test with its name and what it tests; return its id."""
        body = NewSetBody(kind=kind, name=name, tests=tests).model_dump_json()
        request = partial(
            self._http.build_request,
            "POST",
            "/api/sets",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        response = _check(self._send(request), f"create the {kind} set")
        return NewSetOut.model_validate_json(response.content).entry

    def put_set_names(self, names: Mapping[str, SetName]) -> int:
        """Send each set's name and date from the index; return how many the curator kept."""
        body = {entry: {"name": n.name, "date": n.date} for entry, n in names.items()}
        return self._put_json("/api/sets", body, "send the set names")

    def put_predictions(self, predictions: Iterable[Prediction]) -> int:
        """Send blind predictions; return how many cells the curator held to set them on."""
        body = [
            {"entry": p.entry, "cell": p.cell_id, "prediction": p.verdict.value}
            for p in predictions
        ]
        return self._put_json("/api/predictions", body, "send the predictions")

    def _put_json(self, path: str, body: object, what: str) -> int:
        request = partial(
            self._http.build_request,
            "PUT",
            path,
            content=json.dumps(body),
            headers={"Content-Type": "application/json"},
        )
        return Counted.model_validate_json(_check(self._send(request), what).content).count

    def rendered_cells(self, entry: str) -> set[str]:
        """Return the ids of the set's cells the curator already holds a render of."""
        response = _check(self._get(f"/api/entries/{entry}/cells"), f"list {entry}")
        return {c.cell_id for c in CELL_VIEWS.validate_json(response.content)}

    def export(self, entry: str) -> EntryExport | None:
        """Read a set's cells, ratings and metadata; None when the curator has no such set."""
        response = self._get(f"/api/entries/{entry}")
        if response.status_code == HTTPStatus.NOT_FOUND:
            return None
        return EntryExport.model_validate_json(_check(response, f"read {entry}").content)

    def delete_entry(self, entry: str) -> bool:
        """Delete the set with its ratings and renders; False when the curator held no such set."""
        response = self._send(partial(self._http.build_request, "DELETE", f"/api/entries/{entry}"))
        if response.status_code == HTTPStatus.NOT_FOUND:
            return False
        _check(response, f"delete {entry}")
        return True

    def image(self, path: str) -> bytes:
        """Fetch an image by the path an export gave for it."""
        return _check(self._get(path), f"fetch {path}").content

    def verdicts(self, entry: str | None = None) -> list[VerdictOut]:
        """Read every rated page cell's latest rating, oldest rating first."""
        params = None if entry is None else {"entry": entry}
        response = _check(self._get("/api/verdicts", params), "read verdicts")
        return VERDICTS.validate_json(response.content)

    def _get(self, path: str, params: dict[str, str] | None = None) -> httpx.Response:
        return self._send(partial(self._http.build_request, "GET", path, params=params))

    def _send(self, build: Callable[[], httpx.Request]) -> httpx.Response:
        failure = ""
        for delay in (*BACKOFF, None):
            request = build()
            try:
                response = self._http.send(request)
            except httpx.TransportError as error:
                failure = f"{request.method} {request.url.path}: {type(error).__name__} {error}"
            else:
                retry = response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
                if not retry and response.status_code != HTTPStatus.TOO_MANY_REQUESTS:
                    return response
                failure = f"{request.method} {request.url.path}: HTTP {response.status_code}"
            if delay is None:
                break
            self._sleep(delay)
        msg = f"{self.base_url}: {failure}, failed {len(BACKOFF) + 1} times"
        raise CuratorError(msg)


@dataclass(frozen=True)
class HostedSource:
    """The hosted curator's ratings and images, paired with the local register's predictions."""

    client: CuratorClient
    preds: Path = PREDS

    def scored_cells(self, entry: str | None = None) -> list[ScoredCell]:
        predictions = read_predictions(self.preds)
        scored: list[ScoredCell] = []
        for v in self.client.verdicts(entry):
            prediction = predictions.get((v.entry, v.cell))
            if prediction is not None and kind_of(v.entry) == "P":
                rating = None if v.rating is None else v.rating.rating()
                scored.append(
                    ScoredCell(
                        v.entry,
                        v.cell,
                        prediction,
                        v.verdict,
                        v.reason,
                        v.rated_at,
                        rating,
                        v.favorite,
                    )
                )
        return scored

    def sheet_cells(self, entry: str) -> list[SheetCell]:
        exported = self.client.export(entry)
        if exported is None:
            return []
        return [
            SheetCell(
                c.cell,
                c.verdict,
                self.client.image(c.image),
                None if c.rating is None else c.rating.taste,
            )
            for c in exported.cells
        ]

    def close(self) -> None:
        self.client.close()


def open_source() -> Source:
    """Open the hosted curator when STILLSTIFT_CURATOR_URL is set, the local store otherwise."""
    client = CuratorClient.from_env()
    return Store.open() if client is None else HostedSource(client)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="just curate", description=__doc__)
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args(argv)
    try:
        credentials = credentials_from_env()
    except ValueError as error:
        parser.error(str(error))
    if credentials is None and args.host not in LOOPBACK:
        parser.error(f"refusing to listen on {args.host} without {AUTH_ENV[0]} and {AUTH_ENV[1]}")
    raters = raters_from_env()
    if not raters:
        parser.error(f"set {RATERS_ENV} to who is rating, comma-separated")
    uvicorn.run(create_app(credentials=credentials, raters=raters), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
