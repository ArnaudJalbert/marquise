import type { CinemaShowtime } from "./cinema";
import type { MovieCardData } from "./movie";

/** One cell in a movie grid: the movie plus its own screenings. */
export interface MovieCardGridItem {
  /** Stable key for React reconciliation; falls back to title + index. */
  key?: string;
  movie: MovieCardData;
  showtimes?: readonly CinemaShowtime[];
  /** Link to the "all showtimes" page; the movie title always links to it. */
  showtimesUrl: string;
}

/**
 * Data source backing a movie grid view. Implementations turn a "YYYY-MM-DD"
 * date into a collection of movies and screenings for that date; cinema,
 * genre, language and time filters are applied locally by the view, so only
 * date changes hit the data source. The HTTP implementation supplies only its
 * first API page (at most 100 screenings). Use DiscoveryClient for server
 * filtering, pagination, and honest result totals.
 */
export interface MovieGridClient {
  /** The selectable dates, newest or oldest first, as "YYYY-MM-DD" strings. */
  listDates(): Promise<readonly string[]>;
  /** Fetch a date's collection; the HTTP implementation returns page one only. */
  fetchForDate(date: string): Promise<readonly MovieCardGridItem[]>;
}
