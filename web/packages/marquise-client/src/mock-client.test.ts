import { describe, expect, it } from "vitest";

import { MockMovieDetailClient, MockMovieGridClient } from "./mock-client";

describe("MockMovieGridClient", () => {
  it("lists `days` dates starting at `startDate`", async () => {
    const client = new MockMovieGridClient({
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
    const client = new MockMovieGridClient();

    const dates = await client.listDates();

    expect(dates).toHaveLength(7);
    expect(dates[0]).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("is deterministic: the same date yields the same items across instances", async () => {
    const first = new MockMovieGridClient({ startDate: "2026-08-05", days: 3 });
    const second = new MockMovieGridClient({ startDate: "2026-08-05", days: 3 });

    expect(await first.fetchForDate("2026-08-06")).toEqual(
      await second.fetchForDate("2026-08-06"),
    );
  });

  it("is deterministic: repeated fetches of the same date are identical", async () => {
    const client = new MockMovieGridClient({ startDate: "2026-08-05", days: 3 });

    expect(await client.fetchForDate("2026-08-05")).toEqual(
      await client.fetchForDate("2026-08-05"),
    );
  });

  it("returns well-formed items for every date in the window", async () => {
    const client = new MockMovieGridClient({ startDate: "2026-08-05", days: 3 });

    for (const date of await client.listDates()) {
      const items = await client.fetchForDate(date);
      expect(items.length).toBeGreaterThan(0);
      for (const item of items) {
        expect(item.key).toBeTruthy();
        expect(item.movie.title.length).toBeGreaterThan(0);
        expect(item.showtimes?.length).toBeGreaterThan(0);
        for (const showtime of item.showtimes ?? []) {
          expect(showtime.startsAt).toContain(date);
          expect(showtime.cinema.id).toBeTruthy();
          expect(showtime.cinema.name.length).toBeGreaterThan(0);
          expect(showtime.ticketUrl).toContain("example.com");
          expect(showtime.language).toBeTruthy();
        }
      }
    }
  });

  it("returns an empty list outside the date window", async () => {
    const client = new MockMovieGridClient({ startDate: "2026-08-05", days: 2 });

    await expect(client.fetchForDate("2026-08-12")).resolves.toEqual([]);
  });
});

describe("MockMovieDetailClient", () => {
  it("fetches catalogue movie metadata by id", async () => {
    const detail = new MockMovieDetailClient();

    await expect(detail.fetchMovie("dune")).resolves.toMatchObject({
      id: "dune",
      title: "Dune: Part Two",
    });
    await expect(detail.fetchMovie("missing")).rejects.toThrow("Movie not found");
  });

  it("lists the dates the movie actually screens on", async () => {
    const grid = new MockMovieGridClient({ startDate: "2026-08-05", days: 3 });
    const detail = new MockMovieDetailClient({ startDate: "2026-08-05", days: 3 });

    for (const date of await grid.listDates()) {
      const item = (await grid.fetchForDate(date))[0];
      const dates = await detail.listDates(item?.movie ?? { title: "?" });

      expect(dates).toContain(date);
      for (const listed of dates) {
        expect(await detail.fetchShowtimes(item?.movie ?? { title: "?" }, listed)).not.toEqual([]);
      }
    }
  });

  it("returns the same showtimes the grid shows for a movie and date", async () => {
    const grid = new MockMovieGridClient({ startDate: "2026-08-05", days: 3 });
    const detail = new MockMovieDetailClient({ startDate: "2026-08-05", days: 3 });
    const date = (await grid.listDates())[0];
    if (date === undefined) {
      throw new Error("mock grid must provide a date");
    }
    const item = (await grid.fetchForDate(date))[0];
    if (item === undefined) {
      throw new Error("mock grid must return items");
    }

    await expect(detail.fetchShowtimes(item.movie, date)).resolves.toEqual(
      item.showtimes,
    );
  });

  it("returns an empty list for days the movie does not screen", async () => {
    const grid = new MockMovieGridClient({ startDate: "2026-08-05", days: 3 });
    const detail = new MockMovieDetailClient({ startDate: "2026-08-05", days: 3 });

    let found: { movie: { id?: string; title: string }; gap: string } | null =
      null;
    for (const date of await grid.listDates()) {
      for (const item of await grid.fetchForDate(date)) {
        const dates = await detail.listDates(item.movie);
        const gap = (await grid.listDates()).filter(
          (candidate) => !dates.includes(candidate),
        )[0];
        if (item.movie.id !== undefined && gap !== undefined) {
          found = { movie: item.movie, gap };
          break;
        }
      }
      if (found !== null) {
        break;
      }
    }
    if (found === null) {
      throw new Error("expected some movie to miss a day in the mock data");
    }

    await expect(detail.fetchShowtimes(found.movie, found.gap)).resolves.toEqual(
      [],
    );
    await expect(detail.listDates(found.movie)).resolves.not.toContain(found.gap);
  });

  it("is deterministic across instances", async () => {
    const first = new MockMovieDetailClient({ startDate: "2026-08-05", days: 3 });
    const second = new MockMovieDetailClient({ startDate: "2026-08-05", days: 3 });
    const grid = new MockMovieGridClient({ startDate: "2026-08-05", days: 3 });
    const item = (await grid.fetchForDate("2026-08-05"))[0];
    if (item === undefined) {
      throw new Error("mock grid must return items");
    }

    await expect(first.fetchShowtimes(item.movie, "2026-08-05")).resolves.toEqual(
      await second.fetchShowtimes(item.movie, "2026-08-05"),
    );
  });

  it("returns an empty list outside the date window or without an id", async () => {
    const detail = new MockMovieDetailClient({ startDate: "2026-08-05", days: 2 });

    await expect(
      detail.fetchShowtimes({ title: "No id" }, "2026-08-05"),
    ).resolves.toEqual([]);
    await expect(
      detail.fetchShowtimes({ id: "dune", title: "Dune" }, "2026-08-12"),
    ).resolves.toEqual([]);
    await expect(detail.listDates({ title: "No id" })).resolves.toEqual([]);
  });
});
