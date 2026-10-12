import { draftOf, isRated } from "./rating.js";

/** @typedef {import("./rating.js").CellView} CellView */
/** @typedef {import("./rating.js").Draft} Draft */
/** @typedef {"torate" | "all"} Scope */
/** @typedef {Record<string, Draft>} Drafts */
/** @typedef {"current" | "draft" | "rated" | "open"} SegmentTone */

/**
 * The cells ‹ and › step through: every cell, or the unrated ones plus the one open.
 * @param {CellView[]} cells
 * @param {number} cur
 * @param {Scope} scope
 * @returns {number[]}
 */
export function stepList(cells, cur, scope) {
  return cells.flatMap((cell, at) =>
    scope === "all" || !isRated(cell) || at === cur ? [at] : [],
  );
}

/**
 * The cell a step lands on, or -1 when there is none that way.
 * @param {number[]} list
 * @param {number} cur
 * @param {-1 | 1} delta
 * @returns {number}
 */
export function neighbour(list, cur, delta) {
  if (delta > 0) return list.find((at) => at > cur) ?? -1;
  return list.filter((at) => at < cur).at(-1) ?? -1;
}

/**
 * Where the open cell sits: `#03 · 1 of 5 to rate`, `#05 · rated · 4 to rate` or `#03 · 3 of 8`.
 * @param {CellView[]} cells
 * @param {number} cur
 * @param {Scope} scope
 * @returns {string}
 */
export function positionText(cells, cur, scope) {
  const cell = cells[cur];
  if (cell === undefined) return "";
  if (scope === "all")
    return `${cell.cell_id} · ${String(cur + 1)} of ${String(cells.length)}`;
  const list = stepList(cells, cur, scope);
  if (isRated(cell))
    return `${cell.cell_id} · rated · ${String(list.length - 1)} to rate`;
  return `${cell.cell_id} · ${String(list.indexOf(cur) + 1)} of ${String(list.length)} to rate`;
}

/**
 * The key a cell's draft is kept under.
 * @param {string} entry
 * @param {string} cellId
 * @returns {string}
 */
export function draftKey(entry, cellId) {
  return `${entry}:${cellId}`;
}

/**
 * @param {Record<string, number | null>} rows
 * @returns {string}
 */
function setRows(rows) {
  return JSON.stringify(
    Object.entries(rows)
      .filter(([, stars]) => stars !== null)
      .sort(([a], [b]) => a.localeCompare(b)),
  );
}

/**
 * Whether two drafts hold the same rating, whatever the order of their rows and flaws.
 * @param {Draft} a
 * @param {Draft} b
 * @returns {boolean}
 */
export function sameDraft(a, b) {
  return (
    a.taste === b.taste &&
    a.render === b.render &&
    a.reason === b.reason &&
    a.on_target === b.on_target &&
    a.flags.book === b.flags.book &&
    [...a.flaws].sort().join("|") === [...b.flaws].sort().join("|") &&
    setRows(a.rows) === setRows(b.rows)
  );
}

/**
 * Leaving a cell: keep its draft when it differs from the rating it opened with, else drop it.
 * @param {Drafts} drafts
 * @param {string} key
 * @param {Draft} draft
 * @param {CellView} cell
 * @returns {Drafts}
 */
export function keptDrafts(drafts, key, draft, cell) {
  const others = Object.fromEntries(
    Object.entries(drafts).filter(([kept]) => kept !== key),
  );
  return sameDraft(draft, draftOf(cell.rating))
    ? others
    : { ...others, [key]: draft };
}

/**
 * The draft a cell opens with: the one kept for it, else its rating, else blank.
 * @param {Drafts} drafts
 * @param {string} key
 * @param {CellView} cell
 * @returns {Draft}
 */
export function openingDraft(drafts, key, cell) {
  return drafts[key] ?? draftOf(cell.rating);
}

/**
 * How many of the set's other cells hold a kept draft.
 * @param {Drafts} drafts
 * @param {string} entry
 * @param {CellView[]} cells
 * @param {number} cur
 * @returns {number}
 */
export function draftCount(drafts, entry, cells, cur) {
  return cells.filter(
    (cell, at) => at !== cur && draftKey(entry, cell.cell_id) in drafts,
  ).length;
}

/**
 * A progress segment's tone and title: `#03`, plus ` · rated` and ` · draft` as they hold.
 * @param {CellView} cell
 * @param {{ open: boolean, drafted: boolean }} at
 * @returns {{ tone: SegmentTone, title: string }}
 */
export function segment(cell, { open, drafted }) {
  const rated = isRated(cell);
  const title = `${cell.cell_id}${rated ? " · rated" : ""}${drafted ? " · draft" : ""}`;
  if (open) return { tone: "current", title };
  if (drafted) return { tone: "draft", title };
  return { tone: rated ? "rated" : "open", title };
}
