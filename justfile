set shell := ["bash", "-euo", "pipefail", "-c"]
set dotenv-load

# Format, lint, type-check and test both languages; all must pass before a push.
gates: format lint types test

format:
    uv run ruff format --check .
    npx prettier --check stillstift/static

lint:
    uv run ruff check .
    npx eslint stillstift/static

types:
    uv run pyright
    npx tsc -p .

test:
    uv run pytest
    npx vitest run --passWithNoTests

# Rate rendered cells in the browser at http://127.0.0.1:8765 (local only).
curate:
    uv run python -m stillstift.curator

# Render a set's cells on the project's ComfyUI (STILLSTIFT_COMFY_URL): --lines <file> for a lab set, --profile, --cells 01,03, --dry-run, --replace. Uploads to the hosted curator when STILLSTIFT_CURATOR_URL is set.
[positional-arguments]
render entry *args:
    uv run python -m stillstift.render "$@"

# Download the models in models.yaml into the project's ComfyUI (STILLSTIFT_COMFY_MODELS), checked against their SHA-256.
[positional-arguments]
models *args:
    uv run python -m stillstift.models "$@"

# Create an experiment (X) or a test (T) and print its id: just lab X "<name>" --tests "<what it tests>".
[positional-arguments]
lab kind name *args:
    uv run python -m stillstift.lab "$@"

# Write a page set's ratings into register/predictions.csv and print kill/fav recall.
score entry:
    uv run python -m stillstift.score {{entry}}

# One labelled contact sheet of a set's cells: data/sheets/<entry>.png.
sheet entry:
    uv run python -m stillstift.sheet {{entry}}