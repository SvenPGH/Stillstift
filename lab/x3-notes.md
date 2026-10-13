# X3 — Krea 2 Turbo + a coloring-book LoRA, at two strengths

Rendered 2026-10-13 as a hub job into the local store next to X1 and X2; all 8 cells are in it,
and each one's prompt, negative, seed, profile and LoRA weight (store row and PNG infotext) match
its line. 8 pages: X2's K+Q (Krea 2 Turbo, prose that names the coloring page, the
quality sentence and the B+Q negative) plus the "Krea2 Coloring Book" LoRA, at 0.6 and 1.0, on
X1's 4 subjects with the same seeds (101/102/103/104), 896x1152, no upscale. Lines:
`lab/x3.txt`.

## What it tests

X2 settled on Krea 2 Turbo and took K+Q forward; its open points were open hatching strokes on
fur and fine texture, lines thin enough to read grey on the detailed subjects, and an empty top
quarter on the hedgehog page. X3 asks whether a LoRA trained for coloring pages closes the
shapes and firms up the lines, and at what strength, without losing what K+Q already gets right.

| cells | arm | profile | LoRA weight |
|---|---|---|---|
| 01–04 | L06 | krea2-turbo-coloring-06 | 0.6 |
| 05–08 | L10 | krea2-turbo-coloring | 1.0 |

Both profiles are krea2-turbo plus the LoRA, with its trigger as the prefix
("s3c0m1x style coloring book, monochrome lineart illustration"); the cell text is X2's K+Q
text unchanged. A cell line can't set a LoRA weight (only prompt, negative, seed and profile),
hence two profiles.

- L06 and L10 against X2 13–16 (K+Q, same prompt, negative and seed, no LoRA): what the LoRA
  and its trigger change.
- L06 against L10: whether the stronger weight helps or overcooks.

The LoRA was trained on Krea 2 (standard/Raw), not on Turbo; if it misbehaves at 8 steps, that
is the first suspect.

## LoRA and its terms

"Krea2 Coloring Book" by sekoseko, https://civitai.com/models/2885885, version 3262188 "V1",
saved as `loras/krea2-coloring-book.safetensors` (sha256 pinned in `models.yaml`). Selling images
is allowed, but credit is required (allowNoCredit: false): any book with pages made with it must
credit sekoseko.

## Workflow change

`workflows/krea2.json` now has a LoraLoaderModelOnly ("lora 1", as in ComfyUI's Krea 2
template) between the UNET and the sampler. A profile without LoRAs drops that node and links
the UNET straight to the sampler, so krea2-turbo fills exactly the graph X2 rendered with; only
the workflow hash in the infotext changes.

## Sheet and pages

`lab/x3_sheets.py` (`uv run python -m lab.x3_sheets`) writes `D:\Stillstift\probe-3-compare.png`:
four subjects (columns) x three rows, X2 K+Q (X2 13–16, no LoRA), X3 LoRA 0.6 (01–04) and X3
LoRA 1.0 (05–08). Pages copied to `D:\Stillstift\probe-3\` as `L06|L10-<1..4>-<subject>.png`.

## Assessment

The LoRA doesn't change what K+Q draws: per seed, all three rows have the same composition. It
changes the finish, mildly at 0.6 and a bit more at 1.0, always in the coloring page's favour.
Every page stays pure black on white with no colour, grey fill or shading, and anatomy stays
right on every animal.

Measured on the full pages (share of mid-grey pixels, 60–200, and of white, > 235):

| subject | K+Q grey / white | 0.6 grey / white | 1.0 grey / white |
|---|---|---|---|
| hedgehogs | 3.1 % / 80 % | 3.5 % / 81 % | 3.8 % / 81 % |
| old town | 30.3 % / 43 % | 19.0 % / 61 % | 18.1 % / 63 % |
| turtle | 5.9 % / 81 % | 5.5 % / 83 % | 5.4 % / 83 % |
| mandala | 13.2 % / 74 % | 12.3 % / 76 % | 11.0 % / 77 % |

- **Closed shapes.** Better on the mandala at both strengths: fewer, larger petals with ornament
  lines inside, instead of K+Q's dense small petals, so more areas big enough to colour. On the
  hedgehogs, 0.6 brings back the check grid on the blanket (more small, partly open cells, as in
  X2's K); 1.0 keeps K+Q's one closed blanket and adds closed props (a cupcake held in a paw, a
  plate with a pie). The fur is still open hatching strokes at both strengths. Turtle: about the
  same as K+Q; 1.0 adds more small fish.
- **Clean B/W.** The clearest gain is the old town: the fine lines that read grey in K+Q become
  firmer, the cobbles larger and the flower boxes less fuzzy; mid-grey drops from 30 % to 18–19 %
  and white rises from 43 % to 61–63 %. Elsewhere it was already clean and stays so.
- **Line weight.** Outlines are a little bolder and more even with the LoRA, most visibly on the
  old town and the mandala, and more so at 1.0. Inner detail lines stay fine.
- **Detail.** Kept, not lost: the old town is as rich as K+Q's, the mandala trades tiny repeated
  petals for larger ornamented ones, and 1.0 adds small story props on the hedgehog page.
- **Still open.** The hedgehog page keeps its empty top quarter at both strengths (as in X2), and
  the fur stays open strokes; a few seafloor lines on the turtle still end open.

**Which strength.** 1.0. It beats plain K+Q on every subject or ties it, and edges out 0.6 on the
hedgehogs (closed blanket, props), the old town (bolder, less grey) and the mandala (larger
shapes); the turtle is a tie. Nothing looks overcooked at 1.0 on Turbo, so trained-on-Raw is not
a problem at 8 steps. Taken forward: krea2-turbo-coloring (LoRA 1.0) as the base; books using it
must credit sekoseko.
