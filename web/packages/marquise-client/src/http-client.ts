import type {
  BrowseClient,
  ScreeningDayCountApi,
  ScreeningDayCountQuery,
  ScreeningFilters,
  ScreeningMovieApi,
  ScreeningMovieQuery,
} from "./browse-client";
import type { CinemaApi, MovieApi, Page, ScreeningApi } from "./api-types";
import { MovieNotFoundError } from "./movie-not-found-error";
import { montrealDayRange } from "./montreal-date";

export class HttpMarquiseClientError extends Error {
  constructor(
    readonly path: string,
    readonly status: number,
    method = "GET",
  ) {
    super(`Marquise API request failed: ${method} ${path} returned ${status}`);
    this.name = "HttpMarquiseClientError";
  }
}
export interface HttpMarquiseClientOptions {
  baseUrl: string;
  fetch?: typeof fetch;
}
/** Every read requests exactly one API page. Nothing drains paginated endpoints. */
export class HttpMarquiseClient implements BrowseClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;
  constructor(options: HttpMarquiseClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.fetchImpl = (options.fetch ?? globalThis.fetch).bind(globalThis);
  }
  async fetchCinemaPage(
    page: number,
    signal?: AbortSignal,
  ): Promise<Page<CinemaApi>> {
    const params = new URLSearchParams({ page: String(page), size: "100" });
    return this.fetchJson(`/v1/cinemas?${params}`, signal);
  }
  async fetchMoviePage(
    page: number,
    signal?: AbortSignal,
    title?: string,
    size = 100,
  ): Promise<Page<MovieApi>> {
    const params = new URLSearchParams({
      page: String(page),
      size: String(size),
    });
    if (title) params.set("title", title);
    return this.fetchJson(`/v1/movies?${params}`, signal);
  }
  async fetchScreeningMoviesPage(
    query: ScreeningMovieQuery,
    signal?: AbortSignal,
  ): Promise<Page<ScreeningMovieApi>> {
    const params = new URLSearchParams({ start: query.start });
    if (query.end) params.set("end", query.end);
    params.set("page", String(query.page));
    params.set("size", String(query.size));
    return this.postScreeningFilters("/v1/screening-movies", params, query, signal);
  }
  async fetchScreeningDayCounts(
    query: ScreeningDayCountQuery,
    signal?: AbortSignal,
  ): Promise<ScreeningDayCountApi[]> {
    const params = new URLSearchParams({ start: query.start, end: query.end });
    const result = await this.postScreeningFilters<{
      days: ScreeningDayCountApi[];
    }>("/v1/screening-day-counts", params, query, signal);
    return result.days;
  }
  /** Both screening reads send identical filters: query parameters plus a JSON hours body. */
  private postScreeningFilters<ResponseT>(
    path: string,
    params: URLSearchParams,
    filters: ScreeningFilters,
    signal?: AbortSignal,
  ): Promise<ResponseT> {
    if (filters.title?.trim()) params.set("title", filters.title.trim());
    filters.cinemas?.forEach((id) => params.append("cinema", id));
    filters.excludedCinemas?.forEach((id) => params.append("exclude_cinema", id));
    filters.languages?.forEach((language) => params.append("language", language));
    return this.fetchJson(`${path}?${params}`, signal, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(filters.hours ? { hours: filters.hours } : {}),
    });
  }
  async fetchMovieMetadata(
    id: string,
    signal?: AbortSignal,
  ): Promise<MovieApi> {
    // Query IDs preserve opaque slashes that ASGI decodes before path matching.
    const params = new URLSearchParams({ ids: id, page: "1", size: "1" });
    const result = await this.fetchJson<Page<MovieApi>>(
      `/v1/movies?${params}`,
      signal,
    );
    const movie = result.items.find((item) => item.id === id);
    if (!movie) throw new MovieNotFoundError(id);
    return movie;
  }
  async fetchScreeningRangePage(
    movieId: string,
    start: string,
    end: string,
    page: number,
    signal?: AbortSignal,
  ): Promise<Page<ScreeningApi>> {
    const params = new URLSearchParams({
      movie_id: movieId,
      from: montrealDayRange(start).from,
      to: montrealDayRange(end).to,
      page: String(page),
      size: "100",
    });
    return this.fetchJson(`/v1/screenings?${params}`, signal);
  }
  async fetchUpcomingScreeningsPage(
    movieId: string,
    from: string,
    signal?: AbortSignal,
  ): Promise<Page<ScreeningApi>> {
    const params = new URLSearchParams({ from, page: "1", size: "100" });
    return this.fetchJson(
      `/v1/movies/${encodeURIComponent(movieId)}/screenings?${params}`,
      signal,
    );
  }
  private async fetchJson<T>(
    path: string,
    signal?: AbortSignal,
    init: RequestInit = {},
  ): Promise<T> {
    const response = await this.fetchImpl(this.baseUrl + path, {
      ...init,
      signal,
    });
    if (!response.ok)
      throw new HttpMarquiseClientError(
        path,
        response.status,
        init.method ?? "GET",
      );
    return (await response.json()) as T;
  }
}
