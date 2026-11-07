import { expect, it } from "vitest";
import { formatScore, startsIn } from "./catalogue-format";

it.each([[8.14, "8.1/10"], [8, "8.0/10"], [0, "0.0/10"], [null, ""], [undefined, ""]])("formats score %s", (score, expected) => {
  expect(formatScore(score)).toBe(expected);
});

it.each([
  [0, "in 0 min"], [0.5, "in 0 min"], [45, "in 45 min"], [59.9, "in 59 min"],
  [60, "in 1 h"], [80.5, "in 1 h 20 min"], [119, "in 1 h 59 min"], [120, ""], [-1, ""],
])("counts down a showtime %s minutes away as %j", (minutes, expected) => {
  /** Scenario: minutes are floored and only times under two hours away get a countdown. */
  const now = Date.parse("2026-10-30T20:00:00Z");
  const showtime = new Date(now + minutes * 60000).toISOString();
  expect(startsIn(showtime, now)).toBe(expected);
});
