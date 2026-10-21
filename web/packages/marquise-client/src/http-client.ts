import type { CinemaApi, MovieApi, Page, ScreeningApi } from "./api-types";
import type { CinemaShowtime } from "./cinema";
import type {
  DiscoveryClient,
  ScreeningQuery,
  ScreeningPage,
} from "./discovery-client";
import type { MovieCardData } from "./movie";
import { posterRenditionUrl } from "./poster-rendition";
import {
  MovieNotFoundError,
  type MovieDetailClient,
} from "./movie-detail-client";
import type { MovieCardGridItem, MovieGridClient } from "./movie-grid-client";
import {
  addDays,
  montrealDateTime,
  montrealDayRange,
  toMontrealIsoDate,
} from "./montreal-date";

export class HttpMarquiseClientError extends Error {
  constructor(
    readonly path: string,
    readonly status: number,
  ) {
    super(`Marquise API request failed: GET ${path} returned ${status}`);
    this.name = "HttpMarquiseClientError";
  }
}
export interface HttpMarquiseClientOptions {
  baseUrl: string;
  horizonDays?: number;
  /** Legacy grid limit, now bounded to a single page of at most 100 screenings. */
  maxScreenings?: number;
  now?: () => Date;
  fetch?: typeof fetch;
}
/** Every read requests exactly one API page. Nothing drains paginated endpoints. */
export class HttpMarquiseClient
  implements MovieGridClient, MovieDetailClient, DiscoveryClient
{
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;
  constructor(private readonly options: HttpMarquiseClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.fetchImpl = (options.fetch ?? globalThis.fetch).bind(globalThis);
  }
  async listDates(_movie?: MovieCardData): Promise<readonly string[]> {
    const today = toMontrealIsoDate((this.options.now ?? (() => new Date()))());
    return Array.from({ length: this.options.horizonDays ?? 7 }, (_, i) =>
      addDays(today, i),
    );
  }
  async fetchForDate(date: string): Promise<readonly MovieCardGridItem[]> {
    return (
      await this.fetchScreeningPage({
        date,
        page: 1,
        size: this.options.maxScreenings ?? 100,
      })
    ).items;
  }
  async fetchMovie(id: string): Promise<MovieCardData> {
    try {
      return this.toMovie(
        await this.fetchJson<MovieApi>(`/v1/movies/${encodeURIComponent(id)}`),
      );
    } catch (error) {
      if (error instanceof HttpMarquiseClientError && error.status === 404)
        throw new MovieNotFoundError(id);
      throw error;
    }
  }
  async fetchShowtimes(
    movie: MovieCardData,
    date: string,
  ): Promise<readonly CinemaShowtime[]> {
    return movie.id
      ? (await this.fetchShowtimePage(movie.id, date, 1)).items
      : [];
  }
  async fetchCinemaPage(
    page: number,
    signal?: AbortSignal,
    name?: string,
  ): Promise<Page<CinemaApi>> {
    const params = new URLSearchParams({ page: String(page), size: "100" });
    if (name) params.set("name", name);
    return this.fetchJson(`/v1/cinemas?${params}`, signal);
  }
  private screeningPath(query: ScreeningQuery): string {
    const range = montrealDayRange(query.date);
    const params = new URLSearchParams({
      from: range.from,
      to: range.to,
      page: String(query.page),
      size: String(Math.min(100, Math.max(1, query.size ?? 48))),
    });
    if (query.fromTime)
      params.set("from", montrealDateTime(query.date, query.fromTime));
    if (query.toTime)
      params.set("to", montrealDateTime(query.date, query.toTime));
    if (query.movie) params.set("movie", query.movie);
    if (query.movieId) params.set("movie_id", query.movieId);
    if (query.cinemaId) params.set("cinema_id", query.cinemaId);
    if (query.language) params.set("language", query.language);
    return `/v1/screenings?${params}`;
  }
  async fetchScreeningPage(
    query: ScreeningQuery,
    signal?: AbortSignal,
  ): Promise<ScreeningPage> {
    const result = await this.fetchJson<Page<ScreeningApi>>(
      this.screeningPath(query),
      signal,
    );
    const ids = [...new Set(result.items.map((item) => item.movie_id))];
    const params = new URLSearchParams({ page: "1", size: "100" });
    for (const id of ids) params.append("ids", id);
    const [movies, cinemas] = await Promise.all([
      ids.length
        ? this.fetchJson<Page<MovieApi>>(`/v1/movies?${params}`, signal).then(
            (page) => page.items,
          )
        : Promise.resolve<MovieApi[]>([]),
      ids.length
        ? this.cinemaLinks(signal)
        : Promise.resolve(new Map<string, string | null>()),
    ]);
    const byId = new Map(movies.map((movie) => [movie.id, movie]));
    return {
      ...result,
      screeningCount: result.items.length,
      items: ids.map((id) => {
        const screenings = result.items.filter((item) => item.movie_id === id);
        const movie = byId.get(id);
        return {
          key: id,
          movie: movie
            ? this.toMovie(movie)
            : {
                id,
                title: screenings[0]?.movie_title ?? "Unknown title",
                posterUrl: null,
              },
          showtimes: screenings.map((item) => this.toShowtime(item, cinemas)),
          showtimesUrl: `/movies/${encodeURIComponent(id)}`,
        };
      }),
    };
  }
  async fetchShowtimePage(
    movieId: string,
    date: string,
    page: number,
    signal?: AbortSignal,
  ): Promise<Page<CinemaShowtime>> {
    const result = await this.fetchJson<Page<ScreeningApi>>(
      this.screeningPath({ date, movieId, page, size: 48 }),
      signal,
    );
    const cinemas = result.items.length
      ? await this.cinemaLinks(signal)
      : new Map<string, string | null>();
    return {
      ...result,
      items: result.items.map((item) => this.toShowtime(item, cinemas)),
    };
  }
  private toMovie(movie: MovieApi): MovieCardData {
    return {
      id: movie.id,
      title: movie.title,
      posterUrl: posterRenditionUrl(movie.poster_url),
      releaseYear: movie.release_year,
      durationMinutes: movie.duration_minutes,
      directors: movie.directors,
      genres: movie.genres,
    };
  }
  private async cinemaLinks(
    signal?: AbortSignal,
  ): Promise<Map<string, string | null>> {
    // Optional, bounded metadata enrichment. Missing websites never hide screenings.
    const page = await this.fetchCinemaPage(1, signal).catch(() => undefined);
    return new Map(page?.items.map((cinema) => [cinema.id, cinema.website]));
  }
  private toShowtime(
    item: ScreeningApi,
    links: ReadonlyMap<string, string | null>,
  ): CinemaShowtime {
    return {
      startsAt: item.showtime,
      ticketUrl: item.ticket_url,
      language: item.language,
      cinema: {
        id: item.cinema_id,
        name: item.cinema_name,
        link: links.get(item.cinema_id) ?? null,
      },
    };
  }
  private async fetchJson<T>(path: string, signal?: AbortSignal): Promise<T> {
    const response = await this.fetchImpl(this.baseUrl + path, { signal });
    if (!response.ok) throw new HttpMarquiseClientError(path, response.status);
    return (await response.json()) as T;
  }
}
