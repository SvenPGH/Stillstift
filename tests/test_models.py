from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import httpx
import pytest

from stillstift.models import Manifest, ModelError, ModelFile, fetch, main, with_tokens

if TYPE_CHECKING:
    from pathlib import Path

BODY = b"model weights"
SHA = hashlib.sha256(BODY).hexdigest()
URL = "https://huggingface.co/org/repo/resolve/main/file.safetensors"


def model(**changes: str) -> ModelFile:
    fields = {
        "folder": "loras",
        "name": "a.safetensors",
        "url": URL,
        "sha256": SHA,
        "license": "test",
        "commercial_images": "yes",
    }
    return ModelFile.model_validate(fields | changes)


def client(body: bytes = BODY, seen: list[httpx.Request] | None = None) -> httpx.Client:
    def answer(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(200, content=body)

    return httpx.Client(transport=httpx.MockTransport(answer))


def test_fetch_writes_a_file_matching_its_pin(tmp_path: Path) -> None:
    assert fetch(model(), tmp_path, {}, client()) == SHA
    assert (tmp_path / "loras" / "a.safetensors").read_bytes() == BODY


def test_fetch_refuses_a_download_with_another_hash(tmp_path: Path) -> None:
    with pytest.raises(ModelError, match="not the pinned"):
        fetch(model(), tmp_path, {}, client(b"something else"))
    assert list((tmp_path / "loras").iterdir()) == []


def test_fetch_refuses_a_file_on_disk_with_another_hash(tmp_path: Path) -> None:
    target = tmp_path / "loras" / "a.safetensors"
    target.parent.mkdir()
    target.write_bytes(b"tampered")
    with pytest.raises(ModelError, match="not the pinned"):
        fetch(model(), tmp_path, {}, client())


def test_fetch_sends_the_project_token_for_its_host(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []
    fetch(model(), tmp_path, {"STILLSTIFT_HF_TOKEN": "t0k"}, client(seen=seen))
    assert seen[0].headers["Authorization"] == "Bearer t0k"


def test_fetch_refuses_other_hosts_and_unsellable_images(tmp_path: Path) -> None:
    with pytest.raises(ModelError, match="only from"):
        fetch(model(url="https://example.org/a.safetensors"), tmp_path, {}, client())
    with pytest.raises(ModelError, match="may not be sold"):
        fetch(model(commercial_images="unverified"), tmp_path, {}, client())


def test_main_fetches_only_the_named_files(tmp_path: Path) -> None:
    manifest = tmp_path / "models.yaml"
    manifest.write_text(
        f"files:\n  - {{folder: loras, name: a.safetensors, url: {URL}, sha256: {SHA},"
        " license: test, commercial_images: 'yes'}\n",
        encoding="utf-8",
    )
    env = {"STILLSTIFT_COMFY_MODELS": str(tmp_path), "STILLSTIFT_SECRETS": str(tmp_path / "none")}
    assert main(["b.safetensors", "--manifest", str(manifest)], env) == 1
    assert not (tmp_path / "loras").exists()


def test_the_manifest_pins_every_file_it_lets_render() -> None:
    manifest = Manifest.read()
    names = {f.name for f in manifest.files}
    assert {"sd_xl_base_1.0.safetensors", "ColoringBookRedmond-V2.safetensors"} <= names
    for f in manifest.files:
        assert f.commercial_images == "yes", f.name
        assert f.url.startswith(("https://huggingface.co/", "https://civitai.com/")), f.name
        if f.name != "flux1-dev-fp8.safetensors":
            assert len(f.sha256) == 64, f.name


def test_tokens_come_from_the_key_file_and_the_environment_wins(tmp_path: Path) -> None:
    keys = tmp_path / ".env"
    keys.write_text(
        'STILLSTIFT_CIVITAI_TOKEN="from-file"\nSTILLSTIFT_HF_TOKEN=file-hf\nOTHER=ignored\n',
        encoding="utf-8",
    )
    env = with_tokens({"STILLSTIFT_SECRETS": str(keys), "STILLSTIFT_HF_TOKEN": "from-env"})
    tokens = (env["STILLSTIFT_CIVITAI_TOKEN"], env["STILLSTIFT_HF_TOKEN"])
    assert tokens == ("from-file", "from-env")
    assert "OTHER" not in env


def test_a_missing_key_file_leaves_the_environment_as_is(tmp_path: Path) -> None:
    env = {"STILLSTIFT_SECRETS": str(tmp_path / "absent")}
    assert with_tokens(env) == env
