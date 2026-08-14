import type { CinemaShowtime } from "./cinema";
import type { MovieCardData } from "./movie";

/** Raised when a dedicated movie route references an unknown movie id. */
export class MovieNotFoundError extends Error {
  readonly movieId: string;

  constructor(movieId: string) {
    super(`Movie not found: ${movieId}`);
    this.name = "MovieNotFoundError";
    this.movieId = movieId;
  }
}

/**
 * Data source backing a movie detail route. Implementations resolve movie
 * metadata by id and screenings for a single date; the page drives date
 * changes through {@link listDates} and {@link fetchShowtimes} so only the
 * selected date hits the network.
 */
export interface MovieDetailClient {
  /** Resolve the movie metadata required by a dedicated movie route. */
  fetchMovie(movieId: string): Promise<MovieCardData>;
  /** Selectable dates, as "YYYY-MM-DD" strings. Dates without screenings return an empty showtime list. */
  listDates(movie: MovieCardData): Promise<readonly string[]>;
  /** Every screening of the movie on a single date. */
  fetchShowtimes(
    movie: MovieCardData,
    date: string,
  ): Promise<readonly CinemaShowtime[]>;
}
