"""The desktop ComfyUI over its HTTP API: check it is ours, fill a workflow, render, fetch.

A workflow is ComfyUI's API export (`workflows/*.json`). The nodes the render step fills are found
by their title (`_meta.title`), never by node id:

    ckpt       CheckpointLoaderSimple (ckpt_name) or UNETLoader (unet_name)
    clip       CLIPLoader (clip_name); only when the profile sets a text encoder
    vae        VAELoader (vae_name); only when the profile sets a VAE
    lora 1…n   LoraLoader or LoraLoaderModelOnly, filled with the profile's LoRAs in order; a
               node the profile has no LoRA for is dropped and its inputs linked through
    positive   CLIPTextEncode (text)
    negative   CLIPTextEncode (text); optional for workflows without one
    sampler    KSampler (seed, steps, cfg, sampler_name, scheduler)
    guidance   FluxGuidance (guidance); only when the profile sets one
    size       EmptyLatentImage or EmptySD3LatentImage (width, height)
    save       SaveImage (filename_prefix)

Before anything is queued, `Comfy.check_identity` refuses any ComfyUI that is not this project's
install: its output folder must be the one configured, its model folders may hold only files in
`models.yaml`, and every file the render needs must be among them.
"""

from __future__ import annotations

import copy
import hashlib
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import TYPE_CHECKING, Self, cast

import httpx
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from stillstift.models import Manifest
    from stillstift.store import Cell

type Graph = dict[str, dict[str, object]]

URL_ENV = "STILLSTIFT_COMFY_URL"
OUTPUT_ENV = "STILLSTIFT_COMFY_OUTPUT"
DEFAULT_URL = "http://127.0.0.1:8189"
PROFILES = Path("profiles")
POLL_SECONDS = 2.0
MAX_POLLS = 900
REQUEST_TIMEOUT = 60.0


class ComfyError(RuntimeError):
    pass


class LoraSpec(BaseModel):
    name: str
    weight: float = 1.0


class Profile(BaseModel):
    """Pinned generation settings: the workflow, its models and the sampler (profiles/*.json)."""

    workflow: str
    checkpoint: str
    text_encoder: str = ""
    vae: str = ""
    loras: list[LoraSpec] = Field(default_factory=list[LoraSpec])
    prefix: str = ""
    sampler: str = "euler"
    scheduler: str = "normal"
    steps: int = 30
    cfg: float = 7.0
    guidance: float | None = None
    width: int = 896
    height: int = 1152


def load_profile(name: str, folder: Path = PROFILES) -> tuple[str, Profile]:
    """Read profiles/<name>.json; return its name and settings."""
    path = folder / f"{name}.json"
    try:
        return name, Profile.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        msg = f"profile {name}: {error}"
        raise ComfyError(msg) from None


@dataclass(frozen=True)
class Workflow:
    """An API-format workflow and the hash that names it in a render's infotext."""

    graph: Graph
    sha: str

    @classmethod
    def load(cls, path: Path) -> Self:
        try:
            raw = path.read_bytes()
            graph = TypeAdapter(dict[str, dict[str, object]]).validate_json(raw)
        except (OSError, ValidationError) as error:
            msg = f"workflow {path}: {error}"
            raise ComfyError(msg) from None
        return cls(graph, hashlib.sha256(raw).hexdigest()[:12])


def _titled(graph: Graph) -> dict[str, str]:
    """Map each node title to its node id; refuse a title used twice."""
    titles: dict[str, str] = {}
    for node, spec in graph.items():
        meta = spec.get("_meta")
        title = cast("dict[str, object]", meta).get("title") if isinstance(meta, dict) else None
        if not isinstance(title, str):
            continue
        if title in titles:
            msg = f"two nodes are titled {title!r}"
            raise ComfyError(msg)
        titles[title] = node
    return titles


def _inputs(graph: Graph, titles: Mapping[str, str], title: str) -> dict[str, object]:
    node = titles.get(title)
    if node is None:
        msg = f"the workflow has no node titled {title!r}"
        raise ComfyError(msg)
    inputs = graph[node].get("inputs")
    if not isinstance(inputs, dict):
        msg = f"node {title!r} has no inputs"
        raise ComfyError(msg)
    return cast("dict[str, object]", inputs)


