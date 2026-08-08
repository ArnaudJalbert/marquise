/** Flat, denormalised movie data — safe to pass straight from an API response. */
export interface MovieCardData {
  /** The movie's API id; set when the movie is known to the data source. */
  id?: string;
  title: string;
  posterUrl?: string | null;
  releaseYear?: number | null;
  durationMinutes?: number | null;
  directors?: readonly string[] | null;
  /** Genres, e.g. ["Drama", "Sci-Fi"] — used for local genre filtering. */
  genres?: readonly string[] | null;
}
