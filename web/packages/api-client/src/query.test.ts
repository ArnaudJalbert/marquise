import { describe, expect, it } from "vitest";
import { buildQuery } from "./query";

describe("buildQuery", () => {
  it("returns an empty string when there are no params", () => {
    expect(buildQuery({})).toBe("");
  });

  it("skips keys whose value is undefined", () => {
    expect(buildQuery({ title: undefined, page: 1 })).toBe("?page=1");
  });

  it("serializes Date values via toISOString", () => {
    const date = new Date("2026-01-15T00:00:00.000Z");
    expect(buildQuery({ from: date })).toBe(
      `?from=${encodeURIComponent(date.toISOString())}`,
    );
  });

  it("serializes multiple params together", () => {
    const qs = buildQuery({ title: "Dune", page: 2, size: 10 });
    const params = new URLSearchParams(qs.slice(1));
    expect(params.get("title")).toBe("Dune");
    expect(params.get("page")).toBe("2");
    expect(params.get("size")).toBe("10");
  });
});