def needed(profile: Profile, workflow: Workflow) -> set[tuple[str, str]]:
    """Return the model files a render with this profile loads, as (ComfyUI folder, file name)."""
    ckpt = _inputs(workflow.graph, _titled(workflow.graph), "ckpt")
    folder = "diffusion_models" if "unet_name" in ckpt else "checkpoints"
    files = {(folder, profile.checkpoint)} | {("loras", lora.name) for lora in profile.loras}
    if profile.text_encoder:
        files.add(("text_encoders", profile.text_encoder))
    if profile.vae:
        files.add(("vae", profile.vae))
    return files


def prompt_of(cell: Cell, profile: Profile) -> str:
    """Return the prompt as rendered: the profile's prefix (its trigger words), then the cell's."""
    return ", ".join(part for part in (profile.prefix.strip(), cell.prompt.strip()) if part)


LORA_OUTPUTS = ("model", "clip")


def _bypass(graph: Graph, node: str) -> None:
    """Drop a LoRA node, linking whatever read its outputs to the model and CLIP it was fed."""
    fed = cast("dict[str, object]", graph.pop(node)["inputs"])
    for spec in graph.values():
        inputs = cast("dict[str, object]", spec["inputs"])
        for key, value in inputs.items():
            match value:
                case [str() as source, int() as slot] if source == node:
                    inputs[key] = fed[LORA_OUTPUTS[slot]]
                case _:
                    pass


def fill(workflow: Workflow, cell: Cell, profile: Profile) -> Graph:
    """Return a copy of the workflow with the cell's prompt, seed and the profile's settings."""
    graph = copy.deepcopy(workflow.graph)
    titles = _titled(graph)
    ckpt = _inputs(graph, titles, "ckpt")
    ckpt["unet_name" if "unet_name" in ckpt else "ckpt_name"] = profile.checkpoint
    # A loader the profile leaves unset would load a file `needed` never checks.
    loaders = (
        ("clip", "clip_name", "text_encoder", profile.text_encoder),
        ("vae", "vae_name", "vae", profile.vae),
    )
    for title, key, setting, name in loaders:
        if (title in titles) != bool(name):
            msg = f"a {title!r} node in the workflow needs the profile's {setting}, and vice versa"
            raise ComfyError(msg)
        if name:
            _inputs(graph, titles, title)[key] = name
    lora_nodes = sorted(t for t in titles if t.startswith("lora "))
    if len(lora_nodes) < len(profile.loras):
        msg = f"the workflow has {len(lora_nodes)} LoRA nodes, the profile {len(profile.loras)}"
        raise ComfyError(msg)
    for title, lora in zip(lora_nodes, profile.loras, strict=False):
        inputs = _inputs(graph, titles, title)
        inputs.update(lora_name=lora.name, strength_model=lora.weight)
        if "strength_clip" in inputs:
            inputs["strength_clip"] = lora.weight
    for title in lora_nodes[len(profile.loras) :]:
        _bypass(graph, titles[title])
    _inputs(graph, titles, "positive")["text"] = prompt_of(cell, profile)
    if "negative" in titles:
        _inputs(graph, titles, "negative")["text"] = cell.negative
    sampler = _inputs(graph, titles, "sampler")
    sampler.update(
        seed=cell.seed,
        steps=profile.steps,
        cfg=profile.cfg,
        sampler_name=profile.sampler,
        scheduler=profile.scheduler,
    )
    if profile.guidance is not None:
        _inputs(graph, titles, "guidance")["guidance"] = profile.guidance
    _inputs(graph, titles, "size").update(width=profile.width, height=profile.height)
    _inputs(graph, titles, "save")["filename_prefix"] = f"{cell.entry}_{cell.cell_id.lstrip('#')}"
    return graph


