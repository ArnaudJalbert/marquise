import { expectTypeOf, describe, expect, it } from "vitest";
import type {
  ActiveCatalogueFilterType,
  CatalogueFilter,
  CatalogueFilterType,
  CatalogueSelection,
} from "./catalogue-types";

describe("catalogue filter types", () => {
  it("keeps future filter kinds out of active selections", () => {
    expectTypeOf<CatalogueFilterType>().toEqualTypeOf<
      "cinema" | "time" | "audio" | "subtitles"
    >();
    expectTypeOf<CatalogueFilter["type"]>().toEqualTypeOf<
      ActiveCatalogueFilterType
    >();

    const filters: CatalogueSelection["filters"] = [
      { type: "cinema", value: "cinema-id", operator: "is" },
      { type: "time", value: "evening", operator: "is" },
    ];
    expect(filters).toHaveLength(2);
  });
});

// @ts-expect-error Audio is part of the future vocabulary, not an active filter.
const _unsupportedAudioFilter: CatalogueFilter = { type: "audio", value: "VO", operator: "is" };

// @ts-expect-error Subtitles is part of the future vocabulary, not an active filter.
const _unsupportedSubtitlesFilter: CatalogueFilter = { type: "subtitles", value: "VOSTF", operator: "is" };
