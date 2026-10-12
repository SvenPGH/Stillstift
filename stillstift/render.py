"""`just render <entry>`: render a set's unrendered cells on the project's ComfyUI.

Each finished page goes to the local store, or to the hosted curator when
STILLSTIFT_CURATOR_URL is set; a failed upload keeps its PNG under data/failed/.
"""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import ExitStack, closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from stillstift.comfy import (
    Comfy,
    ComfyError,
    Profile,
    Workflow,
    fill,
    infotext,
    load_profile,
    needed,
)
from stillstift.curator import CuratorClient, CuratorError
from stillstift.kinds import cell_arg, is_lab
from stillstift.models import Manifest, ModelError
from stillstift.png import only_parameters
from stillstift.register import (
    RENDERS,
    RegisterError,
    Render,
    entry_profile,
    read_entry,
    read_lines,
    register_render,
    require_intents,
    require_lines,
)
from stillstift.store import Store, data_dir
from stillstift.sync import send_register

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from stillstift.register import Line
    from stillstift.store import Cell
    from stillstift.sync import RegisterSink

FAILED = data_dir() / "failed"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Destination(Protocol):
    """Where a finished render goes: the cells still to render and the hand-over of each.

    Its sink is the curator that keeps the set's name and predictions.
    """

    @property
    def sink(self) -> RegisterSink: ...

    def to_render(self, entry: str, cells: list[Cell], *, replace: bool) -> list[Cell]: ...

    def deliver(self, cell: Cell, render: Render, *, replace: bool) -> str: ...


@dataclass(frozen=True)
class LocalStore:
    store: Store
    out_dir: Path = RENDERS
    now: Callable[[], datetime] = _utc_now

    @property
    def sink(self) -> RegisterSink:
        return self.store

    def to_render(self, entry: str, cells: list[Cell], *, replace: bool) -> list[Cell]:
        self.store.add_cells(cells)
        if replace:
            return cells
        held = {c.cell_id for c in self.store.cells(entry) if c.rendered_at is not None}
        return [c for c in cells if c.cell_id not in held]

    def deliver(self, cell: Cell, render: Render, *, replace: bool) -> str:
        if replace:
            self.store.clear_ratings(cell.entry, cell.cell_id)
        return str(register_render(self.store, cell, render, self.out_dir, self.now()))


@dataclass(frozen=True)
class HostedCurator:
    """Upload each render to the hosted curator; a failed upload keeps its PNG locally."""

    client: CuratorClient
    failed_dir: Path = FAILED

    @property
    def sink(self) -> RegisterSink:
        return self.client

    def to_render(self, entry: str, cells: list[Cell], *, replace: bool) -> list[Cell]:
        if replace:
            return cells
        held = self.client.rendered_cells(entry)
        return [c for c in cells if c.cell_id not in held]

    def deliver(self, cell: Cell, render: Render, *, replace: bool) -> str:
        try:
            self.client.upload(cell, render.png, replace=replace)
        except CuratorError:
            path = self.failed_dir / cell.entry / f"{cell.cell_id}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(render.png)
            sys.stderr.write(f"{cell.entry} {cell.cell_id}: upload failed, kept at {path}\n")
            raise
        return self.client.base_url


@dataclass(frozen=True)
class Job:
    """One cell to render, with the profile it renders with."""

    cell: Cell
    profile_name: str
    profile: Profile
    workflow: Workflow


def _jobs(entry: str, read: list[tuple[Cell, Line]], fallback: str) -> list[Job]:
    """Pair each cell with its line's profile, else the set's, else the --profile given."""
    profiles: dict[str, tuple[Profile, Workflow]] = {}
    jobs: list[Job] = []
    for cell, line in read:
        name = line.profile or fallback
        if not name:
            msg = f"{entry} {cell.cell_id}: no profile (on its line, its row, or --profile)"
            raise RegisterError(msg)
        if name not in profiles:
            _, profile = load_profile(name)
            profiles[name] = (profile, Workflow.load(Path(profile.workflow)))
        profile, workflow = profiles[name]
        jobs.append(Job(cell, name, profile, workflow))
    return jobs


