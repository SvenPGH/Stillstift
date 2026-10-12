"""Read the register (register/sets.csv, register/predictions.csv) into cells and renders.

A set's row holds its cell lines, one per cell:
`--prompt … --negative_prompt … --seed … [--profile <name>]`. The prediction file holds each
cell's blind prediction, its intent and its tags.
"""

from __future__ import annotations

import csv
import io
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple
from urllib.parse import quote

from PIL import Image

from stillstift.kinds import cell_id, is_lab
from stillstift.png import with_parameters
from stillstift.store import Cell, Prediction, SetName, Store, Verdict, data_dir
from stillstift.webp import thumb_path

if TYPE_CHECKING:
    from datetime import datetime

SETS = Path("register/sets.csv")
INDEX = Path("register/index.md")
PREDS = Path("register/predictions.csv")
TAG = re.compile(r"([a-z][a-z0-9_]*):\s*([A-Za-z0-9][A-Za-z0-9_.-]*)")
RENDERS = data_dir() / "renders"
SETTINGS_LINE = "Steps: "
NEGATIVE_MARKER = re.compile(r"^Negative prompt: ", re.MULTILINE)
SEED = re.compile(r"\bSeed: (\d+)")
SIZE = re.compile(r"(\d+)\s*[x\xd7]\s*(\d+)")
INDEX_LINE = re.compile(r"- ((?:P|X|T)[0-9]+[a-z]?) · (.+?) · .*?\b(\d{4}-\d{2}-\d{2})\b")
TIMES = "\N{MULTIPLICATION SIGN}"
SETTING_PAIR = re.compile(r'\s*([A-Za-z][A-Za-z0-9 ]*):\s*("(?:[^"\\]|\\.)*"|[^,]*)')
SHOWN_SETTINGS = (
    ("profile", "Profile"),
    ("checkpoint", "Model"),
    ("loras", "Loras"),
    ("sampler", "Sampler"),
    ("steps", "Steps"),
    ("cfg", "CFG scale"),
    ("guidance", "Guidance"),
    ("seed", "Seed"),
    ("size", "Size"),
)

PREDICTION_CODES = {"k": Verdict.KEEP, "*": Verdict.FAV, "i": Verdict.ISSUE, "x": Verdict.KILL}
TEXT_OPTIONS = ("prompt", "negative_prompt")
OPTIONS = (*TEXT_OPTIONS, "seed", "profile")


class RegisterError(ValueError):
    pass


class Line(NamedTuple):
    """One cell's line: its prompt, negative and seed, and the profile it renders with."""

    prompt: str
    negative: str
    seed: int
    profile: str = ""


def parse_tags(text: str) -> tuple[str, ...]:
    """Read a cell's tags, `category: option` pairs split by `;`, in their written order."""
    tags: list[str] = []
    for part in (p.strip() for p in text.split(";")):
        if not part:
            continue
        found = TAG.fullmatch(part)
        if found is None:
            msg = f"a tag is `category: option`, got {part!r}"
            raise RegisterError(msg)
        tags.append(f"{found[1]}: {found[2]}")
    return tuple(dict.fromkeys(tags))


def parse_line(line: str) -> Line:
    """Read one cell's line: `--prompt … --negative_prompt … --seed … [--profile …]`."""
    args = shlex.split(line)
    found: dict[str, str] = {}
    pos = 0
    while pos < len(args):
        arg = args[pos]
        if not arg.startswith("--"):
            msg = f"must start with --: {arg}"
            raise RegisterError(msg)
        tag = arg[2:]
        if tag not in OPTIONS:
            msg = f"unknown option {arg}"
            raise RegisterError(msg)
        if pos + 1 >= len(args):
            msg = f"missing value for {arg}"
            raise RegisterError(msg)
        end = pos + 2
        if tag in TEXT_OPTIONS:
            while end < len(args) and not args[end].startswith("--"):
                end += 1
        found[tag] = " ".join(args[pos + 1 : end])
        pos = end
    if "prompt" not in found:
        msg = "no --prompt"
        raise RegisterError(msg)
    if "seed" not in found:
        msg = "no --seed"
        raise RegisterError(msg)
    try:
        seed = int(found["seed"])
    except ValueError:
        msg = f"--seed must be an integer, got {found['seed']!r}"
        raise RegisterError(msg) from None
    return Line(found["prompt"], found.get("negative_prompt", ""), seed, found.get("profile", ""))


