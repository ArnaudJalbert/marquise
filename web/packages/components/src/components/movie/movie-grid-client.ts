import type { MovieCardGridItem } from "./movie-card-grid";

/**
 * Data source backing a {@link MovieGridController}. Implementations are
 * responsible for turning a "YYYY-MM-DD" date into the full set of movies and
 * screenings for that date; every other filter (cinema, genre, language, time)
 * is applied locally by the controller so only date changes hit the network.
 */
export interface MovieGridClient {
  /** The selectable dates, newest or oldest first, as "YYYY-MM-DD" strings. */
  listDates(): Promise<readonly string[]>;
  /** Fetch every movie and its screenings for a single date. */
  fetchForDate(date: string): Promise<readonly MovieCardGridItem[]>;
}
