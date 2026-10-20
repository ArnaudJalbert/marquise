import type { CinemaApi, Page } from "./api-types";
import type { MovieCardGridItem } from "./movie-grid-client";
import type { CinemaShowtime } from "./cinema";

/** Server-supported filters only. A page counts screenings, not unique films. */
export interface ScreeningQuery {
  date: string;
  page: number;
  size?: number;
  movie?: string;
  movieId?: string;
  cinemaId?: string;
  language?: string;
  fromTime?: string;
  toTime?: string;
}
export interface ScreeningPage extends Omit<Page<MovieCardGridItem>, "items"> {
  items: MovieCardGridItem[];
  screeningCount: number;
}
export interface DiscoveryClient {
  fetchScreeningPage(
    query: ScreeningQuery,
    signal?: AbortSignal,
  ): Promise<ScreeningPage>;
  fetchCinemaPage(
    page: number,
    signal?: AbortSignal,
    name?: string,
  ): Promise<Page<CinemaApi>>;
  fetchShowtimePage(
    movieId: string,
    date: string,
    page: number,
    signal?: AbortSignal,
  ): Promise<Page<CinemaShowtime>>;
}
