import { el } from "./dom.js";

/**
 * A set's section on an overview page: its id and name over its tiles; no heading when the
 * page is laid out flat (entry "").
 * @param {{ entry: string, title: string, meta: string }} group
 * @param {HTMLElement[]} tiles
 * @param {string} [grid] the grid's class: the plain tile grid by default
 * @returns {HTMLElement}
 */
export function overviewSection(group, tiles, grid = "tiles") {
  const section = el("section", "overview-group");
  if (group.entry !== "") {
    const head = el("div", "overview-head");
    const title = el("h2", "");
    title.append(el("span", "mono", group.entry));
    if (group.title !== "") title.append(` · ${group.title}`);
    head.append(title, el("span", "mono", group.meta));
    section.append(head);
  }
  const box = el("div", grid);
  box.append(...tiles);
  section.append(box);
  return section;
}

/**
 * A tile's Liked stars, filled up to the rating.
 * @param {number | null} taste
 * @returns {HTMLElement}
 */
export function tileStars(taste) {
  const n = taste ?? 0;
  const stars = el("span", "tile-stars");
  stars.append(el("span", "on", "★".repeat(n)), "☆".repeat(5 - n));
  return stars;
}
