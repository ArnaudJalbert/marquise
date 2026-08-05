import { describe, expect, it, vi } from "vitest";

import type { CinemaApi, MovieApi, Page, ScreeningApi } from "./api-types";
import {
  HttpMovieGridClient,
  HttpMovieGridClientError,
} from "./http-client";

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
    const url = new URL(inputUrl);
    const result = handler(url);
    if (result instanceof Response) {
      return result;
    }
    return jsonResponse(result);
  });
  return mock;
}

const FIXED_NOW = () => new Date("2026-08-05T12:00:00Z");

describe("HttpMovieGridClient", () => {
  it("rejects an empty base URL", () => {
    expect(() => new HttpMovieGridClient({ baseUrl: " " })).toThrow(
      "baseUrl must not be empty",
    );
  });

  it("lists only the upcoming dates that have screenings, in UTC days", async () => {
    const mock = stubFetch((url) => {
      const from = url.searchParams.get("from");
      if (from === "2026-08-05") {
        return pageOf([makeScreening()]);
      }
      if (from === "2026-08-07") {
        return pageOf([makeScreening()]);
      }
      return pageOf([] as ScreeningApi[], 0);
    });
    const client = new HttpMovieGridClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
      now: FIXED_NOW,
      horizonDays: 3,
    });

    await expect(client.listDates()).resolves.toEqual([
      "2026-08-05",
      "2026-08-07",
    ]);
    expect(mock.mock.calls).toHaveLength(3);
    expect(String(mock.mock.calls[0]?.[0])).toContain(
      "/v1/screenings?from=2026-08-05&to=2026-08-05&size=1",
    );
  });

  it("returns an empty date list when nothing screens", async () => {
    const mock = stubFetch(() => pageOf([] as ScreeningApi[], 0));
    const client = new HttpMovieGridClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
      now: FIXED_NOW,
      horizonDays: 2,
    });

    await expect(client.listDates()).resolves.toEqual([]);
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
    const client = new HttpMovieGridClient({
      baseUrl: "https://api.example.com/",
      fetch: mock,
    });

    const items = await client.fetchForDate("2026-08-05");

    expect(items).toHaveLength(2);
    expect(items[0]).toEqual({
      key: "movie-a",
      movie: {
        title: "Movie A",
        posterUrl: "https://posters.example.com/a.jpg",
        releaseYear: 2024,
        durationMinutes: 166,
        directors: ["Denis Villeneuve"],
        genres: ["Sci-Fi", "Drama"],
      },
      showtimesUrl: "#",
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
          ticketUrl: "#",
          language: "VF",
          cinema: { id: "cinema-2", name: "Cinema Two", link: "" },
        },
      ],
    });
    expect(items[1]?.movie.title).toBe("Movie B");
    expect(String(mock.mock.calls[0]?.[0])).toContain(
      "https://api.example.com/v1/screenings",
    );
    expect(String(mock.mock.calls[1]?.[0])).toContain(
      "/v1/movies?ids=movie-a&ids=movie-b&size=100",
    );
  });

  it("paginates screenings and bulk-fetches movies in chunks of 100", async () => {
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
    const client = new HttpMovieGridClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    const items = await client.fetchForDate("2026-08-05");

    expect(items).toHaveLength(250);
    const movieCalls = mock.mock.calls.filter((call) =>
      String(call[0]).includes("/v1/movies"),
    );
    expect(movieCalls).toHaveLength(3);
    expect(
      (String(movieCalls[0]?.[0]).match(/ids=/g) ?? []).length,
    ).toBe(100);
    expect(
      (String(movieCalls[2]?.[0]).match(/ids=/g) ?? []).length,
    ).toBe(50);
  });

  it("caps the number of screenings fetched for a date", async () => {
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
    const client = new HttpMovieGridClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
      maxScreenings: 120,
    });

    const items = await client.fetchForDate("2026-08-05");

    expect(items).toHaveLength(1);
    expect(items[0]?.showtimes).toHaveLength(120);
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
    const client = new HttpMovieGridClient({
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
    const client = new HttpMovieGridClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    const items = await client.fetchForDate("2026-08-05");

    expect(items).toHaveLength(1);
    expect(items[0]?.showtimes?.[0]?.cinema.link).toBe("");
  });

  it("throws an HttpMovieGridClientError on a failing response", async () => {
    const mock = stubFetch(() => new Response("boom", { status: 503 }));
    const client = new HttpMovieGridClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
      now: FIXED_NOW,
    });

    const caught = await client.listDates().catch((error: unknown) => error);

    expect(caught).toBeInstanceOf(HttpMovieGridClientError);
    if (caught instanceof HttpMovieGridClientError) {
      expect(caught.status).toBe(503);
      expect(caught.path).toContain("/v1/screenings?from=2026-08-05");
    }
  });
});
