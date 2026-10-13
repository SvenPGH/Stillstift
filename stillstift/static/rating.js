/** @typedef {"yes" | "candidate" | "no"} Flag */
/** @typedef {"yes" | "partly" | "no"} OnTarget */
/**
 * A rating as the API returns it.
 * @typedef {{
 *   taste: number,
 *   rows: Record<string, number>,
 *   render: number | null,
 *   flaws: string[],
 *   flags: { book: Flag | null },
 *   on_target: OnTarget | null,
 *   reason: string,
 * }} Rating
 */
/**
 * @typedef {{
 *   taste: number | null,
 *   rows: Record<string, number | null>,
 *   render: number | null,
 *   flaws: string[],
 *   flags: { book: Flag | null },
 *   on_target: OnTarget | null,
 *   reason: string,
 * }} Draft
 */
/** @typedef {{ rater: string, taste: number, verdict: string }} OtherRating */
/**
 * @typedef {{
 *   cell_id: string,
 *   image: string,
 *   thumb: string,
 *   preview: string,
 *   download: string,
 *   prompt: string,
 *   negative: string,
 *   settings: [string, string][],
 *   intent: string,
 *   tags: string[],
 *   verdict: string | null,
 *   rating: Rating | null,
 *   favorite: boolean,
 *   others: OtherRating[],
 *   prediction: number | null,
 * }} CellView
 */
/**
 * @typedef {{
 *   entry: string,
 *   kind: import("./kinds.js").Kind | null,
 *   name: string,
 *   date: string,
 *   tests: string,
 *   rendered: number,
 *   unrated: number,
 *   cells: number,
 * }} EntrySummary
 */
/** @typedef {"idle" | "saving" | "saved" | "failed"} SaveStatus */
/** @typedef {"off" | "ready" | "saving" | "saved" | "failed"} Tone */
/** @typedef {{ label: string, tone: Tone, note: string }} Button */
/** @typedef {"on_target" | "book"} TriKey */

/** @type {readonly (readonly [string, string])[]} */
export const PARTS = [
  ["subject", "Subject"],
  ["composition", "Composition"],
  ["lines", "Lines"],
  ["colorability", "Colorability"],
  ["detail", "Detail"],
  ["idea", "Idea"],
];

export const FLAWS = [
  "grey/shading",
  "open outlines",
  "solid fills",
  "speckle",
  "too dense",
  "too sparse",
  "anatomy/hands",
  "text/artifacts",
  "cropped",
  "style drift",
];

/** @type {readonly { key: TriKey, label: string, options: readonly (readonly [string, string])[] }[]} */
export const TRI_ROWS = [
  {
    key: "on_target",
    label: "on target",
    options: [
      ["yes", "yes"],
      ["partly", "partly"],
      ["no", "no"],
    ],
  },
  {
    key: "book",
    label: "book",
    options: [
      ["yes", "yes"],
      ["candidate", "cand."],
      ["no", "no"],
    ],
  },
];

/** @returns {Draft} */
export function blankDraft() {
  return {
    taste: null,
    rows: {},
    render: null,
    flaws: [],
    flags: { book: null },
    on_target: null,
    reason: "",
  };
}

/**
 * The draft a cell opens with: its last rating, or blank.
 * @param {Rating | null} rating
 * @returns {Draft}
 */
export function draftOf(rating) {
  if (rating === null) return blankDraft();
  return {
    ...rating,
    rows: { ...rating.rows },
    flaws: [...rating.flaws],
    flags: { book: rating.flags.book ?? null },
  };
}

/**
 * Tapping the value that is already set clears it.
 * @template T
 * @param {T | null} current
 * @param {T} tapped
 * @returns {T | null}
 */
export function toggled(current, tapped) {
  return current === tapped ? null : tapped;
}

/**
 * @param {Draft} draft
 * @param {TriKey} key
 * @returns {string | null}
 */
export function triValue(draft, key) {
  return key === "on_target" ? draft.on_target : draft.flags[key];
}

/**
 * @param {Draft} draft
 * @param {TriKey} key
 * @param {string} tapped
 * @returns {Draft}
 */
export function withTri(draft, key, tapped) {
  const value = toggled(triValue(draft, key), tapped);
  if (key === "on_target")
    return { ...draft, on_target: /** @type {OnTarget | null} */ (value) };
  return {
    ...draft,
    flags: { ...draft.flags, [key]: /** @type {Flag | null} */ (value) },
  };
}

/**
 * @param {Draft} draft
 * @param {string} flaw
 * @returns {Draft}
 */
export function withFlaw(draft, flaw) {
  const flaws = draft.flaws.includes(flaw)
    ? draft.flaws.filter((f) => f !== flaw)
    : [...draft.flaws, flaw];
  return { ...draft, flaws };
}

/**
 * What the page posts; nothing until Liked is set. Blank rows are left out.
 * @param {Draft} draft
 * @returns {Rating | null}
 */
