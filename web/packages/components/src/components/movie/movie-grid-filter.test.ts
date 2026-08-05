import { describe, expect, it } from "vitest";

import type { Cinema } from "./cinema";
import type { CinemaShowtime } from "./cinema";
import type { MovieCardGridItem } from "./movie-card-grid";
import {
  DEFAULT_MOVIE_FILTERS,
  filterMovieGridItems,
  type MovieFilters,
} from "./movie-grid-filter";

const cinemaA: Cinema = {
  id: "cinema-a",
  name: "Cinéma A",
  link: "https://example.com/cinemas/cinema-a",
};
const cinemaB: Cinema = {
  id: "cinema-b",
  name: "Cinéma B",
  link: "https://example.com/cinemas/cinema-b",
};

function showtime(
  time: string,
  cinema: Cinema,
  language?: string,
): CinemaShowtime {
  return {
    startsAt: `2026-08-03T${time}:00-04:00`,
    ticketUrl: "https://tickets.example.com/t",
    cinema,
    ...(language === undefined ? {} : { language }),
  };
}

function item(
  key: string,
  genres: string[],
  showtimes: CinemaShowtime[],
): MovieCardGridItem {
  return {
    key,
    movie: { title: key, genres },
    showtimesUrl: `https://example.com/movies/${key}`,
    showtimes,
  };
}

const allFilters: MovieFilters = {
  timeRange: [0, 24],
  cinemas: [],
  genres: [],
  languages: [],
};

describe("filterMovieGridItems", () => {
  it("returns every item when no filters are active", () => {
    const items = [
      item("dune", ["Sci-Fi"], [showtime("18:00", cinemaA)]),
      item("anora", ["Drama"], [showtime("20:00", cinemaB)]),
    ];

    expect(filterMovieGridItems(items, allFilters)).toEqual(items);
  });

  it("filters by cinema name", () => {
    const items = [
      item("dune", [], [showtime("18:00", cinemaA)]),
      item("anora", [], [showtime("20:00", cinemaB)]),
    ];

    const result = filterMovieGridItems(items, {
      ...allFilters,
      cinemas: ["Cinéma A"],
    });

    expect(result.map((entry) => entry.key)).toEqual(["dune"]);
  });

  it("keeps only the showtimes that match the cinema filter", () => {
    const items = [
      item("dune", [], [
        showtime("18:00", cinemaA),
        showtime("21:00", cinemaB),
      ]),
    ];

    const result = filterMovieGridItems(items, {
      ...allFilters,
      cinemas: ["Cinéma A"],
    });

    expect(result).toHaveLength(1);
    expect(result[0]?.showtimes).toHaveLength(1);
    expect(result[0]?.showtimes?.[0]?.cinema.name).toBe("Cinéma A");
  });

  it("filters by genre using an intersection on the movie genres", () => {
    const items = [
      item("dune", ["Sci-Fi", "Drama"], [showtime("18:00", cinemaA)]),
      item("anora", ["Comedy"], [showtime("20:00", cinemaB)]),
    ];

    const result = filterMovieGridItems(items, {
      ...allFilters,
      genres: ["Drama"],
    });

    expect(result.map((entry) => entry.key)).toEqual(["dune"]);
  });

  it("matches when any selected genre is present on the movie", () => {
    const items = [item("dune", ["Sci-Fi"], [showtime("18:00", cinemaA)])];

    const result = filterMovieGridItems(items, {
      ...allFilters,
      genres: ["Action", "Sci-Fi"],
    });

    expect(result.map((entry) => entry.key)).toEqual(["dune"]);
  });

  it("drops movies with no genres when a genre filter is active", () => {
    const items = [item("dune", [], [showtime("18:00", cinemaA)])];

    const result = filterMovieGridItems(items, {
      ...allFilters,
      genres: ["Drama"],
    });

    expect(result).toHaveLength(0);
  });

  it("filters by language and drops showtimes without a language", () => {
    const items = [
      item("dune", [], [
        showtime("18:00", cinemaA, "VOSTF"),
        showtime("21:00", cinemaA),
      ]),
    ];

    const result = filterMovieGridItems(items, {
      ...allFilters,
      languages: ["VOSTF"],
    });

    expect(result).toHaveLength(1);
    expect(result[0]?.showtimes).toHaveLength(1);
    expect(result[0]?.showtimes?.[0]?.language).toBe("VOSTF");
  });

  it("filters by time range with inclusive bounds", () => {
    const items = [
      item("before", [], [showtime("09:00", cinemaA)]),
      item("start", [], [showtime("10:00", cinemaA)]),
      item("middle", [], [showtime("13:00", cinemaA)]),
      item("end", [], [showtime("14:00", cinemaA)]),
      item("after", [], [showtime("15:00", cinemaA)]),
    ];

    const result = filterMovieGridItems(items, {
      ...allFilters,
      timeRange: [10, 14],
    });

    expect(result.map((entry) => entry.key)).toEqual([
      "start",
      "middle",
      "end",
    ]);
  });

  it("drops movies whose showtimes are all pruned away", () => {
    const items = [
      item("late", [], [showtime("22:00", cinemaA)]),
      item("early", [], [showtime("08:00", cinemaA)]),
    ];

    const result = filterMovieGridItems(items, {
      ...allFilters,
      timeRange: [20, 21],
    });

    expect(result).toHaveLength(0);
  });

  it("keeps typical daytime showtimes under the default filters", () => {
    const items = [
      item("early", [], [showtime("08:00", cinemaA)]),
      item("late", [], [showtime("23:00", cinemaA)]),
    ];

    const result = filterMovieGridItems(items, DEFAULT_MOVIE_FILTERS);

    expect(result).toHaveLength(2);
  });

  it("keeps movies with no showtimes when no showtime filter is active", () => {
    const items = [
      item("coming-soon", [], []),
      item("dune", [], [showtime("18:00", cinemaA)]),
    ];

    const result = filterMovieGridItems(items, allFilters);

    expect(result.map((entry) => entry.key)).toEqual(["coming-soon", "dune"]);
    expect(result[0]?.showtimes).toEqual([]);
  });

  it("drops movies with no showtimes when a showtime filter is active", () => {
    const items = [item("coming-soon", [], [])];

    const result = filterMovieGridItems(items, {
      ...allFilters,
      cinemas: ["Cinéma A"],
    });

    expect(result).toHaveLength(0);
  });

  it("keeps zero-showtime movies when only a genre filter is active", () => {
    const items = [item("coming-soon", ["Drama"], [])];

    const result = filterMovieGridItems(items, {
      ...allFilters,
      genres: ["Drama"],
    });

    expect(result.map((entry) => entry.key)).toEqual(["coming-soon"]);
  });
});
