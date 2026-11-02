import { expect, it } from "vitest";
import { formatScore } from "./catalogue-format";

it.each([[8.14, "8.1/10"], [8, "8.0/10"], [0, "0.0/10"], [null, ""], [undefined, ""]])("formats score %s", (score, expected) => {
  expect(formatScore(score)).toBe(expected);
});
