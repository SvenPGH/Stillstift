import { byId, el } from "./dom.js";

/**
 * What the full-image viewer shows of a cell.
 * @typedef {{
 *   ref: string,
 *   image: string | null,
 *   taste: number | null,
 *   favorite: boolean,
 *   rows: [string, string][],
 *   flaws: string[],
 *   reason: string,
 * }} Shown
 */

/**
 * @param {number | null} taste
 * @returns {{ filled: string, empty: string }}
 */
export function starText(taste) {
  const n = taste ?? 0;
  return { filled: "★".repeat(n), empty: "☆".repeat(5 - n) };
}

/** The viewer's elements, as every page that has one names them. */
export function viewerUi() {
  return {
    viewer: byId("viewer", HTMLElement),
    body: byId("viewer-body", HTMLElement),
    close: byId("viewer-close", HTMLButtonElement),
    image: byId("viewer-image", HTMLImageElement),
    ref: byId("viewer-ref", HTMLElement),
    stars: byId("viewer-stars", HTMLElement),
    fav: byId("viewer-fav", HTMLElement),
    rows: byId("viewer-rows", HTMLElement),
    flaws: byId("viewer-flaws", HTMLElement),
    reason: byId("viewer-reason", HTMLElement),
  };
}

/** @typedef {ReturnType<typeof viewerUi>} ViewerUi */

/**
 * Show the cell full size with its Liked stars, rows, flaws and why; null closes the viewer.
 * @param {ViewerUi} ui
 * @param {Shown | null} shown
 */
export function renderViewer(ui, shown) {
  ui.viewer.hidden = shown === null;
  document.body.classList.toggle("viewing", shown !== null);
  if (shown === null) return;
  if (shown.image !== null && ui.image.getAttribute("src") !== shown.image)
    ui.image.src = shown.image;
  ui.viewer.ariaLabel = shown.ref;
  ui.ref.textContent = shown.ref;
  const { filled, empty } = starText(shown.taste);
  ui.stars.replaceChildren(el("span", "on", filled), empty);
  ui.fav.hidden = !shown.favorite;
  ui.rows.replaceChildren(
    ...shown.rows.map(([key, value]) => {
      const row = el("div", "viewer-row");
      row.append(el("span", "", key), el("span", "mono", value));
      return row;
    }),
  );
  ui.flaws.replaceChildren(...shown.flaws.map((f) => el("span", "badge", f)));
  ui.reason.hidden = shown.reason === "";
  ui.reason.textContent = `“${shown.reason}”`;
}

/**
 * Close on the scrim and the close button. Buttons and links on the scrim keep it open.
 * @param {ViewerUi} ui
 * @param {{ close: () => void }} on
 */
export function wireViewer(ui, { close }) {
  ui.viewer.addEventListener("click", (event) => {
    const target = event.target;
    const inside =
      target instanceof Element &&
      (ui.body.contains(target) || target.closest("button, a") !== null);
    if (!inside) close();
  });
  ui.close.addEventListener("click", close);
}
