import { expect, it, vi } from "vitest";
import { HttpMarquiseClient, HttpMarquiseClientError } from "./http-client";

it("requests one movie-first page with inclusive local dates and no metadata fan-out", async () => {
  const result = { items: [], total: 25, page: 2, size: 24, pages: 2 };
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValue(new Response(JSON.stringify(result)));
  const client = new HttpMarquiseClient({
    baseUrl: "https://api.example",
    fetch,
  });
  const controller = new AbortController();
  expect(
    await client.fetchScreeningMoviesPage(
      { start: "2026-11-01", end: "2026-11-02", page: 2, size: 24 },
      controller.signal,
    ),
  ).toEqual(result);
  expect(fetch).toHaveBeenCalledExactlyOnceWith(
    "https://api.example/v1/screening-movies?start=2026-11-01&end=2026-11-02&page=2&size=24",
    {
      body: "{}",
      headers: { "Content-Type": "application/json" },
      method: "POST",
      signal: controller.signal,
    },
  );
});

it("requests a bounded independent catalogue search through the endpoint", async () => {
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], total: 0, page: 1, pages: 0, size: 24 }),
      ),
    );
  const client = new HttpMarquiseClient({ baseUrl: "", fetch });
  await client.fetchMoviePage(1, undefined, "Dune & more", 24);
  const url = new URL(String(fetch.mock.calls[0]?.[0]), "https://api.example");
  expect(url.pathname).toBe("/v1/movies");
  expect([...url.searchParams]).toEqual([
    ["page", "1"],
    ["size", "24"],
    ["title", "Dune & more"],
  ]);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("serializes combined movie-first filters with repeated alternatives", async () => {
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], total: 0, page: 1, pages: 0, size: 24 }),
      ),
    );
  const client = new HttpMarquiseClient({ baseUrl: "", fetch });
  await client.fetchScreeningMoviesPage({
    start: "2026-11-01",
    end: "2026-11-05",
    page: 1,
    size: 24,
    title: "Dune",
    cinemas: ["c1", "c2"],
    languages: ["VO", "VOSTF"],
    hours: {
      operator: "is",
      ranges: [{ start: 17, end: 21 }],
    },
    excludedCinemas: ["c3", "c4"],
  });
  const url = new URL(String(fetch.mock.calls[0]?.[0]), "https://api.example");
  expect([...url.searchParams]).toEqual([
    ["start", "2026-11-01"],
    ["end", "2026-11-05"],
    ["page", "1"],
    ["size", "24"],
    ["title", "Dune"],
    ["cinema", "c1"],
    ["cinema", "c2"],
    ["exclude_cinema", "c3"],
    ["exclude_cinema", "c4"],
    ["language", "VO"],
    ["language", "VOSTF"],
  ]);
  expect(fetch.mock.calls[0]?.[1]).toMatchObject({
    body: JSON.stringify({
      hours: { operator: "is", ranges: [{ start: 17, end: 21 }] },
    }),
  });
});

it("repeats non-adjacent hour ranges so the API matches them with OR", async () => {
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], total: 0, page: 1, pages: 0, size: 24 }),
      ),
    );
  const client = new HttpMarquiseClient({ baseUrl: "", fetch });
  await client.fetchScreeningMoviesPage({
    start: "2026-11-01",
    page: 1,
    size: 24,
    hours: {
      operator: "is",
      ranges: [
        { start: 0, end: 17 },
        { start: 21, end: 24 },
      ],
    },
  });
  const url = new URL(String(fetch.mock.calls[0]?.[0]), "https://api.example");
  expect(url.pathname).toBe("/v1/screening-movies");
  expect(url.searchParams.has("hours")).toBe(false);
  expect(url.searchParams.has("exclude_cinema")).toBe(false);
  expect(fetch.mock.calls[0]?.[1]).toMatchObject({
    body: JSON.stringify({
      hours: {
        operator: "is",
        ranges: [
          { start: 0, end: 17 },
          { start: 21, end: 24 },
        ],
      },
    }),
  });
});

it("surfaces an invalid hour range rejected by the API", async () => {
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid" }), { status: 422 }),
    );
  const client = new HttpMarquiseClient({ baseUrl: "", fetch });
  await expect(
    client.fetchScreeningMoviesPage({
      start: "2026-11-01",
      page: 1,
      size: 24,
      hours: {
        operator: "is_not",
        ranges: [{ start: 21, end: 17 }],
      },
    }),
  ).rejects.toBeInstanceOf(HttpMarquiseClientError);
  expect(fetch.mock.calls[0]?.[1]).toMatchObject({
    body: JSON.stringify({
      hours: {
        operator: "is_not",
        ranges: [{ start: 21, end: 17 }],
      },
    }),
  });
});