def _select(entry: str, jobs: list[Job], wanted: str | None) -> list[Job]:
    if wanted is None:
        return jobs
    ids = [cell_arg(part) or part.strip() for part in wanted.split(",") if part.strip()]
    unknown = sorted(set(ids) - {j.cell.cell_id for j in jobs})
    if unknown:
        msg = f"{entry}: no cell {', '.join(unknown)}"
        raise RegisterError(msg)
    return [j for j in jobs if j.cell.cell_id in ids]


def _read(entry: str, lines: Path | None, profile: str | None) -> list[Job]:
    require_lines(entry, lines)
    if lines is not None:
        return _jobs(entry, read_lines(entry, lines), profile or "")
    read = read_entry(entry)
    require_intents([cell for cell, _ in read])
    return _jobs(entry, read, entry_profile(entry) or profile or "")


def run(
    comfy: Comfy, destination: Destination, entry: str, jobs: list[Job], *, replace: bool
) -> int:
    """Render the jobs the destination lacks; return how many failed."""
    cells = destination.to_render(entry, [j.cell for j in jobs], replace=replace)
    todo = {c.cell_id for c in cells}
    failed = 0
    for job in (j for j in jobs if j.cell.cell_id in todo):
        label = f"{entry} {job.cell.cell_id}"
        try:
            png = comfy.render(fill(job.workflow, job.cell, job.profile))
            text = infotext(job.cell, job.profile_name, job.profile, job.workflow)
            where = destination.deliver(
                job.cell, Render(only_parameters(png, text), text), replace=replace
            )
        except (ComfyError, CuratorError) as error:
            sys.stderr.write(f"{label}: {error}\n")
            failed += 1
            continue
        sys.stdout.write(f"{label} → {where}\n")
    if not is_lab(entry):
        send_register(destination.sink, {entry})
    return failed


def _destination(stack: ExitStack) -> Destination:
    """Pick the hosted curator when STILLSTIFT_CURATOR_URL is set, the local store otherwise."""
    client = CuratorClient.from_env()
    if client is not None:
        return HostedCurator(stack.enter_context(closing(client)))
    return LocalStore(stack.enter_context(closing(Store.open())))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="just render", description=__doc__)
    parser.add_argument("entry", help="a page set, e.g. P3, or an experiment or test, X2")
    parser.add_argument("--lines", type=Path, help="a lab set's cell lines, one per cell")
    parser.add_argument("--profile", help="the profile for cells whose line and row name none")
    parser.add_argument("--cells", help="only these cells, e.g. 1,3 or 01,03")
    parser.add_argument("--dry-run", action="store_true", help="print each filled workflow")
    parser.add_argument("--replace", action="store_true", help="render cells again")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        jobs = _select(args.entry, _read(args.entry, args.lines, args.profile), args.cells)
        if args.dry_run:
            graphs = {j.cell.cell_id: fill(j.workflow, j.cell, j.profile) for j in jobs}
            sys.stdout.write(json.dumps(graphs, indent=2) + "\n")
            return 0
        with ExitStack() as stack:
            comfy = stack.enter_context(closing(Comfy.connect()))
            needs = set[tuple[str, str]]().union(*(needed(j.profile, j.workflow) for j in jobs))
            comfy.check_identity(Manifest.read(), needs)
            failed = run(comfy, _destination(stack), args.entry, jobs, replace=args.replace)
    except (ComfyError, CuratorError, RegisterError, ModelError, OSError) as error:
        sys.stderr.write(f"render: {error}\n")
        return 1
    sys.stdout.write(f"{args.entry}: {len(jobs) - failed} of {len(jobs)} done\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
