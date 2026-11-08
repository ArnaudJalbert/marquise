import { expectTypeOf, describe, expect, it } from "vitest";
import type {
  ActiveCatalogueFilterType,
  ActiveCatalogueSelection,
  CatalogueFilter,
  CatalogueFilterType,
  CatalogueSelection,
} from "./catalogue-types";

describe("catalogue filter types", () => {
  it("keeps future filter kinds out of active selections", () => {
    expectTypeOf<CatalogueFilterType>().toEqualTypeOf<
      "cinema" | "time" | "audio" | "subtitles"
    >();
    expectTypeOf<CatalogueFilter["type"]>().toEqualTypeOf<CatalogueFilterType>();
    expectTypeOf<CatalogueSelection["filters"][number]["type"]>().toEqualTypeOf<CatalogueFilterType>();
    expectTypeOf<ActiveCatalogueSelection["filters"][number]["type"]>().toEqualTypeOf<
      ActiveCatalogueFilterType
    >();

    const filters: CatalogueSelection["filters"] = [
      { type: "cinema", value: "cinema-id", operator: "is" },
      { type: "time", value: "evening", operator: "is" },
    ];
    expect(filters).toHaveLength(2);

    const futureSelection: CatalogueSelection = {
      start: "2026-11-08",
      end: "2026-11-08",
      title: "",
      filters: [
        { type: "audio", value: "VO", operator: "is" },
        { type: "subtitles", value: "VOSTF", operator: "is" },
      ],
    };
    expect(futureSelection.filters).toHaveLength(2);
  });
});

const _invalidActiveSelection: ActiveCatalogueSelection = {
  start: "2026-11-08",
  end: "2026-11-08",
  title: "",
  filters: [
    // @ts-expect-error Audio is valid in CatalogueSelection, not active UI state.
    { type: "audio", value: "VO", operator: "is" },
  ],
};