def read_entry(entry: str, sets: Path = SETS, preds: Path = PREDS) -> list[tuple[Cell, Line]]:
    """Read a page set's cells with their lines, each with its prediction; refuse a gap."""
    lines = _cell_lines(entry, sets)
    predictions = _predictions(entry, preds)
    if len(lines) != len(predictions):
        msg = f"{entry}: {len(lines)} cell lines but {len(predictions)} predictions"
        raise RegisterError(msg)
    read: list[tuple[Cell, Line]] = []
    for number, (text, row) in enumerate(zip(lines, predictions, strict=True), start=1):
        try:
            line = parse_line(text)
        except RegisterError as error:
            msg = f"{entry} line {number}: {error}"
            raise RegisterError(msg) from None
        prediction = PREDICTION_CODES.get(row["pred"].strip())
        if prediction is None:
            msg = f"{entry} {row['cell']}: no prediction"
            raise RegisterError(msg)
        cell = Cell(
            entry=entry,
            cell_id=row["cell"],
            dimension=row["dimension"],
            value=row["value"],
            prompt=line.prompt,
            negative=line.negative,
            seed=line.seed,
            prediction=prediction,
            prediction_reason=row["pred_reason"],
            intent=(row.get("intent") or "").strip(),
            tags=_cell_tags(entry, row),
        )
        read.append((cell, line))
    return read


def read_lines(entry: str, lines: Path) -> list[tuple[Cell, Line]]:
    """Read a lab set's cells from a file of cell lines, one per line, numbered from #01.

    A lab set has no register row and no predictions: its cells carry neither.
    """
    texts = [t for t in lines.read_text(encoding="utf-8").splitlines() if t.strip()]
    read: list[tuple[Cell, Line]] = []
    for number, text in enumerate(texts, start=1):
        try:
            line = parse_line(text)
        except RegisterError as error:
            msg = f"{lines} line {number}: {error}"
            raise RegisterError(msg) from None
        cell = Cell(
            entry=entry,
            cell_id=cell_id(number),
            dimension="",
            value="",
            prompt=line.prompt,
            negative=line.negative,
            seed=line.seed,
            prediction=None,
            prediction_reason="",
        )
        read.append((cell, line))
    return read


def _cell_tags(entry: str, row: dict[str, str]) -> tuple[str, ...]:
    try:
        return parse_tags(row.get("tags") or "")
    except RegisterError as error:
        msg = f"{entry} {row['cell']}: {error}"
        raise RegisterError(msg) from None


def require_lines(entry: str, lines: Path | None) -> None:
    """Refuse a lab set without its cell lines, and lines for a set the register holds."""
    if is_lab(entry) and lines is None:
        msg = f"{entry} is a lab set: give its cell lines with --lines"
        raise RegisterError(msg)
    if not is_lab(entry) and lines is not None:
        msg = f"{entry} renders from the register; --lines is for a lab set (X or T)"
        raise RegisterError(msg)


def require_intents(cells: list[Cell]) -> None:
    """Refuse to render a cell without its intent, the line of what it is meant to show."""
    missing = [f"{c.entry} {c.cell_id}" for c in cells if not c.intent]
    if missing:
        msg = f"no intent for {', '.join(missing)}: write it in {PREDS} with the prediction"
        raise RegisterError(msg)


def index_names(index: Path = INDEX) -> dict[str, SetName]:
    """Read every set's name and date from its index line: `- P3 · <name> · … · <date>`."""
    names: dict[str, SetName] = {}
    for line in index.read_text(encoding="utf-8").splitlines():
        found = INDEX_LINE.match(line)
        if found is not None:
            names[found[1]] = SetName(found[2], found[3])
    return names


def predictions_of(preds: Path = PREDS) -> list[Prediction]:
    """Every cell's blind prediction from the prediction file, in its order."""
    return [Prediction(e, c, v) for (e, c), v in read_predictions(preds).items()]


def read_predictions(preds: Path = PREDS) -> dict[tuple[str, str], Verdict]:
    """Read every cell's blind prediction from the prediction file, keyed by (entry, cell)."""
    with preds.open(encoding="utf-8", newline="") as f:
        coded = {(row["entry"], row["cell"]): row["pred"].strip() for row in csv.DictReader(f)}
    return {key: PREDICTION_CODES[code] for key, code in coded.items() if code in PREDICTION_CODES}


@dataclass(frozen=True)
class Render:
    """A rendered PNG with the infotext it was made from."""

    png: bytes
    infotext: str


def png_infotext(png: bytes) -> str:
    """Return the `parameters` text of a PNG, where the render step writes its infotext."""
    try:
        with Image.open(io.BytesIO(png)) as image:
            image.load()
            kind, text = image.format, image.info.get("parameters")
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        kind, text = None, None
    if kind != "PNG":
        msg = "not a PNG"
        raise RegisterError(msg)
    if not isinstance(text, str) or not text.strip():
        msg = "the PNG has no generation metadata (a `parameters` text chunk)"
        raise RegisterError(msg)
    return text


