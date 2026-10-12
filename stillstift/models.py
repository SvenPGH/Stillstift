r"""`just models`: download the models in models.yaml into the project's ComfyUI, verified.

Every file comes from huggingface.co or civitai.com, with this project's own tokens, and is
checked against its SHA-256 when the manifest pins one, also when it is on disk already. A file
without a pinned hash is downloaded and its hash printed, to be pinned after its license and
source are checked. Name files to fetch only those, e.g. while another still waits for a token.

The tokens come from the environment or from the project's key file outside the repo
(STILLSTIFT_SECRETS, D:\Stillstift\.env by default); they are sent, never printed.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlparse

import httpx
import yaml
from pydantic import BaseModel, Field, ValidationError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

MANIFEST = Path("models.yaml")
MODELS_ENV = "STILLSTIFT_COMFY_MODELS"
TOKENS = {"huggingface.co": "STILLSTIFT_HF_TOKEN", "civitai.com": "STILLSTIFT_CIVITAI_TOKEN"}
SECRETS_ENV = "STILLSTIFT_SECRETS"
DEFAULT_SECRETS = r"D:\Stillstift\.env"
FOLDERS = (
    "checkpoints",
    "diffusion_models",
    "loras",
    "upscale_models",
    "vae",
    "text_encoders",
)
CHUNK = 1 << 20
TIMEOUT = httpx.Timeout(60.0, read=600.0)


class ModelError(RuntimeError):
    pass


class ModelFile(BaseModel):
    """One file of the manifest: where it goes, where it comes from, and its terms."""

    folder: Literal[
        "checkpoints", "diffusion_models", "loras", "upscale_models", "vae", "text_encoders"
    ]
    name: str
    url: str
    sha256: str = ""
    license: str
    commercial_images: Literal["yes", "no", "unverified"]
    checked: str = ""
    note: str = ""


class Manifest(BaseModel):
    files: list[ModelFile] = Field(default_factory=list[ModelFile])

    @classmethod
    def read(cls, path: Path = MANIFEST) -> Manifest:
        try:
            return cls.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
        except (OSError, yaml.YAMLError, ValidationError) as error:
            msg = f"{path}: {error}"
            raise ModelError(msg) from None

    def by_folder(self) -> dict[str, set[str]]:
        """Every model folder the project uses, with the file names it must hold exactly."""
        folders: dict[str, set[str]] = {folder: set() for folder in FOLDERS}
        for f in self.files:
            folders[f.folder].add(f.name)
        return folders


def with_tokens(env: Mapping[str, str]) -> dict[str, str]:
    """Return the environment plus the download tokens from the project's key file.

    The file stays outside the repo so the keys are never copied in. Only the token keys are
    read from it, and a token already set in the environment wins.
    """
    path = Path(env.get(SECRETS_ENV) or DEFAULT_SECRETS)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return dict(env)
    except OSError as error:
        msg = f"cannot read the key file {path}: {error.strerror}"
        raise ModelError(msg) from None
    found: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.strip().removeprefix("export ").partition("=")
        if sep and key.strip() in TOKENS.values():
            found[key.strip()] = value.strip().strip("\"'")
    return found | {key: value for key, value in env.items() if value}


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    allowed = next((h for h in TOKENS if host == h or host.endswith(f".{h}")), None)
    if allowed is None or urlparse(url).scheme != "https":
        msg = f"{url}: models come only from https://huggingface.co or https://civitai.com"
        raise ModelError(msg)
    return allowed


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def _require(response: httpx.Response, name: str) -> None:
    if not response.is_success:
        msg = f"{name}: HTTP {response.status_code}"
        raise ModelError(msg)


def fetch(model: ModelFile, root: Path, env: Mapping[str, str], http: httpx.Client) -> str:
    """Download one file unless it is there already; return its SHA-256."""
    target = root / model.folder / model.name
    if target.is_file():
        return _pinned(model, _sha256(target))
    if model.commercial_images != "yes":
        msg = f"{model.name}: its images may not be sold ({model.commercial_images}); not fetched"
        raise ModelError(msg)
    token = env.get(TOKENS[_host(model.url)], "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".part", delete=False) as out:
        part = Path(out.name)
        try:
            with http.stream("GET", model.url, headers=headers, follow_redirects=True) as response:
                _require(response, model.name)
                for block in response.iter_bytes(CHUNK):
                    digest.update(block)
                    out.write(block)
        except (httpx.HTTPError, ModelError):
            out.close()
            part.unlink(missing_ok=True)
            raise
    try:
        found = _pinned(model, digest.hexdigest())
    except ModelError:
        part.unlink(missing_ok=True)
        raise
    part.replace(target)
    return found


def _pinned(model: ModelFile, found: str) -> str:
    """Return the hash found; raise when the manifest pins a different one."""
    if model.sha256 and found != model.sha256.lower():
        msg = f"{model.name}: SHA-256 {found} is not the pinned {model.sha256}"
        raise ModelError(msg)
    return found


def _chosen(manifest: Manifest, names: Sequence[str]) -> list[ModelFile]:
    """Return the manifest's files, or only those named; refuse a name it lacks."""
    if not names:
        return manifest.files
    unknown = sorted(set(names) - {f.name for f in manifest.files})
    if unknown:
        msg = f"not in the manifest: {', '.join(unknown)}"
        raise ModelError(msg)
    return [f for f in manifest.files if f.name in names]


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] = os.environ) -> int:
    parser = argparse.ArgumentParser(prog="just models", description=__doc__)
    parser.add_argument("names", nargs="*", help="only these files (by name); all by default")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args(argv)
    root = env.get(MODELS_ENV, "")
    if not root:
        sys.stderr.write(f"models: set {MODELS_ENV} to the project ComfyUI's models folder\n")
        return 1
    try:
        env = with_tokens(env)
        chosen = _chosen(Manifest.read(args.manifest), args.names)
        failed = 0
        with httpx.Client(timeout=TIMEOUT) as http:
            for model in chosen:
                try:
                    found = fetch(model, Path(root), env, http)
                except (ModelError, httpx.HTTPError, OSError) as error:
                    sys.stderr.write(f"models: {error}\n")
                    failed += 1
                    continue
                pin = "" if model.sha256 else "  (pin this sha256 in models.yaml)"
                sys.stdout.write(f"{model.folder}/{model.name}  {found}{pin}\n")
    except ModelError as error:
        sys.stderr.write(f"models: {error}\n")
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
