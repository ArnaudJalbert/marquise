import type { MovieApi, Page, ScreeningApi } from "./api-types";

export interface ScreeningMovieApi extends MovieApi {
  /** At most three qualifying screenings, in start-time and ID order. */
  screenings: ScreeningApi[];
}
export interface ScreeningMovieQuery {
  start: string;
  end: string;
  page: number;
}
/** Production browsing reads. Every listing call requests exactly one page. */
export interface BrowseClient {
  fetchScreeningMoviesPage(
    query: ScreeningMovieQuery,
    signal?: AbortSignal,
  ): Promise<Page<ScreeningMovieApi>>;
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
}
