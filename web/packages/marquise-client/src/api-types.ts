/** Envelope returned by every paginated endpoint of the REST API. */
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

/** A screening as returned by `GET /v1/screenings`. */
export interface ScreeningApi {
  id: string;
  movie_id: string;
  movie_title: string;
  cinema_id: string;
  cinema_name: string;
  /** ISO-8601 timestamp of the screening start, in UTC. */
  showtime: string;
  ticket_url: string | null;
  room: string | null;
  language: string | null;
}

/** A movie as returned by `GET /v1/movies`. */
export interface MovieApi {
  id: string;
  title: string;
  release_year: number | null;
  directors: string[] | null;
  cast: string[] | null;
  duration_minutes: number | null;
  description: string | null;
  poster_url: string | null;
  trailer_url: string | null;
  genres: string[] | null;
  original_title: string | null;
  rating: string | null;
  tmdb_rating?: number | null;
  tmdb_vote_count?: number | null;
  origin_countries: string[] | null;
}

/** A cinema as returned by `GET /v1/cinemas`. */
export interface CinemaApi {
  id: string;
  name: string;
  address: string | null;
  city: string | null;
  website: string | null;
}
