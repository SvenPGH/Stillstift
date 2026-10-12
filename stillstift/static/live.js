import { api } from "./dom.js";

/** @typedef {Pick<Document, "visibilityState" | "addEventListener">} Visible */
/** @typedef {{ stamp: () => Promise<number>, every: number, doc: Visible }} Watch */

const EVERY = 5000;

/** @returns {Promise<number>} */
async function fetchStamp() {
  const changes = /** @type {{ stamp: number }} */ (await api("/api/changes"));
  return changes.stamp;
}

/**
 * Call `refresh` whenever the curator's change stamp moves: checked every five seconds
 * while the page is visible, and at once when it shows again. The first check only takes the
 * stamp; a failed check or refresh is tried again on the next one.
 * @param {() => Promise<void>} refresh
 * @param {Partial<Watch>} [over] the stamp, interval and document, for tests
 * @returns {() => Promise<void>} one check
 */
export function watchChanges(refresh, over = {}) {
  const stamp = over.stamp ?? fetchStamp;
  const doc = over.doc ?? document;
  /** @type {number | null} */
  let seen = null;
  let busy = false;
  async function check() {
    if (busy || doc.visibilityState !== "visible") return;
    busy = true;
    try {
      const now = await stamp();
      if (now !== seen) {
        if (seen !== null) await refresh();
        seen = now;
      }
    } catch {
      // Offline or mid-deploy: the next check tries again.
    } finally {
      busy = false;
    }
  }
  setInterval(() => void check(), over.every ?? EVERY);
  doc.addEventListener("visibilitychange", () => void check());
  void check();
  return check;
}
