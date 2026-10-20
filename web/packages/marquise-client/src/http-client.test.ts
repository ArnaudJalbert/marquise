import { describe, expect, it, vi } from "vitest";

import type { CinemaApi, MovieApi, Page, ScreeningApi } from "./api-types";
import { HttpMarquiseClient, HttpMarquiseClientError } from "./http-client";

let sequence = 0;

function makeScreening(overrides: Partial<ScreeningApi> = {}): ScreeningApi {
  sequence += 1;
  return {
    id: `screening-${sequence}`,
    movie_id: "movie-a",
    movie_title: "Movie A",
    cinema_id: "cinema-1",
    cinema_name: "Cinema One",
    showtime: "2026-08-05T18:30:00Z",
    ticket_url: null,
    room: null,
    language: "VOSTF",
    ...overrides,
  };
}

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

function stubFetch(handler: (url: URL) => Response | unknown) {
  const mock = vi.fn<typeof fetch>();
  mock.mockImplementation(async (input) => {
    const inputUrl =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    const url = new URL(inputUrl, "http://localhost");
    const result = handler(url);
    if (result instanceof Response) {
      return result;
    }
    return jsonResponse(result);
  });
  return mock;
}

const FIXED_NOW = () => new Date("2026-08-05T12:00:00Z");

describe("HttpMarquiseClient paged discovery", () => {
  it("requests exactly the selected screening page, grouping posters without changing totals", async () => {
    const mock = stubFetch((url) => {
      if (url.pathname === "/v1/screenings") {
        expect(url.searchParams.get("page")).toBe("3");
        expect(url.searchParams.get("size")).toBe("2");
        return pageOf([makeScreening(), makeScreening()], 250, 3, 2);
      }
      if (url.pathname === "/v1/movies") {
        expect(url.searchParams.getAll("ids")).toEqual(["movie-a"]);
        return pageOf([makeMovie({ id: "movie-a" })], 200);
      }
      return pageOf([], 250);
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    const result = await client.fetchScreeningPage({
      date: "2026-08-05",
      page: 3,
      size: 2,
    });

    expect(result).toMatchObject({
      page: 3,
      size: 2,
      pages: 125,
      total: 250,
      screeningCount: 2,
    });
    expect(result.items).toHaveLength(1);
    expect(result.items[0]?.showtimes).toHaveLength(2);
    // Metadata endpoints can also advertise more pages: none are drained.
    expect(mock).toHaveBeenCalledTimes(3);
  });

  it("sends all filters to the server in Montréal time and propagates cancellation to enrichment", async () => {
    const controller = new AbortController();
    const mock = stubFetch((url) => {
      if (url.pathname === "/v1/screenings") {
        expect(Object.fromEntries(url.searchParams)).toEqual({
          from: "2026-01-05T23:00:00.000Z",
          to: "2026-01-06T03:30:00.000Z",
          page: "2",
          size: "48",
          movie: "A & B",
          movie_id: "film/id",
          cinema_id: "cinema/id",
          language: "VOSTF",
        });
        return pageOf([makeScreening()], 100, 2, 48);
      }
      return pageOf([]);
    });
    const client = new HttpMarquiseClient({ baseUrl: "", fetch: mock });

    await client.fetchScreeningPage(
      {
        date: "2026-01-05",
        page: 2,
        movie: "A & B",
        movieId: "film/id",
        cinemaId: "cinema/id",
        language: "VOSTF",
        fromTime: "18:00",
        toTime: "22:30",
      },
      controller.signal,
    );

    expect(mock).toHaveBeenCalledTimes(3);
    for (const [, init] of mock.mock.calls)
      expect(init?.signal).toBe(controller.signal);
  });

  it("starts cinema enrichment while movie metadata is still pending", async () => {
    let resolveMovies!: (response: Response) => void;
    const pendingMovies = new Promise<Response>((resolve) => {
      resolveMovies = resolve;
    });
    const mock = vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname === "/v1/screenings")
        return jsonResponse(pageOf([makeScreening()]));
      if (url.pathname === "/v1/movies") return pendingMovies;
      return jsonResponse(pageOf([]));
    });
    const client = new HttpMarquiseClient({ baseUrl: "", fetch: mock });
    const request = client.fetchScreeningPage({ date: "2026-08-05", page: 1 });

    await vi.waitFor(() => {
      expect(mock.mock.calls.some(([url]) => String(url).startsWith("/v1/cinemas?"))).toBe(true);
    });
    resolveMovies(jsonResponse(pageOf([makeMovie({ id: "movie-a" })])));
    await expect(request).resolves.toMatchObject({ screeningCount: 1 });
    expect(mock).toHaveBeenCalledTimes(3);
  });

  it("returns empty screening pages without metadata requests", async () => {
    const mock = stubFetch(() => pageOf([], 0, 1, 48));
    const client = new HttpMarquiseClient({ baseUrl: "", fetch: mock });
    await expect(
      client.fetchScreeningPage({ date: "2026-08-05", page: 1 }),
    ).resolves.toMatchObject({ items: [], total: 0, screeningCount: 0 });
    expect(mock).toHaveBeenCalledTimes(1);
  });

  it("requests only the selected directory page with the server name search", async () => {
    const controller = new AbortController();
    const mock = stubFetch((url) => {
      expect(url.pathname).toBe("/v1/cinemas");
      expect(Object.fromEntries(url.searchParams)).toEqual({
        page: "2",
        size: "100",
        name: "Cinéma & Co",
      });
      return pageOf([makeCinema()], 250, 2);
    });
    const client = new HttpMarquiseClient({ baseUrl: "", fetch: mock });
    const result = await client.fetchCinemaPage(
      2,
      controller.signal,
      "Cinéma & Co",
    );
    expect(result.page).toBe(2);
    expect(result.total).toBe(250);
    expect(mock).toHaveBeenCalledExactlyOnceWith(expect.any(String), {
      signal: controller.signal,
    });
  });

  it("requests only the selected movie showtime page without fetching movie metadata", async () => {
    const mock = stubFetch((url) => {
      if (url.pathname === "/v1/screenings") {
        expect(url.searchParams.get("movie_id")).toBe("movie-a");
        expect(url.searchParams.get("page")).toBe("4");
        return pageOf([makeScreening()], 200, 4, 48);
      }
      expect(url.pathname).toBe("/v1/cinemas");
      return pageOf([]);
    });
    const client = new HttpMarquiseClient({ baseUrl: "", fetch: mock });
    await expect(
      client.fetchShowtimePage("movie-a", "2026-08-05", 4),
    ).resolves.toMatchObject({ page: 4, total: 200 });
    expect(mock).toHaveBeenCalledTimes(2);
  });
});

