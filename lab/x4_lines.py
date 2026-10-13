"""Write X4's cell lines: `uv run python -m lab.x4_lines lab/x4.txt`.

The Christmas set for ages 9 to 15: 12 subjects x seeds 201+n and 301+n, every page in one shared
style block and one negative, so the set looks like one book.
"""

from __future__ import annotations

import sys
from pathlib import Path

STYLE = (
    "A black-and-white Christmas coloring book page for children aged 9 to 15: {subject} "
    "The scene fills the whole page from edge to edge, with background details reaching all "
    "four sides and no large empty areas. It is drawn with moderate detail in clean, bold black "
    "outlines on a plain white background, with medium-sized areas that are easy to color and "
    "no tiny cells. Every shape is a closed black outline left white inside for coloring in, "
    "with no shading, no grey tones, no solid black areas and no color. It is a professionally "
    "drawn, print-ready coloring page with crisp, unbroken, even-weight lines and closed shapes."
)

NEGATIVE = (
    "color, colour, grayscale, greyscale, gray, grey, shading, shadows, solid black fill, black "
    "sky, cross-hatching, sketchy messy lines, blurry, noisy background, text, lettering, letters, "
    "words, watermark, signature, photo, realistic, 3d render, low quality, bad anatomy, extra "
    "hands, extra fingers, extra limbs, deformed, mutated, broken lines, unfinished lines, "
    "smudged, muddy, jpeg artifacts, worst quality, empty space, tiny details"
)

# (short name for page files, subject sentence), in cell order.
SUBJECTS = (
    (
        "market",
        (
            "a busy Christmas market with wooden stalls selling gingerbread and ornaments, "
            "strings of lights between the roofs, a small carousel and people in winter coats "
            "and scarves."
        ),
    ),
    (
        "gingerbread",
        (
            "a big gingerbread house decorated with candy canes, gumdrops, icing swirls and "
            "lollipops, with a candy path leading to its door and gingerbread figures in front "
            "of it."
        ),
    ),
    (
        "reindeer",
        (
            "two reindeer standing in a snowy forest of fir trees, with snowflakes falling, a fox "
            "peeking out from behind a tree and a rabbit in the snow."
        ),
    ),
    (
        "snowmen",
        (
            "a cheerful snowman family of three in scarves and hats, building a little snowman "
            "together in a snowy garden with a wooden fence and fir trees behind them."
        ),
    ),
    (
        "workshop",
        (
            "Santa's workshop, with busy elves building and painting wooden toys at a long "
            "workbench, shelves full of teddy bears, trains and dolls, and stacks of wrapped "
            "presents."
        ),
    ),
    (
        "tree",
        (
            "two kids decorating a tall Christmas tree in a living room, one on a small stepladder "
            "placing a star on top, with ornaments, garlands and presents under the tree."
        ),
    ),
    (
        "sledding",
        (
            "kids sledding down a snowy hill on wooden sleds, with a small village of houses and a "
            "church tower in the valley below and fir trees along the slope."
        ),
    ),
    (
        "fireplace",
        (
            "a cozy fireplace with stockings hanging from the mantel, a cat curled up on a rug in "
            "front of it, wrapped gifts, a rocking chair and a plate of cookies with a glass of "
            "milk."
        ),
    ),
    (
        "nutcracker",
        (
            "a tall nutcracker soldier standing guard beside a toy castle, surrounded by toy "
            "drums, wooden horses, tin soldiers and a little ballerina figure."
        ),
    ),
    (
        "village",
        (
            "a snowy half-timbered village with snow on the roofs, warm lit windows, a big round "
            "full moon, falling snowflakes and a horse-drawn sleigh on the cobbled street."
        ),
    ),
    (
        "mandala",
        (
            "a large symmetrical mandala made of Christmas ornaments, holly leaves, candy canes, "
            "stars and snowflakes arranged in radial symmetry, centered on the page."
        ),
    ),
    (
        "polarbear",
        (
            "a polar bear and a penguin wrapping presents together on the ice, with ribbons, bows, "
            "rolls of wrapping paper and a pile of gifts, and an igloo behind them."
        ),
    ),
)

SEEDS = (201, 301)
PROFILE = "krea2-turbo-coloring"

# Cells 25-28: the two subjects first drawn too young for the set, reworded with more background,
# each at two new seeds. (short name, subject sentence, seeds), in cell order.
RERENDERS = (
    (
        "snowmen",
        (
            "a snowman family of three building a fourth snowman in a snowy village garden, with "
            "a wooden fence hung with icicles, a garden shed, a bird house on a post, fir trees "
            "and a wooden sled leaning on the fence, and snow-covered rooftops behind them."
        ),
        (404, 504),
    ),
    (
        "polarbear",
        (
            "a polar bear and a penguin wrapping presents together on the ice in front of an "
            "igloo, with ribbons, bows, rolls of wrapping paper and a pile of gifts, snow-covered "
            "ice blocks around them, a fishing hole with a little fish, and a starry sky full of "
            "snowflakes above."
        ),
        (412, 512),
    ),
)


def line(subject: str, seed: int) -> str:
    prompt = STYLE.format(subject=subject)
    if '"' in prompt + NEGATIVE:
        msg = "a cell line's text cannot hold a double quote"
        raise ValueError(msg)
    return f'--prompt "{prompt}" --negative_prompt "{NEGATIVE}" --seed {seed} --profile {PROFILE}'


def lines() -> list[str]:
    """Cells 01-12 are the subjects at seed 201+n, 13-24 the same at 301+n, 25-28 RERENDERS."""
    first = [line(text, base + n) for base in SEEDS for n, (_, text) in enumerate(SUBJECTS)]
    return first + [line(text, seed) for _, text, seeds in RERENDERS for seed in seeds]


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write("usage: python -m lab.x4_lines <out file>\n")
        return 1
    out = Path(argv[0])
    written = lines()
    out.write_text("\n".join(written) + "\n", encoding="utf-8")
    sys.stdout.write(f"{len(written)} lines -> {out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
