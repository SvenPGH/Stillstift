/** @typedef {import("./rating.js").Rating} Rating */
/** @typedef {import("./rating.js").EntrySummary} EntrySummary */
/** @typedef {import("./kinds.js").Kind} Kind */
/** @typedef {"fav" | "keep" | "issue" | "kill"} Verdict */
/**
 * A rendered page as GET /api/cells lists it.
 * @typedef {{
 *   entry: string,
 *   kind: Kind | null,
 *   cell_id: string,
 *   image: string,
 *   thumb: string,
 *   download: string,
 *   rendered_at: string,
 *   rating: Rating | null,
 *   verdict: Verdict | null,
 *   prediction: Verdict | null,
 *   favorite: boolean,
 * }} CellRow
 */
/** @typedef {"P" | "X" | "T" | "all"} KindFilter */
/** @typedef {"all" | "yes" | "candidate"} BookFilter */
/** @typedef {Verdict | "all" | "unrated"} VerdictFilter */
/** @typedef {"newest" | "liked_desc" | "liked_asc" | "render_desc"} Sort */
/**
 * @typedef {{
 *   kind: KindFilter,
 *   set: string,
 *   book: BookFilter,
 *   verdict: VerdictFilter,
 *   flaw: string,
 *   sort: Sort,
 *   grouped: boolean,
 * }} Filters
 */
/** @typedef {{ entry: string, title: string, meta: string, cells: CellRow[] }} Group */
/** @typedef {Verdict | "lab" | "unrated"} Tone */

/** @type {Partial<Record<Kind, string>>} */
const LAB_ROW = { X: "— experiment", T: "— test" };

/** @type {Filters} */
export const DEFAULTS = {
  kind: "P",
  set: "all",
  book: "all",
  verdict: "all",
  flaw: "any",
  sort: "newest",
  grouped: true,
};

/** @type {Record<Exclude<Sort, "newest">, (a: CellRow, b: CellRow) => number>} */
const ORDER = {
  liked_desc: (a, b) => (b.rating?.taste ?? -1) - (a.rating?.taste ?? -1),
  liked_asc: (a, b) => (a.rating?.taste ?? 9) - (b.rating?.taste ?? 9),
  render_desc: (a, b) => (b.rating?.render ?? -1) - (a.rating?.render ?? -1),
};

/**
 * The filters a page opened at `#<set>` starts with: that set, under its kind.
 * @param {string} asked
 * @param {EntrySummary[]} entries
 * @returns {Filters}
 */
export function filtersFor(asked, entries) {
  const kind = entries.find((e) => e.entry === asked)?.kind;
  if (kind === undefined || kind === null) return DEFAULTS;
  return { ...DEFAULTS, kind, set: asked };
}

/**
 * Whether any filter or the sort is off its default; the layout does not count.
 * @param {Filters} filters
 * @returns {boolean}
 */
export function isFiltered(filters) {
  return (
    filters.kind !== DEFAULTS.kind ||
    filters.set !== DEFAULTS.set ||
    filters.book !== DEFAULTS.book ||
    filters.verdict !== DEFAULTS.verdict ||
    filters.flaw !== DEFAULTS.flaw ||
    filters.sort !== DEFAULTS.sort
  );
}

/**
 * Whether a cell has been judged, by a rating or a verdict.
 * @param {CellRow} cell
 * @returns {boolean}
 */
function judged(cell) {
  return cell.rating !== null || cell.verdict !== null;
}

/**
 * @param {CellRow} cell
 * @param {VerdictFilter} verdict
 * @returns {boolean}
 */
function verdictPasses(cell, verdict) {
  if (verdict === "all") return true;
  if (verdict === "unrated") return !judged(cell);
  return cell.verdict === verdict;
}

/**
 * @param {CellRow} cell
 * @param {string} flaw "any", "none" or a flaw
 * @returns {boolean}
 */
