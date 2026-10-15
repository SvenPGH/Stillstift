# X24 — Advent in der Winterstraße: style probe

The look probe for the Advent-calendar book (adults and children from 8, bold-and-easy, 24 days in
one snowy half-timbered street). Six days × two line weights on one seed per day
(`lab/x24_lines.py`, `lab/x24.txt`, seeds 24001–24006), krea2-turbo-coloring (LoRA 1.0), 896x1152,
which is exactly the 8.75x11.25 in bleed aspect. Rendered 2026-10-15 to the hosted curator for
Sven alone. #13 and #14 are framed mocks (`lab/x24_mocks.py`, `just frame`). Contact sheet:
`D:\Stillstift\set-X24.png`. Full-size pages and mocks are in `D:\Stillstift\X24\`.

Odd cells are bold, even cells finer. A pixel count found no colour anywhere except #12 (yellow
candle flames, 0.08 % of the page). No letters or digits crept in on any page; the stall boards
stayed blank.

| day | bold | finer | note |
|---|---|---|---|
| 2 wreath | #01 good | #02 good | #01 has five candles, #02 four; every candle burns on both (asked for one). Clean, big shapes. #02's table grain is faint and thin |
| 6 boots | #03 good | #04 good | Boots on the doorstep, heart, oranges, nuts, presents; no chocolate coins. #04's doormat carries little dash marks that read like scribbled letters |
| 11 smoker | #05 kill | #06 kill | Not a Räuchermännchen: a live, bearded hiker with a pipe, face large and front-on, beside a vase that the smoke rises from; on #06 his pipe runs into the vase like a hookah |
| 8 market | #07 good | #08 good | Strongest scene: stalls, carousel, tree, small figures from behind. #07 isn't much bolder than #08; #08 is thin and busy |
| 16 pond | #09 good | #10 good | Reads more like a frozen stream than a pond; the sledge is pulled from behind. Skaters small, from behind |
| 24 eve | #11 issue | #12 issue | White sky with outlined stars and the big star held, lit windows with candles and trees. #11's square tree has grey-green filled branches; #12's flames are yellow (thresholded out in the mock) |

## Line weights

The weight sentence works on close-ups (#01/#03/#05 are clearly heavier than their pairs) but
barely on wide scenes: the market, pond and street come out medium-thin in both, since many small
houses shrink every line. The finer variants carry a little more mid-grey relative to ink (anti-
aliasing of thin lines), so they print lighter.

## Frame

`stillstift/frame.py`: a double rounded border, a day tag with two stars, 8.5x11 in at 300 dpi
without bleed, border 0.5 in from the outer edges and 0.625 in from the gutter side (KDP asks for
0.375 in inside and 0.25 in outside). The number is set in Fredoka SemiBold (SIL Open Font
License, `stillstift/fonts/OFL.txt`). The art covers the frame's inside, so a page loses about 5 %
at the sides. The mocks only Lanczos-scale and threshold; the print run puts the RealESRGAN 4x
upscale in front.

## For the full 24

- Räuchermännchen: describe the object, not a man: a turned wooden toy figure with a cylinder
  body, a painted simple face, a round wooden base, smoke rising from his little round mouth;
  probably as a smaller element on a windowsill scene.
- Wide scenes need a heavier weight sentence or fewer, larger houses ("three or four big houses")
  to really be bold-and-easy.
- Number words win over counts only partly: name the exact number again ("exactly four candles,
  only one of them lit, the other three unlit with no flame").
- Trees: "every branch left white inside"; candle flames: "outlined flame left white".
- Thresholding fixes faint grey and stray colour, but a filled area would go solid black, so
  check every page before framing.