describe("HttpMarquiseClient grid", () => {
  it("targets relative paths when the base URL is empty (same-origin)", async () => {
    const mock = stubFetch((url) => {
      if (url.pathname === "/v1/screenings") {
        return pageOf([makeScreening()]);
      }
      return pageOf([] as CinemaApi[]);
    });
    const client = new HttpMarquiseClient({
      baseUrl: "",
      fetch: mock,
      now: FIXED_NOW,
      horizonDays: 1,
    });

    await client.fetchForDate("2026-08-05");

    const path = String(mock.mock.calls[0]?.[0]);
    expect(path.startsWith("/v1/screenings?")).toBe(true);
    expect(
      Object.fromEntries(new URL(path, "http://localhost").searchParams),
    ).toEqual({
      from: "2026-08-05T04:00:00.000Z",
      to: "2026-08-06T03:59:59.999Z",
      page: "1",
      size: "100",
    });
  });

  it("lists consecutive Montréal days from today without querying the API", async () => {
    const mock = stubFetch(() => {
      throw new Error("listDates must not hit the network");
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
      now: FIXED_NOW,
      horizonDays: 3,
    });

    await expect(client.listDates()).resolves.toEqual([
      "2026-08-05",
      "2026-08-06",
      "2026-08-07",
    ]);
    expect(mock).not.toHaveBeenCalled();
  });

  it("uses Montréal's current day when UTC is already on the next date", async () => {
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      now: () => new Date("2026-08-05T01:00:00Z"),
      horizonDays: 2,
    });

    await expect(client.listDates()).resolves.toEqual([
      "2026-08-04",
      "2026-08-05",
    ]);
  });

  it("returns an empty date list when the horizon is zero", async () => {
    const mock = stubFetch(() => {
      throw new Error("listDates must not hit the network");
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
      now: FIXED_NOW,
      horizonDays: 0,
    });

    await expect(client.listDates()).resolves.toEqual([]);
    expect(mock).not.toHaveBeenCalled();
  });

  it("maps screenings and movies into grid items with cinema links", async () => {
    const screeningA1 = makeScreening({
      movie_id: "movie-a",
      movie_title: "Movie A",
      cinema_id: "cinema-1",
      cinema_name: "Cinema One",
      showtime: "2026-08-05T18:30:00Z",
      ticket_url: "https://tickets.example.com/a1",
      language: "VOSTF",
    });
    const screeningA2 = makeScreening({
      movie_id: "movie-a",
      movie_title: "Movie A",
      cinema_id: "cinema-2",
      cinema_name: "Cinema Two",
      showtime: "2026-08-05T20:00:00Z",
      language: "VF",
    });
    const screeningB = makeScreening({
      movie_id: "movie-b",
      movie_title: "Movie B",
      cinema_id: "cinema-1",
      cinema_name: "Cinema One",
      showtime: "2026-08-05T21:00:00Z",
    });
    const movieA = makeMovie({
      id: "movie-a",
      title: "Movie A",
      release_year: 2024,
      directors: ["Denis Villeneuve"],
      duration_minutes: 166,
      poster_url: "https://posters.example.com/a.jpg",
      genres: ["Sci-Fi", "Drama"],
    });
    const movieB = makeMovie({
      id: "movie-b",
      title: "Movie B",
      release_year: 2023,
      genres: null,
    });
    const cinema1 = makeCinema({
      id: "cinema-1",
      website: "https://cinema1.example.com",
    });

    const mock = stubFetch((url) => {
      if (url.pathname === "/v1/screenings") {
        return pageOf([screeningA1, screeningA2, screeningB]);
      }
      if (url.pathname === "/v1/movies") {
        return pageOf([movieA, movieB]);
      }
      if (url.pathname === "/v1/cinemas") {
        return pageOf([cinema1]);
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com/",
      fetch: mock,
    });

    const items = await client.fetchForDate("2026-08-05");

    expect(items).toHaveLength(2);
    expect(items[0]).toEqual({
      key: "movie-a",
      movie: {
        id: "movie-a",
        title: "Movie A",
        posterUrl: "https://posters.example.com/a.jpg",
        releaseYear: 2024,
        durationMinutes: 166,
        directors: ["Denis Villeneuve"],
        genres: ["Sci-Fi", "Drama"],
      },
      showtimesUrl: "/movies/movie-a",
      showtimes: [
        {
          startsAt: "2026-08-05T18:30:00Z",
          ticketUrl: "https://tickets.example.com/a1",
          language: "VOSTF",
          cinema: {
            id: "cinema-1",
            name: "Cinema One",
            link: "https://cinema1.example.com",
          },
        },
        {
          startsAt: "2026-08-05T20:00:00Z",
          ticketUrl: null,
          language: "VF",
          cinema: { id: "cinema-2", name: "Cinema Two", link: null },
        },
      ],
    });
    expect(items[1]?.movie.title).toBe("Movie B");
    expect(String(mock.mock.calls[0]?.[0])).toContain(
      "https://api.example.com/v1/screenings",
    );
    expect(
      new URL(String(mock.mock.calls[1]?.[0])).searchParams.getAll("ids"),
    ).toEqual(["movie-a", "movie-b"]);
  });

  it("bounds the legacy grid to page one and enriches only those movie IDs", async () => {
    const screenings = Array.from({ length: 250 }, (_, index) =>
      makeScreening({
        movie_id: `movie-${index}`,
        movie_title: `Movie ${index}`,
      }),
    );
    const movies = screenings.map((screening, index) =>
      makeMovie({ id: screening.movie_id, title: `Movie ${index}` }),
    );

    const mock = stubFetch((url) => {
      if (url.pathname === "/v1/screenings") {
        const page = Number(url.searchParams.get("page") ?? 1);
        return pageOf(
          screenings.slice((page - 1) * 100, page * 100),
          screenings.length,
          page,
          100,
        );
      }
      if (url.pathname === "/v1/movies") {
        const ids = url.searchParams.getAll("ids");
        return pageOf(movies.filter((movie) => ids.includes(movie.id)));
      }
      if (url.pathname === "/v1/cinemas") {
        return pageOf([] as CinemaApi[]);
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    const items = await client.fetchForDate("2026-08-05");

    expect(items).toHaveLength(100);
    const screeningCalls = mock.mock.calls.filter((call) =>
      String(call[0]).includes("/v1/screenings"),
    );
    expect(screeningCalls).toHaveLength(1);
    expect(String(screeningCalls[0]?.[0])).toContain("page=1&size=100");
    const movieCalls = mock.mock.calls.filter((call) =>
      String(call[0]).includes("/v1/movies"),
    );
    expect(movieCalls).toHaveLength(1);
    expect((String(movieCalls[0]?.[0]).match(/ids=/g) ?? []).length).toBe(100);
  });

  it("clamps a legacy limit above 100 without fetching another page", async () => {
    const screenings = Array.from({ length: 150 }, () => makeScreening());
    const mock = stubFetch((url) => {
      if (url.pathname === "/v1/screenings") {
        const page = Number(url.searchParams.get("page") ?? 1);
        return pageOf(
          screenings.slice((page - 1) * 100, page * 100),
          screenings.length,
          page,
          100,
        );
      }
      if (url.pathname === "/v1/movies") {
        return pageOf([makeMovie({ id: "movie-a", title: "Movie A" })]);
      }
      if (url.pathname === "/v1/cinemas") {
        return pageOf([] as CinemaApi[]);
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
      maxScreenings: 120,
    });

    const items = await client.fetchForDate("2026-08-05");

    expect(items).toHaveLength(1);
    expect(items[0]?.showtimes).toHaveLength(100);
    expect(
      mock.mock.calls.filter((call) =>
        String(call[0]).includes("/v1/screenings"),
      ),
    ).toHaveLength(1);
  });

  it("falls back to the screening title when movie metadata is missing", async () => {
    const screening = makeScreening({
      movie_id: "movie-ghost",
      movie_title: "Ghost Movie",
      showtime: "2026-08-05T19:00:00Z",
    });
    const mock = stubFetch((url) => {
      if (url.pathname === "/v1/screenings") {
        return pageOf([screening]);
      }
      if (url.pathname === "/v1/movies") {
        return pageOf([] as MovieApi[]);
      }
      if (url.pathname === "/v1/cinemas") {
        return pageOf([] as CinemaApi[]);
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    const items = await client.fetchForDate("2026-08-05");

    expect(items).toHaveLength(1);
    expect(items[0]?.movie.title).toBe("Ghost Movie");
    expect(items[0]?.movie.posterUrl).toBeNull();
  });

  it("keeps grid items when the cinemas request fails", async () => {
    const mock = stubFetch((url) => {
      if (url.pathname === "/v1/screenings") {
        return pageOf([makeScreening()]);
      }
      if (url.pathname === "/v1/movies") {
        return pageOf([makeMovie({ id: "movie-a", title: "Movie A" })]);
      }
      if (url.pathname === "/v1/cinemas") {
        return new Response("boom", { status: 500 });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    const items = await client.fetchForDate("2026-08-05");

    expect(items).toHaveLength(1);
    expect(items[0]?.showtimes?.[0]?.cinema.link).toBeNull();
  });

  it("keeps optional cinema enrichment bounded and scoped to each concurrent request", async () => {
    const mock = stubFetch((url) => {
      if (url.pathname === "/v1/screenings") {
        return pageOf([makeScreening()]);
      }
      if (url.pathname === "/v1/movies") {
        return pageOf([makeMovie({ id: "movie-a", title: "Movie A" })]);
      }
      return pageOf([
        makeCinema({ id: "cinema-1", website: "https://cinema.example" }),
      ]);
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    const results = await Promise.all([
      client.fetchForDate("2026-08-05"),
      client.fetchForDate("2026-08-06"),
      client.fetchForDate("2026-08-07"),
    ]);

    expect(
      results.map((items) => items[0]?.showtimes?.[0]?.cinema.link),
    ).toEqual([
      "https://cinema.example",
      "https://cinema.example",
      "https://cinema.example",
    ]);
    expect(
      mock.mock.calls.filter((call) => String(call[0]).includes("/v1/cinemas")),
    ).toHaveLength(3);
  });

  it("retries the optional cinema lookup after a failure", async () => {
    let cinemaCalls = 0;
    const mock = stubFetch((url) => {
      if (url.pathname === "/v1/screenings") {
        return pageOf([makeScreening()]);
      }
      if (url.pathname === "/v1/movies") {
        return pageOf([makeMovie({ id: "movie-a", title: "Movie A" })]);
      }
      cinemaCalls += 1;
      return cinemaCalls === 1
        ? new Response("boom", { status: 500 })
        : pageOf([
            makeCinema({ id: "cinema-1", website: "https://cinema.example" }),
          ]);
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    const first = await client.fetchForDate("2026-08-05");
    const second = await client.fetchForDate("2026-08-07");

    expect(first[0]?.showtimes?.[0]?.cinema.link).toBeNull();
    expect(second[0]?.showtimes?.[0]?.cinema.link).toBe(
      "https://cinema.example",
    );
    expect(cinemaCalls).toBe(2);
  });

  it("throws an HttpMarquiseClientError on a failing response", async () => {
    const mock = stubFetch(() => new Response("boom", { status: 503 }));
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
      now: FIXED_NOW,
    });

    const caught = await client
      .fetchForDate("2026-08-05")
      .catch((error: unknown) => error);

    expect(caught).toBeInstanceOf(HttpMarquiseClientError);
    if (caught instanceof HttpMarquiseClientError) {
      expect(caught.status).toBe(503);
      expect(caught.path).toContain("/v1/screenings?from=2026-08-05");
    }
  });
});
