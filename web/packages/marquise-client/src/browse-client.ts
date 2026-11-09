import type { CinemaApi, MovieApi, Page, ScreeningApi } from "./api-types";

export interface ScreeningMovieApi extends MovieApi {
  /** At most three qualifying screenings, in start-time and ID order. */
  screenings: ScreeningApi[];
}
/** Half-open whole Montréal hours, `[start, end)` with `0 <= start < end <= 24`. */
export interface HourRange {
  readonly start: number;
  readonly end: number;
}
export interface HourFilter {
  readonly operator: "is" | "is_not";
  /** Matched with OR before the operator is applied. */
  readonly ranges: readonly HourRange[];
}
/** Non-date filters shared by the screening listing and its daily counts. */
export interface ScreeningFilters {
  title?: string;
  cinemas?: readonly string[];
  languages?: readonly string[];
  hours?: HourFilter;
  excludedCinemas?: readonly string[];
}
export interface ScreeningMovieQuery extends ScreeningFilters {
  start: string;
  end?: string;
  page: number;
}
/** An inclusive Montréal horizon of at most 42 days. */
export interface ScreeningDayCountQuery extends ScreeningFilters {
  start: string;
  end: string;
}
/** Matching screening occurrences on one Montréal date. */
export interface ScreeningDayCountApi {
  date: string;
  screenings: number;
}
/** Production browsing reads. Every listing call requests exactly one page. */
export interface BrowseClient {
  fetchCinemaPage(
    page: number,
    signal?: AbortSignal,
  ): Promise<Page<CinemaApi>>;
  fetchScreeningMoviesPage(
    query: ScreeningMovieQuery,
    signal?: AbortSignal,
  ): Promise<Page<ScreeningMovieApi>>;
  /** One total per horizon date, zero included, under the listing filters. */
  fetchScreeningDayCounts(
    query: ScreeningDayCountQuery,
    signal?: AbortSignal,
  ): Promise<ScreeningDayCountApi[]>;
  fetchMoviePage(
    page: number,
    signal?: AbortSignal,
    title?: string,
    size?: number,
  ): Promise<Page<MovieApi>>;
  fetchMovieMetadata(id: string, signal?: AbortSignal): Promise<MovieApi>;
  fetchScreeningRangePage(
    movieId: string,
    start: string,
    end: string,
    page: number,
    signal?: AbortSignal,
  ): Promise<Page<ScreeningApi>>;
  /** One page of 100 of a movie's screenings at or after `from`, soonest first. */
  fetchUpcomingScreeningsPage(
    movieId: string,
    from: string,
    signal?: AbortSignal,
  ): Promise<Page<ScreeningApi>>;
}
