import { button, el } from "./dom.js";
import { isRated, toggled, triValue } from "./rating.js";
import {
  draftCount,
  draftKey,
  neighbour,
  positionText,
  segment,
  stepList,
} from "./steps.js";

/** @typedef {import("./rating.js").CellView} CellView */
/** @typedef {import("./rating.js").Draft} Draft */
/** @typedef {import("./rating.js").TriKey} TriKey */
/** @typedef {import("./rating.js").Button} Button */
/** @typedef {import("./steps.js").Scope} Scope */
/** @typedef {import("./steps.js").Drafts} Drafts */
/** @typedef {{ key: TriKey, label: string, options: readonly (readonly [string, string])[] }} TriRow */
/** @typedef {{ entry: string, cells: CellView[], cur: number, scope: Scope, drafts: Drafts }} Stepping */

/** @type {readonly (readonly [Scope, string])[]} */
const SCOPES = [
  ["torate", "To rate"],
  ["all", "All"],
];

/**
 * A row of five stars; tapping the set star clears it.
 * @param {string} label
 * @param {number | null} value
 * @param {boolean} strong
 * @param {(stars: number | null) => void} set
 * @returns {HTMLElement}
 */
export function starRow(label, value, strong, set) {
  const row = el(
    "div",
    `star-row${strong ? " strong" : ""}${value === null ? "" : " set"}`,
  );
  const buttons = el("span", "star-btns");
  for (let n = 1; n <= 5; n++) {
    const on = value !== null && n <= value;
    const star = button(`star${on ? " on" : ""}`, on ? "★" : "☆", () => {
      set(toggled(value, n));
    });
    star.ariaLabel = `${label}: ${String(n)} star${n > 1 ? "s" : ""}`;
    star.ariaPressed = String(value === n);
    buttons.append(star);
  }
  row.append(
    el("span", "star-label", label),
    buttons,
    el("span", "star-value", value === null ? "" : String(value)),
  );
  return row;
}

/**
 * One toggle chip per flaw, pressed when the flaw is chosen.
 * @param {readonly string[]} names
 * @param {readonly string[]} chosen
 * @param {(flaw: string) => void} flip
 * @returns {HTMLElement[]}
 */
export function flawChips(names, chosen, flip) {
  return names.map((flaw) => {
    const chip = button("chip", flaw, () => {
      flip(flaw);
    });
    chip.ariaPressed = String(chosen.includes(flaw));
    return chip;
  });
}

/**
 * The three-way rows (on target, book), each a radio group of its options.
 * @param {readonly TriRow[]} rows
 * @param {Draft} draft
 * @param {(key: TriKey, option: string) => void} pick
 * @returns {HTMLElement[]}
 */
export function triRows(rows, draft, pick) {
  return rows.map(({ key, label, options }) => {
    const value = triValue(draft, key);
    const row = el("div", `tri-row${value === null ? "" : " set"}`);
    const group = el("div", "seg3");
    group.role = "radiogroup";
    group.ariaLabel = label;
    for (const [option, text] of options) {
      const choice = button("opt", text, () => {
        pick(key, option);
      });
      choice.role = "radio";
      choice.ariaChecked = String(value === option);
      group.append(choice);
    }
    row.append(el("span", "tri-label", label), group);
    return row;
  });
}

/**
 * The progress segments: one button per cell, opening it; `cur` -1 when none is open.
 * @param {Stepping} at
 * @param {(index: number) => void} open
 * @returns {HTMLElement[]}
 */
export function segmentSlots({ entry, cells, cur, drafts }, open) {
  return cells.map((cell, index) => {
    const here = index === cur;
    const drafted = !here && draftKey(entry, cell.cell_id) in drafts;
    const { tone, title } = segment(cell, { open: here, drafted });
    const slot = button("segment-slot", "", () => {
      open(index);
    });
    slot.title = title;
    slot.ariaLabel = title;
    slot.append(el("div", `segment ${tone}`));
    return slot;
  });
}

/**
 * The rated count shown beside the picker.
 * @param {CellView[]} cells
 * @returns {string}
 */
export function ratedText(cells) {
  const rated = cells.filter(isRated).length;
  return `${String(rated)} / ${String(cells.length)} rated`;
}

/**
 * The step row over the rows: ‹ ›, where the open cell sits, the drafts kept and the scope.
 * @param {{ prev: HTMLButtonElement, next: HTMLButtonElement, pos: HTMLElement, drafts: HTMLElement, scope: HTMLElement }} parts
 * @param {Stepping} at
 * @param {(scope: Scope) => void} setScope
 */
export function renderStepRow(parts, at, setScope) {
  const list = stepList(at.cells, at.cur, at.scope);
  parts.prev.disabled = neighbour(list, at.cur, -1) < 0;
  parts.next.disabled = neighbour(list, at.cur, 1) < 0;
  parts.pos.textContent = positionText(at.cells, at.cur, at.scope);
  const kept = draftCount(at.drafts, at.entry, at.cells, at.cur);
  parts.drafts.hidden = kept === 0;
  parts.drafts.textContent = `${String(kept)} unsaved draft${kept === 1 ? "" : "s"} kept`;
  parts.scope.replaceChildren(
    ...SCOPES.map(([scope, label]) => {
      const choice = button("seg-btn", label, () => {
        setScope(scope);
      });
      choice.role = "radio";
      choice.ariaChecked = String(at.scope === scope);
      return choice;
    }),
  );
}

/**
 * The floating submit and the note above it; null hides both.
 * @param {{ submit: HTMLButtonElement, note: HTMLElement }} parts
 * @param {Button | null} shown
 */
export function renderSubmit(parts, shown) {
  parts.submit.hidden = shown === null;
  parts.note.hidden = shown === null || shown.note === "";
  if (shown === null) return;
  parts.submit.textContent = shown.label;
  parts.submit.className = `submit ${shown.tone}`;
  parts.submit.disabled = shown.tone === "off";
  parts.note.textContent = shown.note;
}
