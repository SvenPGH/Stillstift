# Stillstift

Stillstift renders coloring-book pages on a local ComfyUI, rates them in a small web curator with
two raters, and (eventually) assembles the keepers into a print-ready interior PDF for Amazon KDP.

- `stillstift/comfy.py`, `render.py` — fill a workflow (`workflows/*.json`) with a profile
  (`profiles/*.json`), queue it on the project's own ComfyUI, and store the result.
- `stillstift/curator.py`, `store.py`, `ratings.py` — the FastAPI rating app: login, upload,
  rate, favorite, export (`stillstift/static/*` is its plain-JS/HTML/CSS frontend).
- `stillstift/register.py`, `score.py`, `scoring.py`, `sheet.py`, `sync.py`, `lab.py` — the
  register of sets (`register/*.csv`), recall scoring, contact sheets, and experiment/test sets.
- `stillstift/models.py` — downloads only the models listed in `models.yaml`, checked by SHA-256.

## Setup

Requires Python 3.12+, Node, [uv](https://docs.astral.sh/uv/), and
[`just`](https://github.com/casey/just).

```sh
uv lock && uv sync
npm install
cp .env.example .env   # fill in the basic-auth login and the raters' names at least
```

The curator shares one basic-auth login between its raters; `STILLSTIFT_RATERS` (comma-separated,
e.g. `Sven,Anna`) names who is rating, picked in the header and remembered per browser. Every
rating, favorite and the like is kept per rater, so the same page can hold one of each.

## Commands (justfile)

| command | what it does |
|---|---|
| `just gates` | format, lint, type-check and test both languages; must pass before a push |
| `just curate` | run the rating app locally at `http://127.0.0.1:8765` |
| `just comfy` | start the project's own ComfyUI (`scripts/comfy.ps1`) on 127.0.0.1:8189 |
| `just render <entry> [...]` | render a set's cells on the project's ComfyUI |
| `just models [name ...]` | download the models in `models.yaml` (or only those named) into the project's ComfyUI |
| `just lab <kind> <name> ...` | create an experiment (`X`) or a test (`T`) set |
| `just score <entry>` | write a set's ratings to `register/predictions.csv`, print recall |
| `just sheet <entry>` | one labelled contact sheet of a set's cells |

Docker: `docker compose up` runs the curator against `Dockerfile`/`docker-compose.yml`; it needs
`uv.lock` and the `.env` values above.

See `CLAUDE.md` for conventions when working on this project with an agent.
