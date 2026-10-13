export const SWIPE_PX = 50;

/**
 * Which way a finished drag steps: 1 for next (dragged left), -1 for previous, 0 for none.
 * A mostly vertical drag is a scroll, and one with a second finger down is a pinch.
 * @param {{ dx: number, dy: number, fingers: number }} drag
 * @returns {-1 | 0 | 1}
 */
export function swipeStep({ dx, dy, fingers }) {
  if (fingers > 1 || Math.abs(dx) < SWIPE_PX) return 0;
  if (Math.abs(dx) < Math.abs(dy) * 1.5) return 0;
  return dx < 0 ? 1 : -1;
}

/**
 * Step on a swipe across `target`. The click ending a swipe is swallowed so it never also counts
 * as a tap, and a page pinched in pans instead of stepping.
 * @param {HTMLElement} target
 * @param {(delta: -1 | 1) => void} step
 */
export function wireSwipe(target, step) {
  /** @type {Map<number, { x: number, y: number }>} */
  const down = new Map();
  let fingers = 0;
  let swiped = false;
  target.addEventListener("pointerdown", (event) => {
    if (down.size === 0) fingers = 0;
    down.set(event.pointerId, { x: event.clientX, y: event.clientY });
    fingers = Math.max(fingers, down.size);
    swiped = false;
  });
  target.addEventListener("pointerup", (event) => {
    const from = down.get(event.pointerId);
    down.delete(event.pointerId);
    if (from === undefined || (window.visualViewport?.scale ?? 1) > 1.01)
      return;
    const delta = swipeStep({
      dx: event.clientX - from.x,
      dy: event.clientY - from.y,
      fingers,
    });
    swiped = delta !== 0;
    if (delta !== 0) step(delta);
  });
  target.addEventListener("pointercancel", (event) => {
    down.delete(event.pointerId);
  });
  target.addEventListener(
    "click",
    (event) => {
      if (!swiped) return;
      swiped = false;
      event.stopPropagation();
    },
    true,
  );
}
