import { describe, expect, it } from "vitest";

import { MockMovieGridClient } from "./mock-client";

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
