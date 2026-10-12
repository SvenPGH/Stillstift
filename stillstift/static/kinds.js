/** @typedef {"P" | "X" | "T"} Kind */

const KINDS = /** @type {const} */ ({
  P: "P",
  X: "X",
  T: "T",
});
const ENTRY = /^(P|X|T)[0-9]+[a-z]?$/;
/** @type {Partial<Record<Kind, string>>} */
const LAB_BADGES = {
  X: "Experiment · kept out of stats",
  T: "Test · kept out of stats",
};

/**
 * A set's kind from its id: P3 a page set, X2 an experiment, T1 a test; null for an id of no
 * kind.
 * @param {string} entry
 * @returns {Kind | null}
 */
export function kindOf(entry) {
  const found = ENTRY.exec(entry)?.[1];
  return found === undefined ? null : KINDS[/** @type {Kind} */ (found)];
}

/**
 * Whether the set is an experiment or a test: rated on Liked, Render and a why, never counted.
 * @param {string} entry
 * @returns {boolean}
 */
export function isLab(entry) {
  return labBadge(entry) !== "";
}

/**
 * The badge a lab cell is rated under; "" for any other set.
 * @param {string} entry
 * @returns {string}
 */
export function labBadge(entry) {
  const kind = kindOf(entry);
  return kind === null ? "" : (LAB_BADGES[kind] ?? "");
}
