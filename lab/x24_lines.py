"""Write X24's cell lines: `uv run python -m lab.x24_lines lab/x24.txt`.

The style probe for "Advent in der Winterstraße", an Advent-calendar coloring book for adults and
children from 8: six of its 24 days, each in two line weights (bold-and-easy, then a little finer)
on the same seed, so the pair differs only in the weight sentence. Every page sits in the same
snowy half-timbered old-town street; people stay small, seen from behind or far off, and the art
carries no text or digits because the day number goes into a frame laid over it afterwards.
"""

from __future__ import annotations

import sys
from pathlib import Path

STYLE = (
    "A black-and-white Advent coloring book page for adults and children from 8, set in a snowy "
    "German old-town street of half-timbered houses: {subject} {weight} Every shape is a closed "
    "black outline left white inside for coloring in, with no shading, no grey tones, no solid "
    "black areas and no color. Any people are small and seen from behind or from a distance. "
    "There is no text, no letters and no numbers anywhere in the picture. It is a professionally "
    "drawn, print-ready coloring page with crisp, unbroken, even-weight lines and closed shapes."
)

WEIGHTS = (
    (
        "bold",
        (
            "It is drawn in a bold and easy style: thick, clean black outlines, big simple closed "
            "shapes and moderate detail, with large areas that are easy to color and no tiny "
            "cells. The scene fills the page, with no large empty areas."
        ),
    ),
    (
        "fine",
        (
            "It is drawn with clean, medium-weight black outlines, a little finer than a bold "
            "style, with closed shapes and a little more detail, with medium-sized areas that are "
            "easy to color and no tiny cells. The scene fills the page, with no large empty areas."
        ),
    ),
)

NEGATIVE = (
    "color, colour, grayscale, greyscale, gray, grey, shading, shadows, solid black fill, black "
    "sky, night sky filled black, cross-hatching, sketchy messy lines, blurry, noisy background, "
    "text, lettering, letters, words, numbers, digits, signs with writing, watermark, signature, "
    "photo, realistic, 3d render, low quality, close-up face, portrait, bad anatomy, extra hands, "
    "extra fingers, extra limbs, deformed, mutated, broken lines, unfinished lines, smudged, "
    "muddy, jpeg artifacts, worst quality, empty space, tiny details"
)

# (day, short name, subject sentence), in cell order; each subject keeps one seed for both weights.
SUBJECTS = (
    (
        2,
        "wreath",
        (
            "a close-up of an Advent wreath of fir branches on a wooden table by a window, with "
            "four thick candles, only the first one burning with a simple teardrop flame, pine "
            "cones, ribbon bows and a plate of star-shaped cookies; through the small-paned "
            "window the snowy half-timbered houses across the street."
        ),
    ),
    (
        6,
        "boots",
        (
            "a close-up of a pair of children's winter boots standing by an old wooden front door "
            "on Nikolaus morning, filled to the brim with oranges, walnuts, plain round chocolate "
            "coins, a gingerbread heart decorated with icing swirls and a small wrapped present "
            "with a bow; a doormat, a wooden floor and a little window showing falling snow."
        ),
    ),
    (
        11,
        "smoker",
        (
            "a close-up of a traditional carved wooden Erzgebirge incense smoker figurine, a "
            "plump forester with a wide hat, a long coat and a long pipe, standing on a "
            "windowsill, with a gentle curl of smoke drawn as outlined swirls rising from his "
            "mouth; beside him a small wooden fir tree and a pine cone, and through the window "
            "snowy roofs and chimneys."
        ),
    ),
    (
        8,
        "market",
        (
            "a wide view of the street where the Christmas market opens: wooden stalls with snowy "
            "roofs, fir garlands and strings of lanterns, a small carousel and a big decorated fir "
            "tree in the little square, the half-timbered houses with steep snowy roofs behind; "
            "small figures in winter coats, seen from behind, stroll between the stalls. The "
            "stall boards are blank, without any writing."
        ),
    ),
    (
        16,
        "pond",
        (
            "a wide view of a frozen pond at the end of the street, with half-timbered houses and "
            "a church tower behind it; small skaters seen from a distance and from behind, a "
            "child pulling another on a wooden sledge, two skaters holding hands; snow-laden "
            "willows and a wooden bench on the bank, a white sky with snowflakes drawn as "
            "outlined stars."
        ),
    ),
    (
        24,
        "eve",
        (
            "the street on Christmas Eve at night, every window lit and drawn as white panes with "
            "candle arches and little Christmas trees inside, a decorated fir tree in the small "
            "square, an old lantern post, snow on the roofs and footprints in the snow, and one "
            "big bright star above the roofs drawn with outlined rays; the night sky is left "
            "white with a few small outlined stars, not black."
        ),
    ),
)

SEEDS = tuple(24001 + n for n in range(len(SUBJECTS)))
PROFILE = "krea2-turbo-coloring"


def line(subject: str, weight: str, seed: int) -> str:
    prompt = STYLE.format(subject=subject, weight=weight)
    return f'--prompt "{prompt}" --negative_prompt "{NEGATIVE}" --seed {seed} --profile {PROFILE}'


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write("usage: python -m lab.x24_lines <out.txt>\n")
        return 1
    lines = [
        line(subject, weight, seed)
        for (_, _, subject), seed in zip(SUBJECTS, SEEDS, strict=True)
        for _, weight in WEIGHTS
    ]
    Path(argv[0]).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