def _settings_at(lines: list[str]) -> int | None:
    return next(
        (n for n in range(len(lines) - 1, -1, -1) if lines[n].startswith(SETTINGS_LINE)), None
    )


def parse_infotext(infotext: str) -> tuple[str, str, int]:
    """Read (prompt, negative, seed) from an infotext: prompt, negative, `Steps:` line."""
    lines = infotext.splitlines()
    settings = _settings_at(lines)
    if settings is None:
        msg = "no settings line (`Steps: …`) in the infotext"
        raise RegisterError(msg)
    seed = SEED.search(lines[settings])
    if seed is None:
        msg = "no Seed in the infotext's settings line"
        raise RegisterError(msg)
    prompt, *negative = NEGATIVE_MARKER.split("\n".join(lines[:settings]), maxsplit=1)
    return prompt.strip(), "".join(negative).strip(), int(seed.group(1))


def parse_settings(infotext: str) -> list[tuple[str, str]]:
    """Read the settings a rater looks at from an infotext, leaving out what it lacks."""
    lines = infotext.splitlines()
    at = _settings_at(lines)
    pairs = {} if at is None else {k.strip(): v.strip() for k, v in SETTING_PAIR.findall(lines[at])}
    schedule = pairs.pop("Schedule type", "")
    if schedule and pairs.get("Sampler"):
        pairs["Sampler"] = f"{pairs['Sampler']} · {schedule}"
    size = SIZE.fullmatch(pairs.get("Size", ""))
    if size is not None:
        pairs["Size"] = f"{size.group(1)} {TIMES} {size.group(2)}"
    shown = [(key, pairs.get(name, "")) for key, name in SHOWN_SETTINGS]
    return [(key, value) for key, value in shown if value]


def cell_from_infotext(entry: str, cell: str, infotext: str) -> Cell:
    """Build the cell of a render that arrives without a register: no dimension, no prediction."""
    prompt, negative, seed = parse_infotext(infotext)
    return Cell(
        entry=entry,
        cell_id=cell,
        dimension="",
        value="",
        prompt=prompt,
        negative=negative,
        seed=seed,
        prediction=None,
        prediction_reason="",
    )


def register_render(
    store: Store, cell: Cell, render: Render, out_dir: Path, rendered_at: datetime
) -> Path:
    """Write the cell's PNG under out_dir and mark it rendered in the store; return the path."""
    held = store.cell(cell.entry, cell.cell_id)
    store.add_cells([cell])
    path = out_dir / cell.entry / f"{cell.cell_id}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(with_parameters(render.png, render.infotext))
    store.record_render(cell.entry, cell.cell_id, path, render.infotext, rendered_at)
    old = None if held is None else held.image_path
    if old is not None and old != path:
        old.unlink(missing_ok=True)
    return path


def _cell_url(entry: str, cell: str, rendered_at: datetime, what: str) -> str:
    version = int(rendered_at.timestamp() * 1e6)
    return f"/api/entries/{entry}/cells/{quote(cell, safe='')}/{what}?v={version}"


def image_url(entry: str, cell: str, rendered_at: datetime) -> str:
    """Return the page's URL for a cell's render, versioned by when it was rendered.

    A set rendered again under its id gets new URLs, so an open page cannot show the old render
    from the browser's memory.
    """
    return _cell_url(entry, cell, rendered_at, "image")


def thumb_url(entry: str, cell: str, rendered_at: datetime) -> str:
    """Return the URL of a render's thumbnail for grids and pickers, versioned as image_url is."""
    return _cell_url(entry, cell, rendered_at, "thumb")


def delete_entry(store: Store, entry: str) -> bool:
    """Delete the set from the store and its renders and thumbnails from disk.

    False when it held none.
    """
    paths = store.delete_entry(entry)
    if paths is None:
        return False
    thumbs = [thumb_path(path) for path in paths]
    for path in [*paths, *thumbs]:
        path.unlink(missing_ok=True)
    for folder in sorted({path.parent for path in [*thumbs, *paths]}, reverse=True):
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
    return True


def register_row(entry: str, sets: Path = SETS) -> dict[str, str]:
    """Return the set's row of the register; a RegisterError when it has none."""
    with sets.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["id"] == entry:
                return row
    msg = f"{entry}: not in the register"
    raise RegisterError(msg)


def entry_profile(entry: str, sets: Path = SETS) -> str:
    """Return the profile the set's row names for cells whose line names none ("" for none)."""
    return register_row(entry, sets).get("profile", "").strip()


def _cell_lines(entry: str, sets: Path) -> list[str]:
    return [line for line in register_row(entry, sets)["lines"].splitlines() if line.strip()]


def _predictions(entry: str, preds: Path) -> list[dict[str, str]]:
    with preds.open(encoding="utf-8", newline="") as f:
        return [row for row in csv.DictReader(f) if row["entry"] == entry]
