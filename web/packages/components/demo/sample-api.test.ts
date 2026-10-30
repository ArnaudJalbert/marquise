import { describe, expect, it, vi } from "vitest";
import { HttpMarquiseClient } from "marquise-client";
import { loadAllMovies, loadMovieWeek } from "./api";
import { movies } from "./fixtures";
import { sampleApiResponse } from "./sample-api";

function sampleClient() {
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockImplementation(async (input) => {
      const url = new URL(
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.href
            : input.url,
      );
      const body = sampleApiResponse(url);
      return new Response(JSON.stringify(body), {
        status: body ? 200 : 404,
        headers: { "Content-Type": "application/json" },
      });
    });
  return {
    fetch,
    client: new HttpMarquiseClient({ baseUrl: "http://sample.invalid", fetch }),
  };
}

describe("prototype sample API", () => {
  it("loads date-independent catalogue movies through the real HTTP client", async () => {
    const { client, fetch } = sampleClient();
    const result = await loadAllMovies(client, new AbortController().signal);
    expect(result.map((movie) => movie.id)).toEqual(
      movies.map((movie) => movie.id),
    );
    expect(result.every((movie) => movie.poster)).toBe(true);
    expect(fetch).toHaveBeenCalledOnce();
  });

  it("returns every dense screening across all pages without an external backend", async () => {
    const { client, fetch } = sampleClient();
    const dune = movies.find((movie) => movie.id === "dune")!;
    const result = await loadMovieWeek(
      client,
      dune,
      "2026-10-30",
      "2026-11-12",
    );
    expect(result.screenings).toHaveLength(350);
    expect(result.cinemas).toHaveLength(7);
    const dates = [
      ...new Set(result.screenings.map((screening) => screening.date)),
    ];
    expect(dates).toHaveLength(14);
    for (const date of dates)
      expect(
        result.screenings.filter((screening) => screening.date === date),
      ).toHaveLength(25);
    expect(
      result.screenings.find((screening) => screening.date === "2026-11-01")
        ?.time,
    ).toBe("10:00");
    expect(fetch).toHaveBeenCalledTimes(4);
  });

  it("returns only the requested date window and movie, including an empty future window", async () => {
    const { client } = sampleClient();
    const dune = movies.find((movie) => movie.id === "dune")!;
    const result = await loadMovieWeek(
      client,
      dune,
      "2026-10-31",
      "2026-11-03",
    );
    expect(result.screenings).toHaveLength(100);
    expect([
      ...new Set(result.screenings.map((screening) => screening.date)),
    ]).toEqual(["2026-10-31", "2026-11-01", "2026-11-02", "2026-11-03"]);
    const empty = await loadMovieWeek(client, dune, "2027-01-01", "2027-01-04");
    expect(empty.screenings).toEqual([]);
  });

  it("supports catalogue title search and bounded pages", () => {
    const result = sampleApiResponse(
      new URL("http://sample.invalid/v1/movies?title=dune&size=1&page=1"),
    );
    expect(result).toMatchObject({
      total: 1,
      page: 1,
      size: 1,
      pages: 1,
      items: [{ id: "dune" }],
    });
    expect(
      sampleApiResponse(new URL("http://sample.invalid/unrelated")),
    ).toBeUndefined();
  });
});
