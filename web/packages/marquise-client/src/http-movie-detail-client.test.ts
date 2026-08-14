import { describe, expect, it, vi } from "vitest";

import type { CinemaApi, MovieApi, Page, ScreeningApi } from "./api-types";
import { HttpMarquiseClient, HttpMarquiseClientError } from "./http-client";
import { MovieNotFoundError } from "./movie-detail-client";

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

const MOVIE = {
  id: "movie-a",
  title: "Movie A",
};

describe("HttpMarquiseClient detail", () => {
  it("fetches movie metadata by id", async () => {
    const movie: MovieApi = {
      id: "movie-a",
      title: "Movie A",
      release_year: 2026,
      directors: ["Director A"],
      cast: null,
      duration_minutes: 123,
      description: null,
      poster_url: "https://example.com/poster.jpg",
      trailer_url: null,
      genres: ["Drama"],
      original_title: null,
      rating: null,
      origin_countries: null,
    };
    const mock = stubFetch((url) => {
      expect(url.pathname).toBe("/v1/movies/movie-a");
      return movie;
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    await expect(client.fetchMovie("movie-a")).resolves.toEqual({
      id: "movie-a",
      title: "Movie A",
      releaseYear: 2026,
      directors: ["Director A"],
      durationMinutes: 123,
      posterUrl: "https://example.com/poster.jpg",
      genres: ["Drama"],
    });
  });

  it("reports a missing movie with the route-level error", async () => {
    const mock = stubFetch(() => new Response("missing", { status: 404 }));
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    await expect(client.fetchMovie("missing")).rejects.toBeInstanceOf(
      MovieNotFoundError,
    );
  });

  it("lists every horizon date for a movie without querying screenings", async () => {
    const mock = stubFetch(() => {
      throw new Error("listDates must not hit the network");
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
      now: FIXED_NOW,
      horizonDays: 3,
    });

    await expect(client.listDates(MOVIE)).resolves.toEqual([
      "2026-08-05",
      "2026-08-06",
      "2026-08-07",
    ]);
    await expect(client.listDates({ title: "No id" })).resolves.toEqual([
      "2026-08-05",
      "2026-08-06",
      "2026-08-07",
    ]);
    expect(mock).not.toHaveBeenCalled();
  });

  it("returns an empty date list without querying when the horizon is zero", async () => {
    const mock = stubFetch(() => {
      throw new Error("must not fetch for a zero-day horizon");
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
      now: FIXED_NOW,
      horizonDays: 0,
    });

    await expect(client.listDates(MOVIE)).resolves.toEqual([]);
    expect(mock).not.toHaveBeenCalled();
  });

  it("fetches a date's showtimes within an inclusive Montréal day and maps them", async () => {
    const mock = stubFetch((url) => {
      if (url.pathname === "/v1/screenings") {
        expect(url.searchParams.get("movie_id")).toBe("movie-a");
        expect(url.searchParams.get("from")).toBe("2026-08-05T04:00:00.000Z");
        expect(url.searchParams.get("to")).toBe("2026-08-06T03:59:59.999Z");
        return pageOf([
          makeScreening({
            cinema_id: "cinema-1",
            cinema_name: "Cinema One",
            showtime: "2026-08-05T18:30:00Z",
            ticket_url: "https://tickets.example.com/a",
            language: "VF",
          }),
          makeScreening({
            cinema_id: "cinema-2",
            cinema_name: "Cinema Two",
            showtime: "2026-08-05T21:00:00Z",
          }),
        ]);
      }
      if (url.pathname === "/v1/cinemas") {
        return pageOf([
          makeCinema({ id: "cinema-1", website: "https://cinema1.example.com" }),
        ]);
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    const showtimes = await client.fetchShowtimes(MOVIE, "2026-08-05");

    expect(showtimes).toEqual([
      {
        startsAt: "2026-08-05T18:30:00Z",
        ticketUrl: "https://tickets.example.com/a",
        language: "VF",
        cinema: {
          id: "cinema-1",
          name: "Cinema One",
          link: "https://cinema1.example.com",
        },
      },
      {
        startsAt: "2026-08-05T21:00:00Z",
        ticketUrl: null,
        language: "VOSTF",
        cinema: { id: "cinema-2", name: "Cinema Two", link: null },
      },
    ]);
  });

  it("paginates through all of a movie's screenings on a date", async () => {
    const screenings = Array.from({ length: 150 }, (_, index) =>
      makeScreening({ showtime: `2026-08-05T1${index % 9}:00:00Z` }),
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
      if (url.pathname === "/v1/cinemas") {
        return pageOf([] as CinemaApi[]);
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    const showtimes = await client.fetchShowtimes(MOVIE, "2026-08-05");

    expect(showtimes).toHaveLength(150);
    const screeningCalls = mock.mock.calls.filter((call) =>
      String(call[0]).includes("/v1/screenings"),
    );
    expect(screeningCalls).toHaveLength(2);
  });

  it("returns an empty list of showtimes when the movie has no id", async () => {
    const mock = stubFetch(() => {
      throw new Error("must not fetch without a movie id");
    });
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    await expect(
      client.fetchShowtimes({ title: "No id" }, "2026-08-05"),
    ).resolves.toEqual([]);
    expect(mock).not.toHaveBeenCalled();
  });

  it("throws an HttpMarquiseClientError on a failing response", async () => {
    const mock = stubFetch(() => new Response("boom", { status: 503 }));
    const client = new HttpMarquiseClient({
      baseUrl: "https://api.example.com",
      fetch: mock,
    });

    const caught = await client
      .fetchShowtimes(MOVIE, "2026-08-05")
      .catch((error: unknown) => error);

    expect(caught).toBeInstanceOf(HttpMarquiseClientError);
    if (caught instanceof HttpMarquiseClientError) {
      expect(caught.status).toBe(503);
      expect(caught.path).toContain("/v1/screenings?movie_id=movie-a");
    }
  });
});
