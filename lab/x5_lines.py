"""Write X5's cell lines: `uv run python -m lab.x5_lines lab/x5.txt`.

X4's Christmas set with a distinct cast on every page: X4's style block, negative, profile and
seeds (via `lab.x4_lines.line`), only the subject sentences differ. Every character gets a
concrete description (age, hair, build, face, clothes), and no two pages share a main character
type, because Krea 2 Turbo draws one default face when a prompt only says "kids" or "people".
"""

from __future__ import annotations

import sys
from pathlib import Path

from lab.x4_lines import SEEDS, line

# (short name for page files, subject sentence), in X4's subject order.
SUBJECTS = (
    (
        "market",
        (
            "a busy Christmas market with wooden stalls selling gingerbread and ornaments, "
            "strings of lights between the roofs and a small carousel. At the front stall a "
            "stout bald stall keeper with a bushy moustache and a striped apron hands a bag of "
            "gingerbread hearts to a slim mother with a long dark plait and a wool coat, who "
            "carries a baby in a sling, while a small curly-haired girl of about five in "
            "earmuffs and a puffer jacket points at the carousel."
        ),
    ),
    (
        "gingerbread",
        (
            "a big gingerbread house decorated with candy canes, gumdrops, icing swirls and "
            "lollipops, with a candy path leading to its door. In front of it stand a very tall "
            "gingerbread man with a bow tie and icing buttons, as tall as the door, a much "
            "smaller gingerbread lady with an icing skirt and a bun whose head only reaches his "
            "shoulder, and a tiny gingerbread baby no bigger than his hand."
        ),
    ),
    (
        "reindeer",
        (
            "a big old reindeer bull with huge branching antlers and a shaggy neck mane, and a "
            "small young reindeer calf with short stubby antlers, standing in a snowy forest of "
            "fir trees with snowflakes falling, a slender fox with a bushy tail peeking out from "
            "behind a tree and a fat little snowshoe hare sitting in the snow."
        ),
    ),
    (
        "snowmen",
        (
            "a freckled teenage boy with a buzz cut and a puffer jacket building snowmen in a "
            "snowy village garden with his big shaggy sheepdog: a tall, thin snowman with a top "
            "hat and a long striped scarf, a short, round snowman with earmuffs and a tiny "
            "snowman with a bobble hat. Behind them a wooden fence hung with icicles, a garden "
            "shed, a bird house on a post, bare birch trees and snow-covered rooftops."
        ),
    ),
    (
        "workshop",
        (
            "Santa's workshop with three very different elves at a long workbench: an old elf "
            "with a long white beard and round spectacles painting a wooden horse, a plump elf "
            "with rosy round cheeks sawing a toy train, and a young, skinny elf with big pointed "
            "ears and a gap-toothed grin wrapping a present. Shelves full of teddy bears, trains "
            "and dolls, and stacks of wrapped presents around them."
        ),
    ),
    (
        "tree",
        (
            "a living room where a tall Black teenage girl with long box braids and round "
            "glasses stands on a small stepladder placing a star on top of a tall Christmas "
            "tree, while her grandmother, a small elderly lady with short curly grey hair, a "
            "cardigan and glasses on a chain, hands her an ornament from a box. Garlands, "
            "ornaments and presents under the tree."
        ),
    ),
    (
        "sledding",
        (
            "a snowy hill above a small village of houses with a church tower, bare birch trees "
            "along the slope. An East Asian girl of about ten with two pigtails and goggles "
            "pushed up on her bobble hat races down on a wooden sled, while a lanky father with "
            "a short beard and a knitted beanie pulls a small boy of about four in a puffy "
            "snowsuit up the hill on another sled."
        ),
    ),
    (
        "fireplace",
        (
            "a cozy fireplace with stockings hanging from the mantel, where a grandfather with a "
            "full white beard and reading glasses, in a knitted sweater with a reindeer pattern, "
            "dozes in a rocking chair with a book on his lap. A fluffy long-haired cat is curled "
            "up on the rug and a small dachshund in a scarf lies beside a plate of cookies, a "
            "glass of milk and wrapped gifts."
        ),
    ),
    (
        "nutcracker",
        (
            "a tall, thin nutcracker soldier with a white beard and a tall hat standing guard "
            "beside a toy castle, with a tiny toy drummer soldier at his feet whose hat only "
            "reaches the nutcracker's knee, a ballerina figure with her hair in a bun standing on "
            "the floor, a wooden rocking horse and toy drums around them."
        ),
    ),
    (
        "village",
        (
            "a snowy half-timbered village with snow on the roofs, warm lit windows, a big round "
            "full moon and falling snowflakes. A middle-aged coach driver in a fur hat and a "
            "thick scarf drives a sleigh pulled by a big, heavy draft horse with shaggy hooves "
            "down the cobbled street, while a tall young man with long straight hair under a "
            "wool cap shovels snow in front of a bakery."
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
            "a huge old polar bear wearing a knitted scarf and a small chubby penguin chick in a "
            "bobble hat wrapping presents together on the ice in front of an igloo whose entrance "
            "is an open white arch outlined with ice blocks and left white inside, with "
            "ribbons, bows, rolls of wrapping paper and a pile of gifts, snow-covered ice blocks "
            "around them, a fishing hole with a little fish, and a starry sky full of "
            "snowflakes above."
        ),
    ),
)


def lines() -> list[str]:
    """Cells 01-12 are the subjects at seed 201+n, 13-24 the same at 301+n, as in X4."""
    return [line(text, base + n) for base in SEEDS for n, (_, text) in enumerate(SUBJECTS)]


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write("usage: python -m lab.x5_lines <out file>\n")
        return 1
    out = Path(argv[0])
    written = lines()
    out.write_text("\n".join(written) + "\n", encoding="utf-8")
    sys.stdout.write(f"{len(written)} lines -> {out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
