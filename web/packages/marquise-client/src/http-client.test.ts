import { expect, it, vi } from "vitest";

import type { CinemaApi, MovieApi, Page } from "./api-types";
import { HttpMarquiseClient } from "./http-client";

let sequence = 0;

function makeMovie(overrides: Partial<MovieApi> = {}): MovieApi {
  sequence += 1;
  return {
    id: `movie-${sequence}`,
    title: "Movie",
    release_year: 2026,
    directors: ["Director"],
    cast: null,
    duration_minutes: 100,
    description: null,
    poster_url: null,
    trailer_url: null,
    genres: ["Drama"],
    original_title: null,
    rating: null,
    origin_countries: null,
    ...overrides,
  };
}

function makeCinema(overrides: Partial<CinemaApi> = {}): CinemaApi {
  sequence += 1;
  return {
    id: `cinema-${sequence}`,
    name: "Cinema",
    address: null,
    city: null,
    website: null,
    ...overrides,
  };
}

function pageOf<T>(
  items: T[],
  total = items.length,
  page = 1,
  size = 100,
): Page<T> {
  return { items, total, page, size, pages: Math.ceil(total / size) };
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

it("requests only the selected directory page", async () => {
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValue(jsonResponse(pageOf([makeCinema()], 250, 2)));
  const client = new HttpMarquiseClient({ baseUrl: "", fetch });
  const controller = new AbortController();
  const result = await client.fetchCinemaPage(2, controller.signal);
  const url = new URL(String(fetch.mock.calls[0]![0]), "http://localhost");
  expect(url.pathname).toBe("/v1/cinemas");
  expect(Object.fromEntries(url.searchParams)).toEqual({
    page: "2",
    size: "100",
  });
  expect(result.page).toBe(2);
  expect(result.total).toBe(250);
  expect(fetch).toHaveBeenCalledExactlyOnceWith(expect.any(String), {
    signal: controller.signal,
  });
});

it("fetches one date-independent catalogue page with optional title search", async () => {
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValue(jsonResponse(pageOf([makeMovie()])));
  const client = new HttpMarquiseClient({
    baseUrl: "https://api.example",
    fetch,
  });
  const controller = new AbortController();
  await client.fetchMoviePage(3, controller.signal, "Dune");
  const url = new URL(String(fetch.mock.calls[0]![0]));
  expect(url.pathname).toBe("/v1/movies");
  expect(Object.fromEntries(url.searchParams)).toEqual({
    page: "3",
    size: "100",
    title: "Dune",
  });
  expect(fetch.mock.calls[0]![1]?.signal).toBe(controller.signal);
  expect(fetch).toHaveBeenCalledOnce();
});

it("queries a movie's exact ID across inclusive Montreal days and the DST transition", async () => {
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValue(jsonResponse(pageOf([])));
  const client = new HttpMarquiseClient({
    baseUrl: "https://api.example",
    fetch,
  });
  await client.fetchScreeningRangePage(
    "movie-a",
    "2026-10-30",
    "2026-11-02",
    2,
  );
  const url = new URL(String(fetch.mock.calls[0]![0]));
  expect(url.pathname).toBe("/v1/screenings");
  expect(Object.fromEntries(url.searchParams)).toEqual({
    movie_id: "movie-a",
    from: "2026-10-30T04:00:00.000Z",
    to: "2026-11-03T04:59:59.999Z",
    page: "2",
    size: "100",
  });
  expect(fetch).toHaveBeenCalledOnce();
});