function flawPasses(cell, flaw) {
  const flaws = cell.rating?.flaws ?? [];
  if (flaw === "any") return true;
  if (flaw === "none") return judged(cell) && flaws.length === 0;
  return flaws.includes(flaw);
}

/**
 * The pages the filters leave, in the sort's order; newest keeps the server's order.
 * @param {CellRow[]} cells
 * @param {Filters} filters
 * @returns {CellRow[]}
 */
export function shownCells(cells, filters) {
  const shown = cells.filter(
    (c) =>
      (filters.kind === "all" || c.kind === filters.kind) &&
      (filters.set === "all" || c.entry === filters.set) &&
      (filters.book === "all" || c.rating?.flags.book === filters.book) &&
      verdictPasses(c, filters.verdict) &&
      flawPasses(c, filters.flaw),
  );
  if (filters.sort === "newest") return shown;
  return [...shown].sort(ORDER[filters.sort]);
}

/**
 * One section per set, headed by its id and name, while grouped and sorted newest first;
 * otherwise one plain grid.
 * @param {CellRow[]} shown
 * @param {CellRow[]} cells every page, for each set's rated count
 * @param {EntrySummary[]} entries
 * @param {Filters} filters
 * @returns {Group[]}
 */
export function groupsOf(shown, cells, entries, filters) {
  if (shown.length === 0) return [];
  if (!filters.grouped || filters.sort !== "newest")
    return [{ entry: "", title: "", meta: "", cells: shown }];
  const sets = [...new Set(shown.map((c) => c.entry))];
  return sets.map((entry) => {
    const summary = entries.find((e) => e.entry === entry);
    const own = cells.filter((c) => c.entry === entry);
    const mine = shown.filter((c) => c.entry === entry);
    const rated = own.filter(judged).length;
    const date = summary?.date ?? "";
    return {
      entry,
      title: summary?.name ?? "",
      meta: `${date} · ${String(mine.length)} shown · ${String(rated)} / ${String(own.length)} rated`,
      cells: mine,
    };
  });
}

/**
 * The verdict a tile shows on its right: the mapped verdict, a lab set's kind once rated,
 * else unrated.
 * @param {CellRow} cell
 * @returns {{ text: string, tone: Tone }}
 */
export function verdictLabel(cell) {
  if (cell.verdict !== null) return { text: cell.verdict, tone: cell.verdict };
  if (cell.kind !== "P" && cell.rating !== null)
    return { text: cell.kind ?? "", tone: "lab" };
  return { text: "unrated", tone: "unrated" };
}

/**
 * The viewer's rows: Render, Verdict and Predicted (shown only once the cell is rated).
 * @param {CellRow} cell
 * @returns {[string, string][]}
 */
export function viewerRows(cell) {
  const lab = LAB_ROW[cell.kind ?? "X"] ?? "— experiment";
  const unjudged = cell.kind === "P" ? "unrated" : lab;
  return [
    ["Render", String(cell.rating?.render ?? "—")],
    ["Verdict", cell.verdict ?? unjudged],
    ["Predicted", cell.prediction ?? "—"],
  ];
}

/**
 * The Set menu's choices: every set of the chosen kind, by id and name.
 * @param {EntrySummary[]} entries
 * @param {KindFilter} kind
 * @returns {[string, string][]}
 */
export function setChoices(entries, kind) {
  const sets = entries.filter((e) => kind === "all" || e.kind === kind);
  return [
    ["all", "All sets"],
    ...sets.map(
      (e) =>
        /** @type {[string, string]} */ ([
          e.entry,
          e.name === "" ? e.entry : `${e.entry} · ${e.name}`,
        ]),
    ),
  ];
}

/**
 * The header's count: page-set images, and those in experiments and tests.
 * @param {CellRow[]} cells
 * @returns {string}
 */
export function totalText(cells) {
  const pages = cells.filter((c) => c.kind === "P").length;
  return `${String(pages)} pages · ${String(cells.length - pages)} in experiments`;
}
