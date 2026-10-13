import { describe, expect, it } from "vitest";
import {
  loadRaters,
  raterUrl,
  saveRater,
  savedRater,
  withRater,
} from "./raters.js";

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

describe("withRater", () => {
  it("asks for the rater's own ratings", () => {
    expect(withRater("/api/entries", "Viktoriia")).toBe(
      "/api/entries?rater=Viktoriia",
    );
  });

  it("joins a URL that already has a query", () => {
    expect(withRater("/api/x?v=1", "Sven")).toBe("/api/x?v=1&rater=Sven");
  });

  it("leaves the URL alone when no rater is picked", () => {
    expect(withRater("/api/entries", null)).toBe("/api/entries");
  });
});

describe("raterUrl", () => {
  it("waits for the raters, so a read made at once is still the picked rater's own", async () => {
    const storage = fakeStorage();
    saveRater(storage, "Viktoriia");
    /** @type {(raters: readonly string[]) => void} */
    let arrive = () => undefined;
    const raters = loadRaters(
      () =>
        new Promise((resolve) => {
          arrive = resolve;
        }),
      storage,
    );
    const url = raterUrl(raters, "/api/entries");
    expect(raters.current()).toBeNull();
    arrive(["Sven", "Viktoriia"]);
    expect(await url).toBe("/api/entries?rater=Viktoriia");
  });

  it("reads without a rater when the raters can't be fetched", async () => {
    const storage = fakeStorage();
    saveRater(storage, "Viktoriia");
    const raters = loadRaters(
      () => Promise.reject(new Error("offline")),
      storage,
    );
    expect(await raterUrl(raters, "/api/entries")).toBe("/api/entries");
  });
});
