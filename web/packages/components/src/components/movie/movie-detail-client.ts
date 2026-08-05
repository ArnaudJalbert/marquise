import type { CinemaShowtime } from "./cinema";
import type { MovieCardData } from "./movie";

/**
 * Data source backing a {@link MovieDetailPage}. Implementations resolve a
 * movie's screenings for a single date; the page drives date changes through
 * {@link listDates} and {@link fetchShowtimes} so only the selected date hits
 * the network.
 */
export interface MovieDetailClient {
  /** Dates the movie has screenings on, as "YYYY-MM-DD" strings. */
  listDates(movie: MovieCardData): Promise<readonly string[]>;
  /** Every screening of the movie on a single date. */
  fetchShowtimes(
    movie: MovieCardData,
    date: string,
  ): Promise<readonly CinemaShowtime[]>;
}
