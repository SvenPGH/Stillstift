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
    for title in ("ckpt", "positive", "sampler", "size", "save"):
        node(graph, title)


def test_needed_names_checkpoint_and_loras() -> None:
    _, settings = load_profile("sdxl-redmond")
    assert needed(settings, Workflow.load(Path(settings.workflow))) == {
        ("checkpoints", "sd_xl_base_1.0.safetensors"),
        ("loras", "ColoringBookRedmond-V2.safetensors"),
    }


def test_krea2_fills_its_three_loaders_and_needs_their_files() -> None:
    _, settings = load_profile("krea2-turbo")
    workflow = Workflow.load(Path(settings.workflow))
    graph = fill(workflow, CELL, settings)
    assert node(graph, "ckpt")["inputs"] == {
        "unet_name": "krea2_turbo_fp8_scaled.safetensors",
        "weight_dtype": "default",
    }
    clip = node(graph, "clip")["inputs"]
    assert isinstance(clip, dict)
    assert (clip["clip_name"], clip["type"]) == ("qwen3vl_4b_fp8_scaled.safetensors", "krea2")
    assert node(graph, "vae")["inputs"] == {"vae_name": "krea2_vae.safetensors"}
    positive = node(graph, "positive")["inputs"]
    assert isinstance(positive, dict)
    assert positive["text"] == CELL.prompt
    sampler = node(graph, "sampler")["inputs"]
    assert isinstance(sampler, dict)
    assert (sampler["steps"], sampler["cfg"], sampler["scheduler"]) == (8, 1.5, "simple")
    assert all(spec.get("_meta") != {"title": "lora 1"} for spec in graph.values())
    assert sampler["model"] == ["1", 0]
    assert needed(settings, workflow) == {
        ("diffusion_models", "krea2_turbo_fp8_scaled.safetensors"),
        ("text_encoders", "qwen3vl_4b_fp8_scaled.safetensors"),
        ("vae", "krea2_vae.safetensors"),
    }


@pytest.mark.parametrize(
    ("profile", "weight"), [("krea2-turbo-coloring-06", 0.6), ("krea2-turbo-coloring", 1.0)]
)
def test_krea2_coloring_loads_its_lora_between_model_and_sampler(
    profile: str, weight: float
) -> None:
    _, settings = load_profile(profile)
    workflow = Workflow.load(Path(settings.workflow))
    graph = fill(workflow, CELL, settings)
    lora = node(graph, "lora 1")
    assert lora["class_type"] == "LoraLoaderModelOnly"
    assert lora["inputs"] == {
        "lora_name": "krea2-coloring-book.safetensors",
        "strength_model": weight,
        "model": ["1", 0],
    }
    sampler = node(graph, "sampler")["inputs"]
    assert isinstance(sampler, dict)
    assert sampler["model"] == ["10", 0]
    positive = node(graph, "positive")["inputs"]
    assert isinstance(positive, dict)
    assert positive["text"] == f"{settings.prefix}, {CELL.prompt}"
    assert ("loras", "krea2-coloring-book.safetensors") in needed(settings, workflow)


def test_fill_refuses_more_loras_than_the_workflow_has_nodes() -> None:
    _, settings = load_profile("krea2-turbo-coloring")
    two = [*settings.loras, *settings.loras]
    with pytest.raises(ComfyError, match="1 LoRA nodes, the profile 2"):
        fill(
            Workflow.load(Path(settings.workflow)), CELL, settings.model_copy(update={"loras": two})
        )


def test_fill_refuses_a_loader_the_profile_leaves_unset() -> None:
    _, settings = load_profile("krea2-turbo")
    workflow = Workflow.load(Path(settings.workflow))
    with pytest.raises(ComfyError, match="text_encoder"):
        fill(workflow, CELL, settings.model_copy(update={"text_encoder": ""}))


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


def test_identity_checks_the_text_encoder_and_vae_folders() -> None:
    listed = manifest(
        ("diffusion_models", "k.safetensors"),
        ("text_encoders", "te.safetensors"),
        ("vae", "v.safetensors"),
    )
    needs = {
        ("diffusion_models", "k.safetensors"),
        ("text_encoders", "te.safetensors"),
        ("vae", "v.safetensors"),
    }
    held = {
        "diffusion_models": ["k.safetensors"],
        "text_encoders": ["te.safetensors"],
        "vae": ["v.safetensors"],
    }
    comfy(held).check_identity(listed, needs, ENV)
    with pytest.raises(ComfyError, match=r"vae holds files not in models\.yaml: stray"):
        comfy(held | {"vae": ["v.safetensors", "stray.safetensors"]}).check_identity(
            listed, needs, ENV
        )
    with pytest.raises(ComfyError, match=r"text_encoders lacks te\.safetensors"):
        comfy(held | {"text_encoders": []}).check_identity(listed, needs, ENV)


def test_render_needs_the_identity_check_first() -> None:
    with pytest.raises(ComfyError, match="check_identity first"):
        comfy({}).render({})
