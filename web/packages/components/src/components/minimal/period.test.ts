import { describe, expect, it } from "vitest";
import { describePeriod, fitView, stepPeriod } from "./period";

// Tuesday November 3, 2026.
const today = "2026-11-03";

describe("describePeriod", () => {
  it.each([
    ["2026-11-03", "2026-11-03", "Today", "Tue Nov 3"],
    ["2026-11-04", "2026-11-04", "Tomorrow", "Wed Nov 4"],
    ["2026-11-05", "2026-11-05", "Thu Nov 5", undefined],
    ["2026-11-06", "2026-11-08", "This weekend", "Nov 6 → Nov 8"],
    ["2026-11-13", "2026-11-15", "Next weekend", "Nov 13 → Nov 15"],
    ["2026-11-20", "2026-11-22", "Weekend of Nov 20", "Nov 20 → Nov 22"],
    ["2026-11-09", "2026-11-15", "Week of Nov 9", "Nov 9 → Nov 15"],
    ["2026-11-03", "2026-11-05", "Nov 3 → Nov 5", undefined],
  ])("names %s to %s as %s", (start, end, title, detail) => {
    /** Scenario: the header names common periods and shows the dates under a name. */
    const period = describePeriod(start, end, today);
    expect([period.title, period.detail]).toEqual([title, detail]);
  });

  it("names the rest of the current weekend when today is Saturday", () => {
    /** Scenario: on Saturday, Saturday and Sunday are still this weekend. */
    expect(describePeriod("2026-11-07", "2026-11-08", "2026-11-07").title).toBe(
      "This weekend",
    );
  });
});

describe("stepPeriod", () => {
  it.each([
    ["2026-11-03", "2026-11-03", 1, ["2026-11-04", "2026-11-04"]],
    ["2026-11-04", "2026-11-04", -1, ["2026-11-03", "2026-11-03"]],
    ["2026-11-03", "2026-11-05", 1, ["2026-11-06", "2026-11-08"]],
    ["2026-11-06", "2026-11-08", 1, ["2026-11-13", "2026-11-15"]],
    ["2026-11-09", "2026-11-15", 1, ["2026-11-16", "2026-11-22"]],
  ])("steps %s to %s by %i period", (start, end, direction, expected) => {
    /** Scenario: stepping moves by the period's own length; weekends move a week. */
    expect(stepPeriod(start, end, today, direction as 1 | -1)).toEqual(expected);
  });

  it("returns to the rest of the current weekend from next weekend", () => {
    /** Scenario: on Saturday, stepping back from next weekend stops at today. */
    expect(stepPeriod("2026-11-13", "2026-11-15", "2026-11-07", -1)).toEqual([
      "2026-11-07",
      "2026-11-08",
    ]);
  });

  it("refuses to step before today or past the horizon", () => {
    /** Scenario: the stepper cannot leave the six-week day strip. */
    expect(stepPeriod("2026-11-03", "2026-11-03", today, -1)).toBeUndefined();
    expect(stepPeriod("2026-11-04", "2026-11-06", today, -1)).toBeUndefined();
    expect(stepPeriod("2026-12-14", "2026-12-14", today, 1)).toBeUndefined();
  });
});

describe("fitView", () => {
  it("shows two weeks for a week or less inside one fortnight", () => {
    /** Scenario: auto zoom keeps short periods in the day view. */
    expect(fitView(undefined, 0, 0)).toEqual({ days: 14, first: 0 });
    expect(fitView(undefined, 9, 15)).toEqual({ days: 14, first: 7 });
  });

  it("widens to six weeks for periods longer than a week", () => {
    /** Scenario: auto zoom widens when the period is longer than a week. */
    expect(fitView(undefined, 0, 9)).toEqual({ days: 42, first: 0 });
    expect(fitView({ days: 14, first: 0 }, 3, 10)).toEqual({ days: 42, first: 0 });
  });

  it("keeps the last fortnight inside the horizon", () => {
    /** Scenario: a short period at the end of the strip shows the last two weeks. */
    expect(fitView(undefined, 40, 41)).toEqual({ days: 14, first: 28 });
  });

  it("keeps the current fortnight when the period is already visible", () => {
    /** Scenario: auto zoom does not jump when the period is in view. */
    expect(fitView({ days: 14, first: 7 }, 8, 9)).toEqual({ days: 14, first: 7 });
  });
});
