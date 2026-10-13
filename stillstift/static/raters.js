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
 * The configured raters, fetched once, and the one picked in this browser.
 * @typedef {{
 *   ready: Promise<void>,
 *   known: () => readonly string[],
 *   current: () => string | null,
 * }} Raters
 */

/**
 * Fetch the configured raters; until they arrive no rater is known, as none is configured yet.
 * @param {() => Promise<readonly string[]>} fetchRaters
 * @param {Pick<Storage, "getItem">} storage
 * @returns {Raters}
 */
export function loadRaters(fetchRaters, storage) {
  /** @type {readonly string[]} */
  let known = [];
  const ready = fetchRaters().then(
    (raters) => {
      known = raters;
    },
    () => {
      known = [];
    },
  );
  return {
    ready,
    known: () => known,
    current: () => savedRater(storage, known),
  };
}

/**
 * The URL asking for `rater`'s own ratings and counts; unchanged when none is picked.
 * @param {string} url
 * @param {string | null} rater
 */
export function withRater(url, rater) {
  if (rater === null) return url;
  const join = url.includes("?") ? "&" : "?";
  return `${url}${join}rater=${encodeURIComponent(rater)}`;
}

/**
 * The URL of a read that must come back as the picked rater's own, made once the raters are
 * known: asked any sooner, it would count every rater's ratings as this one's.
 * @param {Raters} raters
 * @param {string} url
 * @returns {Promise<string>}
 */
export async function raterUrl(raters, url) {
  await raters.ready;
  return withRater(url, raters.current());
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
