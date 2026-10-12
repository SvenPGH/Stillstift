from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from stillstift.comfy import Comfy, ComfyError, Workflow, fill, load_profile, needed
from stillstift.models import Manifest, ModelFile
from stillstift.store import Cell

OUTPUT = r"D:\Stillstift\outputs"
ENV = {"STILLSTIFT_COMFY_OUTPUT": OUTPUT}
CELL = Cell(
    entry="T1",
    cell_id="#01",
    dimension="",
    value="",
    prompt="a hedgehog in a garden",
    negative="color",
    seed=7,
    prediction=None,
    prediction_reason="",
)


def node(graph: dict[str, dict[str, object]], title: str) -> dict[str, object]:
    found = [spec for spec in graph.values() if spec.get("_meta") == {"title": title}]
    assert len(found) == 1, title
    return found[0]


@pytest.mark.parametrize("profile", ["sdxl-redmond", "sdxl-ax", "flux-coloring"])
def test_each_profile_fills_its_workflow(profile: str) -> None:
    _, settings = load_profile(profile)
    graph = fill(Workflow.load(Path(settings.workflow)), CELL, settings)
    assert node(graph, "ckpt")["class_type"] == "CheckpointLoaderSimple"
    assert node(graph, "ckpt")["inputs"] == {"ckpt_name": settings.checkpoint}
    lora = node(graph, "lora 1")["inputs"]
    assert isinstance(lora, dict)
    assert lora["lora_name"] == settings.loras[0].name
    positive = node(graph, "positive")["inputs"]
    assert isinstance(positive, dict)
    assert positive["text"] == f"{settings.prefix}, {CELL.prompt}"
    sampler = node(graph, "sampler")["inputs"]
    assert isinstance(sampler, dict)
    assert (sampler["seed"], sampler["steps"]) == (7, settings.steps)
    save = node(graph, "save")["inputs"]
    assert isinstance(save, dict)
    assert save["filename_prefix"] == "T1_01"


@pytest.mark.parametrize("path", sorted(Path("workflows").glob("*.json")))
def test_workflows_are_api_format_and_link_existing_nodes(path: Path) -> None:
    graph = json.loads(path.read_text(encoding="utf-8"))
    for spec in graph.values():
        assert isinstance(spec["class_type"], str)
        for value in spec["inputs"].values():
            if isinstance(value, list):
                assert value[0] in graph, f"{path}: link to missing node {value[0]}"
    for title in ("ckpt", "lora 1", "positive", "sampler", "size", "save"):
        node(graph, title)


def test_needed_names_checkpoint_and_loras() -> None:
    _, settings = load_profile("sdxl-redmond")
    assert needed(settings, Workflow.load(Path(settings.workflow))) == {
        ("checkpoints", "sd_xl_base_1.0.safetensors"),
        ("loras", "ColoringBookRedmond-V2.safetensors"),
    }


def manifest(*names: tuple[str, str]) -> Manifest:
    files = [
        ModelFile.model_validate(
            {
                "folder": folder,
                "name": name,
                "url": "https://huggingface.co/x",
                "license": "test",
                "commercial_images": "yes",
            }
        )
        for folder, name in names
    ]
    return Manifest(files=files)


def comfy(held: dict[str, list[str]], output: str = OUTPUT) -> Comfy:
    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/system_stats":
            argv = ["main.py", "--output-directory", output, "--disable-metadata"]
            return httpx.Response(200, json={"system": {"argv": argv}})
        folder = request.url.path.removeprefix("/models/")
        return httpx.Response(200, json=held.get(folder, []))

    return Comfy.connect({}, httpx.MockTransport(answer))


LISTED = manifest(("checkpoints", "base.safetensors"), ("checkpoints", "later.safetensors"))
NEEDS = {("checkpoints", "base.safetensors")}


def test_identity_accepts_a_listed_file_nothing_needs_being_absent() -> None:
    c = comfy({"checkpoints": ["base.safetensors"]})
    c.check_identity(LISTED, NEEDS, ENV)
    assert c.checked


def test_identity_refuses_another_output_folder() -> None:
    with pytest.raises(ComfyError, match="not this project's install"):
        comfy({"checkpoints": ["base.safetensors"]}, r"C:\other\output").check_identity(
            LISTED, NEEDS, ENV
        )


def test_identity_refuses_a_file_outside_the_manifest() -> None:
    held = {"checkpoints": ["base.safetensors", "stray.safetensors"]}
    with pytest.raises(ComfyError, match=r"not in models\.yaml: stray"):
        comfy(held).check_identity(LISTED, NEEDS, ENV)


def test_identity_refuses_a_needed_file_that_is_missing_or_unlisted() -> None:
    with pytest.raises(ComfyError, match=r"lacks base\.safetensors"):
        comfy({}).check_identity(LISTED, NEEDS, ENV)
    with pytest.raises(ComfyError, match=r"needs models not in models\.yaml"):
        comfy({}).check_identity(LISTED, {("loras", "unknown.safetensors")}, ENV)


def test_render_needs_the_identity_check_first() -> None:
    with pytest.raises(ComfyError, match="check_identity first"):
        comfy({}).render({})
