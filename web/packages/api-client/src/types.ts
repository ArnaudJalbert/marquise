export interface MovieResponse {
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
  origin_countries: string[] | null;
}

export interface CinemaResponse {
  id: string;
  name: string;
  address: string | null;
  city: string | null;
  website: string | null;
}

export interface ScreeningResponse {
  id: string;
  movie_id: string;
  movie_title: string;
  cinema_id: string;
  cinema_name: string;
  showtime: string;
  ticket_url: string | null;
  room: string | null;
  language: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

/** Shape of the JSON body on every non-2xx response from the Marquise API. */
export interface ApiErrorBody {
  detail: string;
  error_code: string | null;
  request_id: string | null;
}

export interface PaginationParams {
  page?: number;
  size?: number;
}
