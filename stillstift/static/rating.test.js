import { describe, expect, it } from "vitest";
import { othersLines, submitButton } from "./rating.js";

describe("othersLines", () => {
  it("is empty when nobody else has rated the cell", () => {
    expect(othersLines([])).toEqual([]);
  });

  it("formats each other rater's name, stars and verdict", () => {
    const lines = othersLines([{ rater: "Anna", taste: 3, verdict: "keep" }]);
    expect(lines).toEqual(["Anna · ★★★☆☆ · keep"]);
  });
});

describe("submitButton", () => {
  it("asks for a rater before anything else, even when liked and ready", () => {
    const button = submitButton({
      cellId: "#01",
      rerate: false,
      status: "idle",
      liked: true,
      rater: null,
    });
    expect(button.tone).toBe("off");
    expect(button.label).toBe("Who's rating?");
  });

  it("submits normally once a rater is picked", () => {
    const button = submitButton({
      cellId: "#01",
      rerate: false,
      status: "idle",
      liked: true,
      rater: "Sven",
    });
    expect(button.tone).toBe("ready");
  });
});
