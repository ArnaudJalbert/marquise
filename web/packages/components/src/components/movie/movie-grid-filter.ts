import { getHour } from "./format";
import type { CinemaShowtime } from "marquise-client";
import type { MovieCardGridItem } from "./movie-card-grid";

/** Lower bound of the time-range slider (inclusive), in hours. */
export const TIME_MIN_HOUR = 0;
/** Upper bound of the time-range slider (inclusive), in hours. */
export const TIME_MAX_HOUR = 24;

/**
 * Locally-applied movie grid filters. Empty arrays mean "all". Only the
 * selected date ever triggers a fetch — these filters run against the
 * already-fetched date's data.
 */
export interface MovieFilters {
  /** Case-insensitive movie-title search; empty means no title filter. */
  query: string;
  /** Start–end hours, both inclusive, within `[TIME_MIN_HOUR, TIME_MAX_HOUR]`. */
  timeRange: readonly [number, number];
  /** Cinema names to keep; empty means no cinema filter. */
  cinemas: readonly string[];
  /** Genre names to keep; empty means no genre filter. */
  genres: readonly string[];
  /** Language tags to keep; empty means no language filter. */
  languages: readonly string[];
}

export const DEFAULT_MOVIE_FILTERS: MovieFilters = {
  query: "",
  timeRange: [TIME_MIN_HOUR, TIME_MAX_HOUR],
  cinemas: [],
  genres: [],
  languages: [],
};

/** Create the initial filters, starting the time range at the current Montreal hour. */
export function createDefaultMovieFilters(now: Date = new Date()): MovieFilters {
  return {
    query: "",
    timeRange: [getHour(now.toISOString()), TIME_MAX_HOUR],
    cinemas: [],
    genres: [],
    languages: [],
  };
}

function showtimeMatches(
  showtime: CinemaShowtime,
  filters: MovieFilters,
): boolean {
  if (
    filters.cinemas.length > 0 &&
    !filters.cinemas.includes(showtime.cinema.name)
  ) {
    return false;
  }
  if (filters.languages.length > 0) {
    const language = showtime.language;
    if (
      language === null ||
      language === undefined ||
      !filters.languages.includes(language)
    ) {
      return false;
    }
  }
  const hour = getHour(showtime.startsAt);
  return hour >= filters.timeRange[0] && hour <= filters.timeRange[1];
}

/** True when a showtime-level filter (cinema, language or time) is active. */
function showtimeFilterActive(filters: MovieFilters): boolean {
  return (
    filters.cinemas.length > 0 ||
    filters.languages.length > 0 ||
    filters.timeRange[0] > TIME_MIN_HOUR ||
    filters.timeRange[1] < TIME_MAX_HOUR
  );
}

/**
 * Apply cinema, genre, language and time filters locally to a date's items.
 *
 * Genres filter the movie itself; cinema, language and time prune the movie's
 * showtimes. Items whose movie fails the genre filter are removed. An item with
 * no showtimes at all is kept untouched when no showtime-level filter is
 * active — so "coming soon" movies stay visible — and dropped once a cinema,
 * language or time filter is applied.
 */
export function filterMovieGridItems(
  items: readonly MovieCardGridItem[],
  filters: MovieFilters,
): MovieCardGridItem[] {
  const result: MovieCardGridItem[] = [];
  const query = filters.query.trim().toLocaleLowerCase();
  for (const item of items) {
    if (!item.movie.title.toLocaleLowerCase().includes(query)) {
      continue;
    }
    const movieGenres = item.movie.genres ?? [];
    if (
      filters.genres.length > 0 &&
      !filters.genres.some((genre) => movieGenres.includes(genre))
    ) {
      continue;
    }
    const showtimes = (item.showtimes ?? []).filter((showtime) =>
      showtimeMatches(showtime, filters),
    );
    if (showtimes.length === 0 && showtimeFilterActive(filters)) {
      continue;
    }
    result.push({ ...item, showtimes });
  }
  return result;
}
