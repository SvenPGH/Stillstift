# X1 — First style probe: 3 profiles x 4 subjects

12 pages, 3 profiles (A sdxl-redmond, B sdxl-ax, C flux-coloring) x 4 subjects (hedgehog family
picnic, old town street, sea turtle, floral mandala), same seed per subject across profiles
(101/102/103/104). Lines: `lab/x1.txt`. Sheet: `data/sheets/X1.png`, copied to
`D:\Stillstift\probe-1-sheet.png`; full pages copied to `D:\Stillstift\probe-1\` as
`A/B/C-<subject>-<name>.png`. All renders at 896x1152, no upscale pass yet. Every raw ComfyUI PNG
(`X1_01..12_00001_.png`) carries zero text chunks (`--disable-metadata` confirmed); the curator
copies (`data/renders/X1/#01..12.png`) carry only our own `parameters` infotext, as intended.

## Time per page

SDXL (A and B, steps 30, dpmpp_2m/karras): ~16s/page once the checkpoint is loaded — A and B cost
the same since only the LoRA differs. FLUX (C, steps 28, deis/beta): ~100s for the first page
(checkpoint swap from SDXL's 6.9 GB to FLUX's fp8 ~12 GB) then ~60s/page — except #11 (C-3,
turtle), which took ~14 minutes and came out the most degraded of the set; that stall lines up
with the worst output, which smells like VRAM strain on the 4060 Ti rather than a clean render.

## Per-profile assessment

**A — sdxl-redmond (ColoringBookRedmond-V2 @ 0.9).** Clean, closed outlines throughout, no grey
fill, no stray shading; solid black stays confined to small accents (pupils, nose, mushroom
spots) the way a coloring page wants. Detail scales sensibly with the subject — simple and
bold for the hedgehogs, properly intricate for the mandala and town street. The most consistent
and most straightforwardly colorable of the three; closest to "ready to print" as-is.

**B — sdxl-ax (ax-adult-coloring @ 0.9).** The most detailed and the one Sven called out as
clearly the most interesting ("way more going on") — #05 (hedgehogs) and #06 (old town) pack in
noticeably more scene and texture than A's versions of the same subjects. But the quality is
rougher: #05 has a muddled extra hand/paw on the hedgehog passing food, #07 (turtle) renders the
shell as dense solid-black triangular facets that read as part-shaded rather than outline-only,
and the fine fur/petal texture on #05 and #08 borders on cross-hatching that will be fiddly to
color cleanly. Overall: best "going on," worst finish — half-drawn lines, an extra hand, and
patches of muddiness keep it from being print-ready.

**C — flux-coloring (coloringbookflux @ 1.0).** Inconsistent in a way the other two aren't: #10
(old town) and #12 (mandala) fill the page and look good, close to A's quality. But #09
(hedgehogs) and #11 (turtle) are confirmed near-blank by eye — a small, perfectly clean line
drawing floating in the middle of an otherwise empty page, wasting most of the 896x1152 canvas.
File sizes back this up (mostly-white PNGs compress hard): 296 KB / 995 KB / 144 KB / 628 KB for
#09–#12, against ~1.7–2.1 MB for every A and B page. This is the same failure mode flagged before
testing started; it clearly still happens, and happens selectively (character/creature subjects,
not architecture/pattern subjects) at these settings (cfg 1.0, guidance 3.5).

## Verdict and next steps

Sven's call after looking at the pages himself: B is clearly the most interesting of the three,
but current quality is still too rough to ship (half-drawn lines, the extra hand, muddiness).
Take the Ax LoRA forward, not sdxl-ax as rendered here.

Next probe: the Ax LoRA against 2-3 other commercially-licensed SDXL fine-tune checkpoints (not
just sd_xl_base_1.0), plus a black & white / vector cleanup pass on the output, same 4 subjects
and the same seeds (101/102/103/104) for a fair comparison. If FLUX is tried again, the near-blank
failure on character subjects needs a prompt or settings fix first — it is not yet a usable arm.