export function payload(draft) {
  if (draft.taste === null) return null;
  /** @type {Record<string, number>} */
  const rows = {};
  for (const [part] of PARTS) {
    const stars = draft.rows[part];
    if (stars !== undefined && stars !== null) rows[part] = stars;
  }
  return {
    taste: draft.taste,
    rows,
    render: draft.render,
    flaws: FLAWS.filter((f) => draft.flaws.includes(f)),
    flags: { ...draft.flags },
    on_target: draft.on_target,
    reason: draft.reason.trim(),
  };
}

/**
 * @param {CellView} cell
 * @returns {boolean}
 */
export function isRated(cell) {
  return cell.rating !== null || cell.verdict !== null;
}

/**
 * The first unrated cell from `from` on, wrapping around; -1 when all are rated.
 * @param {CellView[]} cells
 * @param {number} from
 * @returns {number}
 */
export function nextUnrated(cells, from) {
  for (let k = 0; k < cells.length; k++) {
    const i = (from + k) % cells.length;
    const cell = cells[i];
    if (cell !== undefined && !isRated(cell)) return i;
  }
  return -1;
}

/**
 * @param {EntrySummary} entry
 * @returns {string}
 */
export function entryStatus(entry) {
  if (entry.rendered === 0) return "nothing rendered yet";
  return entry.unrated > 0 ? `${String(entry.unrated)} to rate` : "all rated";
}

/**
 * The entry that needs work next: one with cells to rate, else one with nothing rendered.
 * @param {EntrySummary[]} entries
 * @param {string} current
 * @returns {string | null}
 */
export function nextEntry(entries, current) {
  const others = entries.filter((e) => e.entry !== current);
  const next =
    others.find((e) => e.unrated > 0) ?? others.find((e) => e.rendered === 0);
  return next?.entry ?? null;
}

/**
 * The confirm text before a set is deleted with its renders and ratings.
 * @param {string} entry
 * @param {CellView[]} cells
 * @returns {string}
 */
export function deletePrompt(entry, cells) {
  const images =
    cells.length === 1 ? "1 image" : `${String(cells.length)} images`;
  const rated = cells.filter(isRated).length;
  const ratings = rated === 1 ? "1 rating" : `${String(rated)} ratings`;
  return `Delete ${entry} for good, with its ${images} and ${ratings}?`;
}

/**
 * The set to open once one is deleted: the next that needs work, else the newest.
 * @param {EntrySummary[]} entries
 * @returns {string | null}
 */
export function entryAfterDelete(entries) {
  return nextEntry(entries, "") ?? entries[0]?.entry ?? null;
}

const PICK_RATER = "Pick a rater above to rate.";

/**
 * The floating button while rating a cell; asks for a rater before it lets you save.
 * @param {{ cellId: string, rerate: boolean, status: SaveStatus, liked: boolean, rater: string | null }} at
 * @returns {Button}
 */
export function submitButton({ cellId, rerate, status, liked, rater }) {
  if (rater === null)
    return { label: "Who's rating?", tone: "off", note: PICK_RATER };
  if (status === "saving")
    return { label: `Saving ${cellId}…`, tone: "saving", note: "" };
  if (status === "saved")
    return { label: `Saved ${cellId}`, tone: "saved", note: "" };
  if (status === "failed")
    return {
      label: "Retry save",
      tone: "failed",
      note: "Save failed. Your input is kept.",
    };
  if (!liked) return { label: "Submit", tone: "off", note: "" };
  const verb = rerate ? "Update" : "Submit";
  return { label: `${verb} ${cellId} →`, tone: "ready", note: "" };
}

/**
 * The floating button on the grid; asks for a rater before it lets you save.
 * @param {{ status: SaveStatus, favorite: boolean, next: boolean, rater: string | null }} at
 * @returns {Button}
 */
export function favoriteButton({ status, favorite, next, rater }) {
  if (rater === null)
    return { label: "Who's rating?", tone: "off", note: PICK_RATER };
  if (status === "saving")
    return { label: "Saving…", tone: "saving", note: "" };
  if (status === "saved")
    return next
      ? { label: "Saved · next set →", tone: "saved", note: "" }
      : { label: "Saved", tone: "off", note: "" };
  if (status === "failed")
    return {
      label: "Retry save",
      tone: "failed",
      note: "Save failed. Favorite is kept.",
    };
  return { label: "Save favorite", tone: favorite ? "ready" : "off", note: "" };
}

/**
 * The other configured raters' taste and verdict of a cell, small and read-only.
 * @param {OtherRating[]} others
 * @returns {string[]}
 */
export function othersLines(others) {
  return others.map((o) => {
    const stars = "★".repeat(o.taste) + "☆".repeat(5 - o.taste);
    return `${o.rater} · ${stars} · ${o.verdict}`;
  });
}