def infotext(cell: Cell, name: str, profile: Profile, workflow: Workflow) -> str:
    """Write the render's generation metadata for the PNG's `parameters` chunk."""
    lines = [prompt_of(cell, profile)]
    if cell.negative:
        lines.append(f"Negative prompt: {cell.negative}")
    settings = [
        f"Steps: {profile.steps}",
        f"Sampler: {profile.sampler}",
        f"Schedule type: {profile.scheduler}",
        f"CFG scale: {profile.cfg:g}",
    ]
    if profile.guidance is not None:
        settings.append(f"Guidance: {profile.guidance:g}")
    settings += [
        f"Seed: {cell.seed}",
        f"Size: {profile.width}x{profile.height}",
        f"Model: {Path(profile.checkpoint).stem}",
    ]
    if profile.text_encoder:
        settings.append(f"Text encoder: {Path(profile.text_encoder).stem}")
    if profile.vae:
        settings.append(f"VAE: {Path(profile.vae).stem}")
    if profile.loras:
        loras = " · ".join(f"{Path(lora.name).stem} @ {lora.weight:g}" for lora in profile.loras)
        settings.append(f"Loras: {loras}")
    settings += [f"Profile: {name}", f"Workflow: {workflow.sha}"]
    lines.append(", ".join(settings))
    return "\n".join(lines)


class Queued(BaseModel):
    prompt_id: str


class HistoryImage(BaseModel):
    filename: str
    subfolder: str = ""
    type: str = "output"


class HistoryOutput(BaseModel):
    images: list[HistoryImage] = Field(default_factory=list[HistoryImage])


class HistoryStatus(BaseModel):
    status_str: str = ""
    completed: bool = False
    messages: list[tuple[str, dict[str, object]]] = Field(
        default_factory=list[tuple[str, dict[str, object]]]
    )


class HistoryEntry(BaseModel):
    status: HistoryStatus = Field(default_factory=HistoryStatus)
    outputs: dict[str, HistoryOutput] = Field(default_factory=dict[str, HistoryOutput])


HISTORY = TypeAdapter(dict[str, HistoryEntry])


class SystemInfo(BaseModel):
    argv: list[str] = Field(default_factory=list[str])


class SystemStats(BaseModel):
    """What /system_stats tells of the running ComfyUI; only its launch arguments are read."""

    system: SystemInfo = Field(default_factory=SystemInfo)


NAMES = TypeAdapter(list[str])


def _finished(entry: HistoryEntry) -> HistoryImage | None:
    """Return the first output image of a finished prompt, None while it runs; raise on failure."""
    status = entry.status
    if status.status_str == "error":
        problems = [
            str(m.get("exception_message", m))
            for kind, m in status.messages
            if kind == "execution_error"
        ]
        msg = f"ComfyUI failed the workflow: {'; '.join(problems) or 'no reason given'}"
        raise ComfyError(msg)
    if not status.completed:
        return None
    images = [i for out in entry.outputs.values() for i in out.images if i.type == "output"]
    if not images:
        msg = "ComfyUI finished the workflow without an image"
        raise ComfyError(msg)
    return images[0]


def _folder_key(path: str) -> str:
    return str(PureWindowsPath(path)).rstrip("\\").lower()


def _same_folder(a: str, b: str) -> bool:
    """Compare two folder paths the way Windows does: case and trailing separators ignored."""
    return _folder_key(a) == _folder_key(b)


