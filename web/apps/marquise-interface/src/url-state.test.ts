import { describe, expect, it } from "vitest";

import {
  movieDateFromUrl,
  parseListingsUrl,
  parseRoute,
  serializeListingsUrl,
} from "./url-state";

describe("listings URL state", () => {
  it("parses every persisted setting", () => {
    const url = new URL(
      "https://example.com/?date=2026-08-08&from=15&to=23" +
        "&cinema=Cin%C3%A9ma+Moderne&cinema=Cin%C3%A9ma+Moderne" +
        "&genre=Sci-Fi&language=VOSTF&card=240&details=hidden" +
        "&filters=closed&page=3",
    );

    expect(parseListingsUrl(url)).toEqual({
      date: "2026-08-08",
      filters: {
        timeRange: [15, 23],
        cinemas: ["Cinéma Moderne"],
        genres: ["Sci-Fi"],
        languages: ["VOSTF"],
      },
      cardSize: 240,
      hideDetails: true,
      filtersOpen: false,
      pageIndex: 2,
    });
  });

  it("hides filters unless URL state explicitly opens them", () => {
    expect(parseListingsUrl(new URL("https://example.com/")).filtersOpen).toBe(false);
    expect(
      parseListingsUrl(new URL("https://example.com/?filters=open")).filtersOpen,
    ).toBe(true);
    expect(
      parseListingsUrl(new URL("https://example.com/?filters=closed")).filtersOpen,
    ).toBe(false);
  });

  it("ignores malformed values and clamps card size", () => {
    const state = parseListingsUrl(
      new URL("https://example.com/?date=nope&from=23&to=4&card=999&page=0"),
    );

    expect(state.date).toBeUndefined();
    expect(state.filters.timeRange).toBeUndefined();
    expect(state.cardSize).toBe(320);
    expect(state.pageIndex).toBe(0);
  });

  it("serializes state while preserving unrelated parameters and the hash", () => {
    const url = serializeListingsUrl(
      new URL("https://example.com/old?utm_source=test&date=old#section"),
      {
        date: "2026-08-08",
        filters: {
          timeRange: [15, 24],
          cinemas: ["Cinéma Moderne"],
          genres: [],
          languages: [],
        },
        cardSize: 200,
        hideDetails: false,
        filtersOpen: true,
        pageIndex: 0,
      },
    );

    expect(url.pathname).toBe("/");
    expect(url.searchParams.get("utm_source")).toBe("test");
    expect(url.searchParams.get("date")).toBe("2026-08-08");
    expect(url.searchParams.getAll("cinema")).toEqual(["Cinéma Moderne"]);
    expect(url.searchParams.has("card")).toBe(false);
    expect(url.searchParams.get("filters")).toBe("open");
    expect(url.hash).toBe("#section");
  });

  it("omits closed filter state from URLs", () => {
    const url = serializeListingsUrl(new URL("https://example.com/"), {
      filters: {},
      cardSize: 200,
      hideDetails: false,
      filtersOpen: false,
      pageIndex: 0,
    });

    expect(url.searchParams.has("filters")).toBe(false);
  });
});

describe("application routes", () => {
  it("parses listings, encoded movie ids, and unknown routes", () => {
    expect(parseRoute("/")).toEqual({ kind: "listings" });
    expect(parseRoute("/movies/movie%2Fone")).toEqual({
      kind: "movie",
      movieId: "movie/one",
    });
    expect(parseRoute("/unknown")).toEqual({ kind: "not-found" });
  });

  it("accepts only valid movie dates", () => {
    expect(
      movieDateFromUrl(new URL("https://example.com/movies/a?date=2026-08-08")),
    ).toBe("2026-08-08");
    expect(
      movieDateFromUrl(new URL("https://example.com/movies/a?date=2026-02-30")),
    ).toBeUndefined();
  });
});
