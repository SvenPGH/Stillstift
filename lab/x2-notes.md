# X2 — Quality tags on sdxl-ax, and Krea 2 Turbo

16 pages: 4 arms x X1's 4 subjects (hedgehog family picnic, old town street, sea turtle, floral
mandala), same seeds as X1 (101/102/103/104), 896x1152, no upscale. Lines: `lab/x2.txt`. Rendered
2026-10-13 as a hub job into the local store next to X1; all 16 cells are in it, and each one's
prompt, negative, seed, profile and settings (store row and PNG infotext) match its line.

## What it tests

X1's B (sdxl-ax) was the most interesting arm but rough: half-drawn lines, an extra hand,
muddiness. Its prompts had no quality tags, and its negative nothing about anatomy. X2 asks
whether quality wording fixes that on B, and whether Krea 2 Turbo, prompted in tags or in prose,
does better than B at all.

| cells | arm | profile | positive | negative |
|---|---|---|---|---|
| 01–04 | B+Q | sdxl-ax (as in X1) | quality tags, then X1's subject text unchanged | X1's + anatomy/quality terms |
| 05–08 | K-T | krea2-turbo | X1's subject text verbatim (tag style), no quality words | X1's |
| 09–12 | K | krea2-turbo | X1's subjects as prose: a black-and-white coloring page, clean outlines, white fill, no shading | X1's |
| 13–16 | K+Q | krea2-turbo | K's prose plus one sentence of quality wording | B+Q's |

- B+Q against X1 05–08: do the tags and the anatomy negative alone clean up B's lines and hands?
- K-T against X1 05–08: Krea 2 Turbo (Qwen3-VL text encoder, 8 steps, euler/simple, CFG 1.5 so
  the negative still applies) against B with the very same prompt, negative and seed: only the
  model differs.
- K against K-T: does Krea 2 do better with prose than with X1's tag-style prompt?
- K+Q against K: does quality wording in prose help Krea 2 the way tags may help SDXL?

The Krea workflow (`workflows/krea2.json`) is the core of ComfyUI's "Krea-2: Text to Image"
template: UNETLoader, CLIPLoader (type `krea2`), VAELoader, EmptyLatentImage, KSampler. It leaves
out the template's prompt enhancement (a TextGenerate pass that rewrites the prompt) so every cell
renders exactly the text in its line, and replaces its zeroed negative with a real one.

## Sheets and pages

`just sheet` lays out one set's cells only and cannot add X1's B row, so `lab/x2_sheets.py`
(`uv run python -m lab.x2_sheets`) writes both sheets from the raw ComfyUI PNGs:

- `D:\Stillstift\probe-2-sheet.png`: X2's four arms (rows) x four subjects (columns).
- `D:\Stillstift\probe-2-compare.png`: the same with X1's B row (X1 05–08) on top.
- `D:\Stillstift\probe-2\`: X2's pages as `BQ|KT|K|KQ-<1..4>-<subject>.png`.

## Per-arm assessment

Measured share of strongly coloured pixels (saturation > 60) per page: 0.0–0.1 % on every B+Q, K
and K+Q page; 42 %, 58 % and 44 % on K-T's hedgehogs, old town and turtle.

**B+Q — sdxl-ax + quality tags (01–04).** Still B: busy, detailed, and rough. The tags did not
fix what X1 showed. Hedgehogs (01): no extra hand this time, but the right hedgehog's snout is a
doubled, pointed shape, the picnic is barely there (no blanket, a smudge of a basket), and the
flower foreground and background rocks are muddy grey texture. Old town (02): wobbly, half-drawn
lines throughout, flower boxes as grey mush, bicycle frames and wheels broken and merged. Turtle
(03): the flippers and head are again solid black patterned fills, as in X1, and the corals at
the edges are grey speckle. Mandala (04): B's best page, bold and closed, but lumpy and not
truly radially symmetric (an oval centre). Tags and the anatomy negative changed the
composition (same seed, different picture) more than the finish.

**K-T — Krea 2, X1's tag prompts (05–08).** Clean, well-drawn illustrations, but in full colour
on three of four subjects: a cartoon hedgehog picnic with a red-check blanket, a watercolour
half-timbered street, a painted reef. X1's prompts never say black-and-white or coloring page;
"clean bold outlines, plain white background" reads as an illustration on white, and the
negative's "color, colour …" at CFG 1.5 barely pushes back. The mandala (08) came out as line
art, since a mandala in these words is already a coloring motif, but with soft grey shading in
the petals and an off-white ground. Not the tags' fault as such: the prompt has to name the page.

**K — Krea 2, prose (09–12).** Every page is a real coloring page: black outlines on white, no
colour, no grey fill, correct anatomy (no extra hands or limbs on any animal). Hedgehogs (09):
bold, friendly, simple; the fur is open hatching strokes and the blanket's thin check lines
break off, so a few areas don't close; the top quarter of the page is empty. Old town (10): very
clean, intricate and consistent, a convincing street in perspective with cobbles, bakery window,
bicycles and flower boxes; lines are fine (it reads grey when shrunk) but crisp. Turtle (11):
clean bold outer lines with fine scale texture on the flippers; a few seafloor lines end open.
Mandala (12): crisp, radial, very dense, with small hatch strokes inside the petals; for adults.

**K+Q — Krea 2, prose + quality (13–16).** Same compositions as K per seed, slightly cleaner.
Hedgehogs (13): the blanket becomes one large closed shape instead of a broken grid, the basket
reads cleaner and a second baby hedgehog appears; bigger, more closed areas to colour. The empty
top quarter remains. Old town (14): near-identical to K, just as clean. Turtle (15): more even
line weight, one more fish, lighter coral. Mandala (16): a little less hatching inside the
petals than K, so more open areas to colour. No page is worse than its K twin.

## Verdict and next steps

Sven's verdicts: Krea is "miles better" visually, so Stillstift sticks with Krea 2 Turbo, and
SDXL (sdxl-ax, sdxl-redmond) is retired. K-T came out in colour because X1's prompts never say
black-and-white and the negative at CFG 1.5 barely pushes back, so a Krea prompt must say it is a
black-and-white coloring page. K+Q's hedgehogs gave cleaner, more closed areas to colour than
K's; K's old town is "super clean".

Taken forward: K+Q (prose that names the coloring page, plus the quality sentence and the B+Q
negative) as the Krea 2 base. Still open: open hatching strokes on fur and fine texture, an
empty top quarter on the hedgehog page, and lines on the detailed subjects thin enough to read
grey when printed small.

Next: X3 = K+Q as the base plus a Krea 2 coloring-book LoRA at two strengths, same subjects and
seeds.