it("propagates API failure and cancellation without a sample-data fallback", async () => {
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValueOnce(new Response("offline", { status: 503 }))
    .mockRejectedValueOnce(new DOMException("Cancelled", "AbortError"));
  const client = new HttpMarquiseClient({ baseUrl: "", fetch });
  const query = { start: "2026-11-01", end: "2026-11-01", page: 1, size: 24 };
  await expect(client.fetchScreeningMoviesPage(query)).rejects.toBeInstanceOf(
    HttpMarquiseClientError,
  );
  await expect(client.fetchScreeningMoviesPage(query)).rejects.toHaveProperty(
    "name",
    "AbortError",
  );
});

it("requests every visible day's screening total in one call with the listing filters", async () => {
  const days = [
    { date: "2026-11-01", screenings: 0 },
    { date: "2026-11-02", screenings: 7 },
  ];
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValue(new Response(JSON.stringify({ days })));
  const client = new HttpMarquiseClient({ baseUrl: "https://api.example", fetch });
  const controller = new AbortController();
  expect(
    await client.fetchScreeningDayCounts(
      {
        start: "2026-11-01",
        end: "2026-11-02",
        title: " Dune ",
        cinemas: ["c1"],
        excludedCinemas: ["c3"],
        languages: ["VO"],
        hours: { operator: "is_not", ranges: [{ start: 0, end: 17 }, { start: 21, end: 24 }] },
      },
      controller.signal,
    ),
  ).toEqual(days);
  expect(fetch).toHaveBeenCalledExactlyOnceWith(
    "https://api.example/v1/screening-day-counts?start=2026-11-01&end=2026-11-02" +
      "&title=Dune&cinema=c1&exclude_cinema=c3&language=VO",
    {
      body: JSON.stringify({
        hours: { operator: "is_not", ranges: [{ start: 0, end: 17 }, { start: 21, end: 24 }] },
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
      signal: controller.signal,
    },
  );
});

it("surfaces a rejected day-count range instead of reporting zero", async () => {
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValue(new Response(JSON.stringify({ detail: "Invalid" }), { status: 422 }));
  const client = new HttpMarquiseClient({ baseUrl: "", fetch });
  await expect(
    client.fetchScreeningDayCounts({ start: "2026-11-02", end: "2026-11-01" }),
  ).rejects.toBeInstanceOf(HttpMarquiseClientError);
});

it("resolves an exact opaque movie ID through the one-ID query, preserving slashes", async () => {
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [{ id: "catalogue/id", title: "Slash film" }],
          total: 1,
          page: 1,
          pages: 1,
          size: 1,
        }),
      ),
    )
    .mockResolvedValueOnce(new Response(JSON.stringify({ items: [] })));
  const client = new HttpMarquiseClient({ baseUrl: "", fetch });
  const controller = new AbortController();
  expect(
    (await client.fetchMovieMetadata("catalogue/id", controller.signal)).id,
  ).toBe("catalogue/id");
  expect(fetch).toHaveBeenNthCalledWith(
    1,
    "/v1/movies?ids=catalogue%2Fid&page=1&size=1",
    { signal: controller.signal },
  );
  await expect(client.fetchMovieMetadata("missing")).rejects.toHaveProperty(
    "name",
    "MovieNotFoundError",
  );
});

it("requests one page of a movie's upcoming screenings from a datetime, preserving slashes", async () => {
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], total: 0, page: 1, pages: 0, size: 100 }),
      ),
    );
  const client = new HttpMarquiseClient({ baseUrl: "", fetch });
  const controller = new AbortController();
  await client.fetchUpcomingScreeningsPage(
    "catalogue/id",
    "2026-11-01T22:00:00.000Z",
    controller.signal,
  );
  const url = new URL(String(fetch.mock.calls[0]?.[0]), "https://api.example");
  expect(url.pathname).toBe("/v1/movies/catalogue%2Fid/screenings");
  expect([...url.searchParams]).toEqual([
    ["from", "2026-11-01T22:00:00.000Z"],
    ["page", "1"],
    ["size", "100"],
  ]);
  expect(fetch).toHaveBeenCalledExactlyOnceWith(expect.any(String), {
    signal: controller.signal,
  });
});
