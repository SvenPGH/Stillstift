import { describe, expect, it } from "vitest";
import { saveRater, savedRater } from "./raters.js";

/** A plain object standing in for localStorage in tests. */
function fakeStorage() {
  /** @type {Record<string, string>} */
  const kept = {};
  return {
    getItem: (/** @type {string} */ key) => kept[key] ?? null,
    setItem: (/** @type {string} */ key, /** @type {string} */ value) => {
      kept[key] = value;
    },
  };
}

describe("savedRater", () => {
  it("is null when nothing has been picked", () => {
    expect(savedRater(fakeStorage(), ["Sven", "Anna"])).toBeNull();
  });

  it("returns the rater once saved, if still configured", () => {
    const storage = fakeStorage();
    saveRater(storage, "Anna");
    expect(savedRater(storage, ["Sven", "Anna"])).toBe("Anna");
  });

  it("is null when the saved rater is no longer configured", () => {
    const storage = fakeStorage();
    saveRater(storage, "Mallory");
    expect(savedRater(storage, ["Sven", "Anna"])).toBeNull();
  });

  it("is null when storage throws, as in a private window", () => {
    const storage = {
      getItem: () => {
        throw new Error("blocked");
      },
    };
    expect(savedRater(storage, ["Sven", "Anna"])).toBeNull();
  });
});
