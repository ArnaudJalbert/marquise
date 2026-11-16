/** Raised when a dedicated movie route references an unknown movie id. */
export class MovieNotFoundError extends Error {
  readonly movieId: string;

  constructor(movieId: string) {
    super(`Movie not found: ${movieId}`);
    this.name = "MovieNotFoundError";
    this.movieId = movieId;
  }
}
