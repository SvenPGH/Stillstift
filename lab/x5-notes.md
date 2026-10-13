# X5 — Christmas set with a distinct cast

24 pages: X4's 12 subjects x X4's seeds (cells 01–12 at 201+n, 13–24 at 301+n), profile
krea2-turbo-coloring. Rendered 2026-10-13 as a job from this branch
(`D:\Stillstift\jobs\render-set.ps1 X5 lab/x5.txt`; the first run stopped after #01 when the hub
daemon restarted, the second continued from #02). Cells 02, 06, 10, 14, 18 and 22 were then
re-rendered with `--replace` after their cast wording was changed (gingerbread, tree, village);
ComfyUI saves those as `X5_<nn>_00002_.png`, and `lab.x2_sheets.page` picks the newest file.
After every run ComfyUI was stopped and no ComfyUI python was left. All 24 cells are in the store at `D:\Stillstift\data` and match
`lab/x5.txt` (`uv run python -m lab.store_check X5 lab/x5.txt`).

## What it tests

Sven's feedback on X4: the characters look samey across pages, with the same faces, kids and
builds. X5 keeps X4's style block, negative, profile and seeds exactly; only the subject
sentences change (`lab/x5_lines.py` reuses `lab.x4_lines.line`; checked line by line, all 24
lines are identical to X4 outside the subject sentence). Each sentence names a concrete cast:
age, hair, build, face, clothing, and breeds and sizes for animals, with no main character type
on two pages. The snowmen and sledding pages say "bare birch trees" instead of fir trees,
because snowy firs were behind every tinted page in X4.

| page | cast asked for |
|---|---|
| market | bald stall keeper with a moustache; slim mother with a long plait and a baby in a sling; curly-haired girl of five in earmuffs |
| gingerbread | tall thin gingerbread man, gingerbread lady half his height with a bun, tiny gingerbread baby |
| reindeer | old reindeer bull with huge antlers, small calf, slender fox, fat snowshoe hare |
| snowmen | freckled teenage boy with a buzz cut and a shaggy sheepdog; tall, round and tiny snowmen |
| workshop | old elf with a long beard and spectacles, plump elf with round cheeks, skinny young elf with a gap-toothed grin |
| tree | tall Black teenage girl with box braids and glasses; her grandmother, small and elderly, with curly grey hair and glasses on a chain |
| sledding | East Asian girl of ten with pigtails and goggles; lanky father with a beard; boy of four in a snowsuit |
| fireplace | grandfather with a white beard, reading glasses and a reindeer sweater; long-haired cat; dachshund |
| nutcracker | tall thin nutcracker, short round drummer, ballerina with a bun |
| village | middle-aged coach driver in a fur hat with a draft horse; tall young man with long hair shovelling snow |
| mandala | unchanged (no characters) |
| polar bear | huge old bear in a scarf, chubby penguin chick in a bobble hat |

## Results

Krea 2 Turbo followed the casts closely: on every page, both seeds draw the people and animals
asked for, so the default face is gone. Every page is clean black and white (0.0–0.2 % tint, no
tinted trees anywhere; the birch wording worked), with no lettering.

- **Distinct cast, achieved:** market, tree, sledding, fireplace, workshop, snowmen and village
  each show a different main character type: a moustached stall keeper, a teenager with box
  braids and her grandmother, a girl with goggles and her father, a bearded grandfather, three
  elves of different ages, a freckled teen with a sheepdog, a coach driver in a fur hat with a
  draft horse. Ages run from a baby to grandparents.
- **Animals:** the reindeer bull and spotted calf, the long-haired cat and dachshund, the
  sheepdog and the draft horse with feathered hooves all came out as asked.
- **Partly:** the nutcracker's drummer is barely shorter than a child-sized figure, and the
  gingerbread lady stays as tall as the man despite "half his height" (only the baby is small).
  The village's coach driver came out as an older man in a fur hat, a type no other page has.
- **Flaws:** both polar bears fill the igloo door solid grey again (as 12b in X4); the market's
  plait and the curly hair are solid black fills (small areas); in sledding the father's
  posture and push bar look odd on both seeds; #05 workshop has a stray row of elf boots under
  the table; #16 snowmen has a floating stick; #21 nutcracker poses the ballerina on the
  rocking horse; both village moons are now plain discs.
- **Mandala:** text and seeds are unchanged from X4, so the pages are the same as X4's.

## Picks

| subject | pick | why |
|---|---|---|
| 01 market | #13 (301) | Fewer tiny background faces than #01, which also repeats the mother in the crowd |
| 02 gingerbread | #02 (202) | Fuller house and candy; both seeds are alike |
| 03 reindeer | #15 (303) | Spotted calf, snowfall, fox and hare all readable |
| 04 snowmen | #04 (204) | Reads clearly as a teenager; #16 has a floating stick |
| 05 workshop | #17 (305) | #05 has a stray row of boots under the table |
| 06 tree | #18 (306) | The girl reaches for the star; grandmother hands an ornament; #06 has a star in her hand and one on top |
| 07 sledding | #19 (307) | #07 puts the father's feet on the girl's sled |
| 08 fireplace | #20 (308) | Slightly fuller; both are good |
| 09 nutcracker | #09 (209) | Ballerina stands; #21 balances her on the horse |
| 10 village | #22 (310) | Cobbled street and a bakery window; #10 adds a stray passenger |
| 11 mandala | #11 (211) | Same as X4's pick |
| 12 polar bear | X4 #27 (412) | Both X5 pages have the grey igloo door |

Sheets: `D:\Stillstift\christmas-set-x5.png` (the picks) and `D:\Stillstift\christmas-x4-vs-x5.png`
(each subject's X4 pick beside its X5 pick), from `uv run python -m lab.x5_sheets`.

## Next

- **Polar bear:** say the igloo entrance is "an open white arch with ice blocks around it"; the
  scarf and bobble hat are worth keeping.
- **Gingerbread and nutcracker:** give the figures concrete height ratios ("half his height").
- **Print:** as in X4 (3x upscale, threshold, margins, credits); the solid black hair stays
  black after thresholding, which is fine as an accent but leaves less to colour.
