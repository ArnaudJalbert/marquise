import { describe, expect, it } from "vitest";
import { CATALOGUE_TIME_FILTERS, matchesCatalogueTimeFilter } from "./catalogue-time-filters";

describe("catalogue time filters", () => {
  it("uses half-open hour ranges at the defined boundaries", () => {
    expect(CATALOGUE_TIME_FILTERS.map(({ value, label, start, end }) => ({ value, label, start, end }))).toEqual([
      { value: "matinee", label: "Matinée", start: 0, end: 17 },
      { value: "evening", label: "Evening", start: 17, end: 21 },
      { value: "late", label: "Late", start: 21, end: 24 },
    ]);

    expect(matchesCatalogueTimeFilter("00:00", "matinee")).toBe(true);
    expect(matchesCatalogueTimeFilter("16:59", "matinee")).toBe(true);
    expect(matchesCatalogueTimeFilter("17:00", "matinee")).toBe(false);
    expect(matchesCatalogueTimeFilter("17:00", "evening")).toBe(true);
    expect(matchesCatalogueTimeFilter("20:59", "evening")).toBe(true);
    expect(matchesCatalogueTimeFilter("21:00", "evening")).toBe(false);
    expect(matchesCatalogueTimeFilter("21:00", "late")).toBe(true);
    expect(matchesCatalogueTimeFilter("23:59", "late")).toBe(true);
  });
});
