# CLAUDE.md

Stillstift renders coloring-book pages on a local ComfyUI, rates them with two raters in a small
web curator (FastAPI + plain JS), and will eventually assemble the keepers into a print-ready
interior PDF for Amazon KDP (A4). See `README.md` for the module map and setup.

## Commands

- `just gates` — format, lint, type-check, test; must pass before a push (runs `ruff`, `pyright`,
  `prettier`, `eslint`, `tsc`, `pytest`, `vitest`).
- `just format`, `just lint`, `just types`, `just test` — run one gate at a time.
- `just curate` — run the rating app locally.
- `just render`, `just models`, `just lab`, `just score`, `just sheet` — see `README.md`.

Run the relevant gate after any change before calling it done; don't weaken `ruff.toml`,
`pyrightconfig.json`, `tsconfig.json` or `eslint.config.js` to make a failure go away — fix the
code instead.

## Conventions

- Comments only for the non-obvious why (a constraint, a workaround, an invariant that would
  surprise a reader) — never for what the code already says.
- Checks are strict on purpose: `ruff` lints with `select = ["ALL"]`, `pyright` runs strict,
  `tsc` runs strict with `checkJs`. Fix the code to satisfy them.
- Workflow nodes are filled by title (`_meta.title`), never by node id — see the header of
  `stillstift/comfy.py` for the title contract a workflow JSON must honor.
- Only family-friendly line art, ever — never explicit or sexual content, in rendered pages,
  profiles, workflows, test fixtures, or prompts.
- Models come only from `models.yaml`, and only entries with `commercial_images: "yes"`; every
  file is checked by SHA-256 before use. Never add a model or loosen that check to unblock a
  render.
