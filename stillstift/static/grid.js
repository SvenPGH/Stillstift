/** @typedef {import("./rating.js").CellView} CellView */
/**
 * @typedef {{
 *   cellId: string,
 *   image: string,
 *   thumb: string,
 *   download: string,
 *   stars: number,
 *   flaws: string[],
 * }} Tile
 */

/**
 * The grid of a finished entry: one tile per rendered cell, in the server's order.
 * @param {CellView[]} cells from GET /api/entries/{entry}/cells
 * @returns {Tile[]}
 */
export function tiles(cells) {
  return cells.map((c) => ({
    cellId: c.cell_id,
    image: c.image,
    thumb: c.thumb,
    download: c.download,
    stars: c.rating?.taste ?? 0,
    flaws: c.rating?.flaws ?? [],
  }));
}

/**
 * One step through the lightbox's images, stopping at both ends.
 * @param {number} index
 * @param {number} delta
 * @param {number} count
 * @returns {number}
 */
export function stepIndex(index, delta, count) {
  return Math.min(Math.max(index + delta, 0), count - 1);
}