@dataclass
class Comfy:
    """The project's ComfyUI: queue a workflow, poll its history, fetch the image."""

    http: httpx.Client
    sleep: Callable[[float], None] = time.sleep
    checked: bool = field(default=False)

    @classmethod
    def connect(
        cls,
        env: Mapping[str, str] = os.environ,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> Self:
        """Connect to STILLSTIFT_COMFY_URL, the desktop install on 127.0.0.1:8189 by default."""
        url = env.get(URL_ENV) or DEFAULT_URL
        http = httpx.Client(base_url=url, transport=transport, timeout=REQUEST_TIMEOUT)
        return cls(http, sleep)

    def close(self) -> None:
        self.http.close()

    def check_identity(
        self,
        manifest: Manifest,
        needs: Iterable[tuple[str, str]] = (),
        env: Mapping[str, str] = os.environ,
    ) -> None:
        """Refuse a ComfyUI that is not this project's install, or that lacks a needed model.

        Its launch arguments must name the configured output folder (`--output-directory`), each
        model folder the manifest covers may hold only the manifest's files, and every needed
        (folder, file) must be listed in the manifest and present. A listed file nothing needs
        may be absent, e.g. one that still waits for its download token.
        """
        output = env.get(OUTPUT_ENV, "")
        if not output:
            msg = f"set {OUTPUT_ENV} to the output folder this project's ComfyUI is started with"
            raise ComfyError(msg)
        args = self._read("/system_stats", TypeAdapter(SystemStats)).system.argv
        given = next(
            (args[i + 1] for i, a in enumerate(args[:-1]) if a == "--output-directory"), None
        )
        if given is None or not _same_folder(given, output):
            msg = (
                f"the ComfyUI at {self.http.base_url} is not this project's install"
                f" (its --output-directory is not {output}); refusing to queue anything"
            )
            raise ComfyError(msg)
        required = frozenset(needs)
        listed = manifest.by_folder()
        unlisted = sorted(
            f"{folder}/{name}" for folder, name in required if name not in listed.get(folder, set())
        )
        if unlisted:
            msg = f"the render needs models not in models.yaml: {', '.join(unlisted)}"
            raise ComfyError(msg)
        for folder, wanted in listed.items():
            held = set(self._read(f"/models/{folder}", NAMES))
            extra = sorted(held - wanted)
            if extra:
                msg = f"ComfyUI's {folder} holds files not in models.yaml: {', '.join(extra)}"
                raise ComfyError(msg)
            missing = sorted(name for f, name in required if f == folder and name not in held)
            if missing:
                msg = f"ComfyUI's {folder} lacks {', '.join(missing)}: run `just models`"
                raise ComfyError(msg)
        self.checked = True

    def render(self, graph: Graph) -> bytes:
        """Run the graph and return the PNG it saved."""
        if not self.checked:
            msg = "check_identity first"
            raise ComfyError(msg)
        prompt_id = self._queue(graph)
        image = self._wait(prompt_id)
        params = {"filename": image.filename, "subfolder": image.subfolder, "type": image.type}
        response = self._send(self.http.build_request("GET", "/view", params=params))
        self._require(response, f"fetch {image.filename}")
        return response.content

    def _queue(self, graph: Graph) -> str:
        body = {"prompt": graph, "client_id": uuid.uuid4().hex}
        response = self._send(self.http.build_request("POST", "/prompt", json=body))
        self._require(response, "queue the workflow")
        try:
            return Queued.model_validate_json(response.content).prompt_id
        except ValidationError:
            msg = f"ComfyUI answered /prompt without a prompt_id: {response.text[:200]}"
            raise ComfyError(msg) from None

    def _wait(self, prompt_id: str) -> HistoryImage:
        for _ in range(MAX_POLLS):
            entry = self._history(prompt_id)
            image = None if entry is None else _finished(entry)
            if image is not None:
                return image
            self.sleep(POLL_SECONDS)
        msg = f"ComfyUI did not finish {prompt_id} in {MAX_POLLS * POLL_SECONDS:.0f} s"
        raise ComfyError(msg)

    def _history(self, prompt_id: str) -> HistoryEntry | None:
        try:
            response = self._send(self.http.build_request("GET", f"/history/{prompt_id}"))
            return HISTORY.validate_json(response.content).get(prompt_id)
        except (ComfyError, ValidationError):
            return None

    def _read[T](self, path: str, adapter: TypeAdapter[T]) -> T:
        response = self._send(self.http.build_request("GET", path))
        self._require(response, f"read {path}")
        try:
            return adapter.validate_json(response.content)
        except ValidationError:
            msg = f"ComfyUI answered {path} with something unexpected: {response.text[:200]}"
            raise ComfyError(msg) from None

    def _send(self, request: httpx.Request) -> httpx.Response:
        try:
            return self.http.send(request)
        except httpx.TransportError as error:
            msg = f"ComfyUI is not reachable at {self.http.base_url} ({error})"
            raise ComfyError(msg) from None

    @staticmethod
    def _require(response: httpx.Response, what: str) -> None:
        if not response.is_success:
            msg = f"{what}: HTTP {response.status_code} {response.text[:500]}"
            raise ComfyError(msg)
