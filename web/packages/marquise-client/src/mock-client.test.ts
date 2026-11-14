import { describe, expect, it } from "vitest";

import { MockMarquiseClient } from "./mock-client";
import { MONTREAL_TIME_ZONE } from "./montreal-date";
import type { CinemaShowtime } from "./cinema";
import type { MovieCardGridItem } from "./movie-grid-client";
import type { ScreeningQuery } from "./discovery-client";

function createScreeningQuery(
  item: MovieCardGridItem,
  showtime: CinemaShowtime,
): ScreeningQuery {
  const time = formatMontrealTime(showtime.startsAt);
  return {
    date: "2026-08-05",
    page: 1,
    movie: item.movie.title,
    movieId: item.movie.id,
    cinemaId: showtime.cinema.id,
    language: showtime.language ?? undefined,
    fromTime: time,
    toTime: time,
  };
}

function formatMontrealTime(startsAt: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: MONTREAL_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(startsAt));
}

async function prepareScreeningFilter() {
  const client = new MockMarquiseClient({ startDate: "2026-08-05" });
  const item = (await client.fetchForDate("2026-08-05"))[0]!;
  const showtime = item.showtimes![0]!;
  return { client, item, showtime, query: createScreeningQuery(item, showtime) };
}

describe("MockMarquiseClient grid", () => {
  it("lists `days` dates starting at `startDate`", async () => {
    const client = new MockMarquiseClient({
      startDate: "2026-08-05",
      days: 7,
    });

    await expect(client.listDates()).resolves.toEqual([
      "2026-08-05",
      "2026-08-06",
      "2026-08-07",
      "2026-08-08",
      "2026-08-09",
      "2026-08-10",
      "2026-08-11",
    ]);
  });

  it("defaults to today with seven selectable days", async () => {
    const client = new MockMarquiseClient();

    const dates = await client.listDates();

    expect(dates).toHaveLength(7);
    expect(dates[0]).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("is deterministic: the same date yields the same items across instances", async () => {
    const first = new MockMarquiseClient({ startDate: "2026-08-05", days: 3 });
    const second = new MockMarquiseClient({ startDate: "2026-08-05", days: 3 });

    expect(await first.fetchForDate("2026-08-06")).toEqual(
      await second.fetchForDate("2026-08-06"),
    );
  });

  it("is deterministic: repeated fetches of the same date are identical", async () => {
    const client = new MockMarquiseClient({ startDate: "2026-08-05", days: 3 });

    expect(await client.fetchForDate("2026-08-05")).toEqual(
      await client.fetchForDate("2026-08-05"),
    );
  });

  it("returns well-formed items for every date in the window", async () => {
    const client = new MockMarquiseClient({ startDate: "2026-08-05", days: 3 });

    for (const date of await client.listDates()) {
      const items = await client.fetchForDate(date);
      expect(items.length).toBeGreaterThan(0);
      for (const item of items) {
        expect(item.key).toBeTruthy();
        expect(item.movie.title.length).toBeGreaterThan(0);
        expect(item.showtimes?.length).toBeGreaterThan(0);
        for (const showtime of item.showtimes ?? []) {
          expect(new Date(showtime.startsAt).getTime()).not.toBeNaN();
          expect(showtime.cinema.id).toBeTruthy();
          expect(showtime.cinema.name.length).toBeGreaterThan(0);
          expect(showtime.ticketUrl).toContain("example.com");
          expect(showtime.language).toBeTruthy();
        }
      }
    }
  });

  it("returns an empty list outside the date window", async () => {
    const client = new MockMarquiseClient({ startDate: "2026-08-05", days: 2 });

    await expect(client.fetchForDate("2026-08-12")).resolves.toEqual([]);
  });
});

describe("MockMarquiseClient detail", () => {
  it("fetches catalogue movie metadata by id", async () => {
    const detail = new MockMarquiseClient();

    await expect(detail.fetchMovie("dune")).resolves.toMatchObject({
      id: "dune",
      title: "Dune: Part Two",
    });
    await expect(detail.fetchMovie("missing")).rejects.toThrow(
      "Movie not found",
    );
  });

  it("lists every selectable date for a movie", async () => {
    const client = new MockMarquiseClient({ startDate: "2026-08-05", days: 3 });
    const dates = await client.listDates();
    const item = (await client.fetchForDate(dates[0] ?? ""))[0];

    await expect(
      client.listDates(item?.movie ?? { title: "?" }),
    ).resolves.toEqual(dates);
  });

  it("returns the same showtimes the grid shows for a movie and date", async () => {
    const client = new MockMarquiseClient({ startDate: "2026-08-05", days: 3 });
    const date = (await client.listDates())[0];
    if (date === undefined) {
      throw new Error("mock grid must provide a date");
    }
    for (const item of await client.fetchForDate(date)) {
      await expect(client.fetchShowtimes(item.movie, date)).resolves.toEqual(
        item.showtimes,
      );
    }
  });

  it("returns empty showtimes for selectable days without a screening", async () => {
    const client = new MockMarquiseClient({ startDate: "2026-08-05", days: 3 });
    const dates = await client.listDates();
    let found: { movie: { id?: string; title: string }; date: string } | null =
      null;

    for (const date of dates) {
      for (const item of await client.fetchForDate(date)) {
        for (const candidate of dates) {
          if (
            (await client.fetchShowtimes(item.movie, candidate)).length === 0
          ) {
            found = { movie: item.movie, date: candidate };
            break;
          }
        }
        if (found !== null) break;
      }
      if (found !== null) break;
    }
    if (found === null) {
      throw new Error("expected some movie to miss a day in the mock data");
    }

    await expect(
      client.fetchShowtimes(found.movie, found.date),
    ).resolves.toEqual([]);
    await expect(client.listDates(found.movie)).resolves.toEqual(dates);
  });

  it("is deterministic across instances", async () => {
    const first = new MockMarquiseClient({ startDate: "2026-08-05", days: 3 });
    const second = new MockMarquiseClient({ startDate: "2026-08-05", days: 3 });
    const grid = new MockMarquiseClient({ startDate: "2026-08-05", days: 3 });
    const item = (await grid.fetchForDate("2026-08-05"))[0];
    if (item === undefined) {
      throw new Error("mock grid must return items");
    }

    await expect(
      first.fetchShowtimes(item.movie, "2026-08-05"),
    ).resolves.toEqual(await second.fetchShowtimes(item.movie, "2026-08-05"));
  });

  it("returns an empty list outside the date window or without an id", async () => {
    const detail = new MockMarquiseClient({ startDate: "2026-08-05", days: 2 });

    await expect(
      detail.fetchShowtimes({ title: "No id" }, "2026-08-05"),
    ).resolves.toEqual([]);
    await expect(
      detail.fetchShowtimes({ id: "dune", title: "Dune" }, "2026-08-12"),
    ).resolves.toEqual([]);
    await expect(detail.listDates({ title: "No id" })).resolves.toEqual([
      "2026-08-05",
      "2026-08-06",
    ]);
  });
});

describe("MockMarquiseClient paged demo", () => {
  it("pages screening rows while keeping grouped poster counts and totals distinct", async () => {
    const client = new MockMarquiseClient({ startDate: "2026-08-05" });
    const catalogue = await client.fetchForDate("2026-08-05");
    const rows = catalogue.flatMap((item) => item.showtimes ?? []);
    const first = await client.fetchScreeningPage({
      date: "2026-08-05",
      page: 1,
      size: 2,
    });
    const next = await client.fetchScreeningPage({
      date: "2026-08-05",
      page: 2,
      size: 2,
    });
    expect(first.total).toBe(rows.length);
    expect(first.pages).toBe(Math.ceil(rows.length / 2));
    expect(first.screeningCount).toBe(2);
    expect(first.items.flatMap((item) => item.showtimes ?? [])).toEqual(
      rows.slice(0, 2),
    );
    expect(next.items.flatMap((item) => item.showtimes ?? [])).toEqual(
      rows.slice(2, 4),
    );
  });

  it("filters demo screenings by title, movie ID, cinema ID, language and Montréal time together", async () => {
    const { client, item, showtime, query } = await prepareScreeningFilter();
    const result = await client.fetchScreeningPage(query);
    expect(result.items.map((match) => match.movie.id)).toEqual([
      item.movie.id,
    ]);
    expect(result.items.flatMap((match) => match.showtimes ?? [])).toEqual([
      showtime,
    ]);
  });

  it("returns an empty screening page for an unmatched title", async () => {
    const client = new MockMarquiseClient({ startDate: "2026-08-05" });
    await expect(
      client.fetchScreeningPage({
        date: "2026-08-05",
        page: 1,
        movie: "missing movie",
      }),
    ).resolves.toMatchObject({ items: [], total: 0 });
  });

  it("searches demo cinema names without fabricating directory pages", async () => {
    const client = new MockMarquiseClient();
    const first = await client.fetchCinemaPage(1, undefined, "moderne");
    expect(first.items.map((cinema) => cinema.id)).toEqual(["cinema-moderne"]);
    expect(first.total).toBe(1);
    await expect(
      client.fetchCinemaPage(2, undefined, "moderne"),
    ).resolves.toMatchObject({ items: [], page: 2, total: 1 });
  });
});
