import { describe, expect, it } from "vitest";

import {
  montrealDateTime,
  montrealDayRange,
  toMontrealIsoDate,
} from "./montreal-date";

describe("montrealDayRange", () => {
  it("uses the full Montréal day during daylight saving time", () => {
    expect(montrealDayRange("2026-08-05")).toEqual({
      from: "2026-08-05T04:00:00.000Z",
      to: "2026-08-06T03:59:59.999Z",
    });
  });

  it("accounts for the shortened spring-forward day", () => {
    expect(montrealDayRange("2026-03-08")).toEqual({
      from: "2026-03-08T05:00:00.000Z",
      to: "2026-03-09T03:59:59.999Z",
    });
  });

  it("accounts for the extended fall-back day", () => {
    expect(montrealDayRange("2026-11-01")).toEqual({
      from: "2026-11-01T04:00:00.000Z",
      to: "2026-11-02T04:59:59.999Z",
    });
  });
});

describe("toMontrealIsoDate", () => {
  it("maps a previous UTC evening to the correct Montréal calendar date", () => {
    expect(toMontrealIsoDate(new Date("2026-08-06T01:00:00Z"))).toBe(
      "2026-08-05",
    );
  });
});

describe("montrealDateTime", () => {
  it("uses the offset in effect on each side of daylight saving time", () => {
    expect(montrealDateTime("2026-03-07", "11:15")).toBe(
      "2026-03-07T16:15:00.000Z",
    );
    expect(montrealDateTime("2026-03-08", "11:15")).toBe(
      "2026-03-08T15:15:00.000Z",
    );
  });
});
