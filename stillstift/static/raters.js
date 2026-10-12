const KEY = "stillstift-rater";

/**
 * The rater kept in storage, if any and still configured; null otherwise, so rating controls
 * know to ask for one.
 * @param {Pick<Storage, "getItem">} storage
 * @param {readonly string[]} raters
 * @returns {string | null}
 */
export function savedRater(storage, raters) {
  try {
    const kept = storage.getItem(KEY);
    return kept !== null && raters.includes(kept) ? kept : null;
  } catch {
    return null;
  }
}

/**
 * @param {Pick<Storage, "setItem">} storage
 * @param {string} rater
 */
export function saveRater(storage, rater) {
  try {
    storage.setItem(KEY, rater);
  } catch {
    // Private windows refuse storage; the choice lasts the page.
  }
}

/**
 * Fill the "Who's rating?" row of pills, one per configured rater, the picked one checked.
 * @param {HTMLElement} group
 * @param {readonly string[]} raters
 * @param {string | null} picked
 * @param {(rater: string) => void} pick
 */
export function mountRaterPicker(group, raters, picked, pick) {
  group.replaceChildren(
    ...raters.map((rater) => {
      const button = document.createElement("button");
      button.type = "button";
      button.role = "radio";
      button.className = "seg-btn rater-btn";
      button.textContent = rater;
      button.ariaChecked = String(rater === picked);
      button.addEventListener("click", () => {
        pick(rater);
      });
      return button;
    }),
  );
}
