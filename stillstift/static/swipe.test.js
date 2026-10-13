import { describe, expect, it } from "vitest";
import { SWIPE_PX, swipeStep } from "./swipe.js";

describe("swipeStep", () => {
  it("steps to the next page on a drag to the left", () => {
    expect(swipeStep({ dx: -SWIPE_PX, dy: 0, fingers: 1 })).toBe(1);
  });

  it("steps to the previous page on a drag to the right", () => {
    expect(swipeStep({ dx: 80, dy: 10, fingers: 1 })).toBe(-1);
  });

  it("ignores a drag shorter than a swipe, like a tap", () => {
    expect(swipeStep({ dx: SWIPE_PX - 1, dy: 0, fingers: 1 })).toBe(0);
  });

  it("ignores a mostly vertical drag, which scrolls", () => {
    expect(swipeStep({ dx: 60, dy: 70, fingers: 1 })).toBe(0);
  });

  it("ignores a two-finger pinch", () => {
    expect(swipeStep({ dx: -120, dy: 0, fingers: 2 })).toBe(0);
  });
});
