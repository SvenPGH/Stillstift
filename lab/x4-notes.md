# X4 — Christmas set for ages 9 to 15

24 pages, plus 4 re-renders: 12 Christmas subjects x 2 seeds (cells 01–12 at seed 201+n, 13–24
at 301+n), and cells 25–28 re-rendering two subjects with new wording (see below); profile
krea2-turbo-coloring (Krea 2 Turbo + the coloring-book LoRA at 1.0, X3's pick), 896x1152, no
upscale. Cells 01–24 rendered 2026-10-13 by Sven from a clone at `D:\Stillstift\xmas-src`,
cells 25–28 the same day as a job from this branch (`D:\Stillstift\jobs\x4-rerender.ps1`), all
into the store at `D:\Stillstift\data`. All 28 cells are in it, and each one's prompt, negative,
seed and profile (store row and PNG infotext) match `lab/x4.txt`
(`uv run python -m lab.store_check X4 lab/x4.txt`).

Lines: `lab/x4.txt`, written by `lab/x4_lines.py` (`uv run python -m lab.x4_lines lab/x4.txt`;
its first 24 lines are byte-identical to the file the set was rendered from). Every page shares one style
block and one negative, so only the subject sentence differs: a black-and-white Christmas page
for ages 9 to 15, filling the page edge to edge, moderate detail, bold closed outlines,
medium-sized areas and no tiny cells. The negative adds lettering, black sky, empty space and
tiny details to X3's.

Pages: `D:\Stillstift\probe-4\<nn><a|b>-<subject>.png` (a = seed 201+n, b = 301+n); sheet of all
24: `D:\Stillstift\probe-4-sheet.jpg`; the picks: `D:\Stillstift\christmas-set.png`
(`uv run python -m lab.x4_sheets`).

## What it tests

Whether one shared style block holds a 12-page set together: same line weight, same level of
detail, no lettering, no grey or colour, nothing empty, for an older-child audience.

## Picks

One seed per subject, picked for a clean page first and for fitting the set second.

| subject | pick | why | the other seed |
|---|---|---|---|
| 01 market | a (201) | Busy, full page, friendly faces | b: every face left blank, a crowd of faceless people |
| 02 gingerbread | a (202) | Fills the page; bold, closed candy shapes | b: fine, but more empty sky above the roof |
| 03 reindeer | b (303) | Both foxes read as whole animals | a: the right fox's body merges into the trees |
| 04 snowmen | a (204) | Clean, though young in style | b, #25, #26: grey-green fill in the fir trees |
| 05 workshop | a (205) | Coherent scene of elves making wooden toys | b: fine, a bit busier; either works |
| 06 tree | a (206) | Both kids stand on stepladders | b: the boy on the right floats in mid-air |
| 07 sledding | a (207) | Clean | b: green-tinted fir trees (2.4 % coloured pixels) |
| 08 fireplace | b (308) | Brick-lined fireplace, string of lights: more to color | a: nearly the same; emptier hearth |
| 09 nutcracker | a (209) | Whole soldiers, ballerina, drum and cart all readable | b: a soldier merges into a cart wheel |
| 10 village | a (210) | Bold half-timbered street, two-horse sleigh | b: fine, but more tiny cobble cells |
| 11 mandala | a (211) | Larger ornaments and holly, fewer tiny cells | b: denser, more small snowflake cells |
| 12 polar bear | #27 (412) | Re-render: snowflake sky, fishing hole, fills the page, no grey | 12a: too young in style; 12b: grey igloo door; #28: fish half in the hole, plainer sky |

## Outliers

- **Colour or grey:** 04b, 07b, #25 and #26 have tinted fir trees, and 12b has a solid grey
  igloo door. None of them is picked. Every other page measures 0.0 % colour.
- **Broken figures:** 01b's faceless crowd, 06b's floating boy, 03a's merged fox and 09b's
  soldier on a wheel. None is picked.
- **Style that doesn't match the set:** 04 snowmen and 12 polar bear, at both seeds. They are
  drawn for small children: a few big shapes, thick lines, little background, and an empty band
  over the top 10–11 % of the page. Next to the market, the workshop and the village they look
  like they came from another book. The re-renders fix the polar bear; the snowmen pick (04a)
  still has this problem.
- **Empty areas:** 07 sledding (pick) has a plain sky over the top 10 %; 02 and 12 have smaller
  bands. Everything else reaches the top edge.
- **Lettering, solid black, tiny cells:** no lettering anywhere. Solid black stays limited to
  eyes, buttons and noses. The densest picks (01 market, 05 workshop, 11 mandala) have small
  cells, but none is too small to color for this age.

## Re-renders (cells 25–28)

Two subjects failed on style. They were re-rendered with the same style block and negative,
two seeds each, as cells 25–28:

- **04 snowmen:** "a snowman family of three building a fourth snowman in a snowy village
  garden, with a wooden fence hung with icicles, a garden shed, a bird house on a post, fir trees
  and a wooden sled leaning on the fence, and snow-covered rooftops behind them." Seeds 404, 504.
- **12 polar bear:** "a polar bear and a penguin wrapping presents together on the ice in front
  of an igloo, with ribbons, bows, rolls of wrapping paper and a pile of gifts, snow-covered ice
  blocks around them, a fishing hole with a little fish, and a starry sky full of snowflakes
  above." Seeds 412, 512.

Results:

- **Polar bear works.** #27 (412) and #28 (512) both fill the page with snowflakes, ice blocks
  and the fishing hole, and are clean (0.0 % tint, 3.6–3.9 % grey, empty top 2.6–4.1 % instead
  of 11.3 %). #27 replaces 12a in the picks.
- **Snowmen don't, yet.** #25 (404) and #26 (504) have exactly the older, fuller scene asked for
  (shed with icicles, bird house, sleds, rooftops), but the fir trees are filled grey-green on
  both: a quarter of the tree area is mid-grey, against 3.6 % on 04a. Thresholding for print
  would turn that into blotches, so 04a stays the pick. Snow-covered fir trees are the common
  factor of every tinted page in this set (04b, 07b, #25, #26); X5 words them as bare birch
  trees on the snowmen and sledding pages.

## For the print version

- **Size:** at 896x1152 a page prints at about 105 dpi on 8.5x11 in; it needs about 2550x3300
  for 300 dpi. Upscale 3x, e.g. with the RealESRGAN anime model already in `models.yaml`.
- **Pure black and white:** threshold every page after upscaling, which removes anti-aliasing
  grey and any leftover tint. Then check that the thinnest lines still print.
- **Margins:** the prompts ask for scenes reaching all four edges. Either set the interior up
  with bleed, or scale each page into the safe area with a white margin. Print one page per sheet
  with blank backs, so markers don't bleed through.
- **Credits:** credit sekoseko (the LoRA's terms), disclose AI generation where KDP asks, and
  stay within the Krea 2 license's under-$1M condition.
