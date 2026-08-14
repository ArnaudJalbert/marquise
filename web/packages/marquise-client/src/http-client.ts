import type { CinemaShowtime } from "./cinema";
import type { MovieCardData } from "./movie";
import {
  MovieNotFoundError,
  type MovieDetailClient,
} from "./movie-detail-client";
import type { MovieCardGridItem, MovieGridClient } from "./movie-grid-client";
import { addDays, montrealDayRange, toMontrealIsoDate } from "./montreal-date";

import type { CinemaApi, MovieApi, Page, ScreeningApi } from "./api-types";

/** Thrown when a request to the REST API fails with a non-2xx status. */
export class HttpMarquiseClientError extends Error {
  /** The HTTP status code returned by the API. */
  readonly status: number;
  /** The request path, e.g. `/v1/screenings?from=2026-08-05`. */
  readonly path: string;

  constructor(path: string, status: number) {
    super(`Marquise API request failed: GET ${path} returned ${status}`);
    this.name = "HttpMarquiseClientError";
    this.status = status;
    this.path = path;
  }
}

export interface HttpMarquiseClientOptions {
  /** API origin. May be empty to target a same-origin API. */
  baseUrl: string;
  /** Number of upcoming days offered as selectable dates; defaults to 7. */
  horizonDays?: number;
  /** Largest number of screenings fetched for a grid date; defaults to 500. */
  maxScreenings?: number;
  /** Clock used to compute "today"; defaults to `new Date()`. */
  now?: () => Date;
  /** Custom fetch implementation; defaults to the global fetch. */
  fetch?: typeof fetch;
}

const DEFAULT_HORIZON_DAYS = 7;
const DEFAULT_MAX_SCREENINGS = 500;
const SCREENING_PAGE_SIZE = 100;
const MOVIE_BULK_LIMIT = 100;

/** REST API client shared by movie grids and movie detail pages. */
export class HttpMarquiseClient implements MovieGridClient, MovieDetailClient {
  private readonly baseUrl: string;
  private readonly horizonDays: number;
  private readonly maxScreenings: number;
  private readonly now: () => Date;
  private readonly fetchImpl: typeof fetch;
  private cinemaWebsitesPromise: Promise<ReadonlyMap<string, string>> | undefined;

  constructor(options: HttpMarquiseClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.horizonDays = options.horizonDays ?? DEFAULT_HORIZON_DAYS;
    this.maxScreenings = options.maxScreenings ?? DEFAULT_MAX_SCREENINGS;
    this.now = options.now ?? (() => new Date());
    this.fetchImpl = (options.fetch ?? globalThis.fetch).bind(globalThis);
  }

  async listDates(): Promise<readonly string[]>;
  async listDates(movie: MovieCardData): Promise<readonly string[]>;
  async listDates(_movie?: MovieCardData): Promise<readonly string[]> {
    const today = toMontrealIsoDate(this.now());
    return Array.from({ length: this.horizonDays }, (_, day) =>
      addDays(today, day),
    );
  }

  async fetchForDate(date: string): Promise<readonly MovieCardGridItem[]> {
    const screenings = await this.fetchScreeningsForDate(date);
    if (screenings.length === 0) {
      return [];
    }
    const screeningsByMovie = new Map<string, ScreeningApi[]>();
    for (const screening of screenings) {
      const list = screeningsByMovie.get(screening.movie_id) ?? [];
      list.push(screening);
      screeningsByMovie.set(screening.movie_id, list);
    }
    const movieIds = [...screeningsByMovie.keys()];
    const movies = await this.fetchMoviesByIds(movieIds);
    const movieById = new Map(movies.map((movie) => [movie.id, movie]));
    const cinemaLinks = await this.loadCinemaWebsiteLinks();
    return movieIds.map((movieId) =>
      this.toMovieGridItem(
        movieById.get(movieId),
        screeningsByMovie.get(movieId) ?? [],
        cinemaLinks,
      ),
    );
  }

  async fetchMovie(movieId: string): Promise<MovieCardData> {
    let movie: MovieApi;
    try {
      movie = await this.fetchJson<MovieApi>(
        `/v1/movies/${encodeURIComponent(movieId)}`,
      );
    } catch (error) {
      if (error instanceof HttpMarquiseClientError && error.status === 404) {
        throw new MovieNotFoundError(movieId);
      }
      throw error;
    }
    return this.toMovie(movie);
  }

  async fetchShowtimes(
    movie: MovieCardData,
    date: string,
  ): Promise<readonly CinemaShowtime[]> {
    if (movie.id === undefined) {
      return [];
    }
    const screenings = await this.fetchScreeningsForMovieDate(movie.id, date);
    const cinemaLinks = await this.loadCinemaWebsiteLinks();
    return screenings.map((screening) =>
      this.toCinemaShowtime(screening, cinemaLinks),
    );
  }

  private async fetchScreeningsForDate(date: string): Promise<ScreeningApi[]> {
    const { from, to } = montrealDayRange(date);
    return this.fetchScreenings(
      `/v1/screenings?from=${from}&to=${to}`,
      this.maxScreenings,
    );
  }

  private async fetchScreeningsForMovieDate(
    movieId: string,
    date: string,
  ): Promise<ScreeningApi[]> {
    const { from, to } = montrealDayRange(date);
    return this.fetchScreenings(
      `/v1/screenings?movie_id=${encodeURIComponent(movieId)}&from=${from}&to=${to}`,
    );
  }

  private async fetchScreenings(
    query: string,
    limit = Number.POSITIVE_INFINITY,
  ): Promise<ScreeningApi[]> {
    const items: ScreeningApi[] = [];
    let page = 1;
    for (;;) {
      const result = await this.fetchJson<Page<ScreeningApi>>(
        `${query}&page=${page}&size=${SCREENING_PAGE_SIZE}`,
      );
      items.push(...result.items);
      if (
        result.items.length === 0 ||
        items.length >= result.total ||
        items.length >= limit
      ) {
        return items.slice(0, limit);
      }
      page += 1;
    }
  }

  private async fetchMoviesByIds(ids: readonly string[]): Promise<MovieApi[]> {
    const movies: MovieApi[] = [];
    for (let index = 0; index < ids.length; index += MOVIE_BULK_LIMIT) {
      const chunk = ids.slice(index, index + MOVIE_BULK_LIMIT);
      const query = chunk.map((id) => `ids=${encodeURIComponent(id)}`).join("&");
      const result = await this.fetchJson<Page<MovieApi>>(
        `/v1/movies?${query}&size=${MOVIE_BULK_LIMIT}`,
      );
      movies.push(...result.items);
    }
    return movies;
  }

  private async loadCinemaWebsiteLinks(): Promise<ReadonlyMap<string, string>> {
    if (this.cinemaWebsitesPromise !== undefined) {
      return this.cinemaWebsitesPromise;
    }
    const request = this.fetchJson<Page<CinemaApi>>("/v1/cinemas?size=100")
      .then(
        (result) =>
          new Map(
            result.items.flatMap((cinema) =>
              cinema.website === null ? [] : [[cinema.id, cinema.website]],
            ),
          ),
      )
      .catch(() => {
        if (this.cinemaWebsitesPromise === request) {
          this.cinemaWebsitesPromise = undefined;
        }
        return new Map<string, string>();
      });
    this.cinemaWebsitesPromise = request;
    return request;
  }

  private toMovieGridItem(
    movie: MovieApi | undefined,
    screenings: readonly ScreeningApi[],
    cinemaLinks: ReadonlyMap<string, string>,
  ): MovieCardGridItem {
    const movieId = movie?.id ?? screenings[0]?.movie_id;
    return {
      key: movieId,
      movie: movie === undefined
        ? {
            id: movieId,
            title: screenings[0]?.movie_title ?? "Unknown title",
            posterUrl: null,
            releaseYear: null,
            durationMinutes: null,
            directors: null,
            genres: null,
          }
        : this.toMovie(movie),
      showtimesUrl: movieId === undefined
        ? ""
        : `/movies/${encodeURIComponent(movieId)}`,
      showtimes: screenings.map((screening) =>
        this.toCinemaShowtime(screening, cinemaLinks),
      ),
    };
  }

  private toMovie(movie: MovieApi): MovieCardData {
    return {
      id: movie.id,
      title: movie.title,
      posterUrl: movie.poster_url,
      releaseYear: movie.release_year,
      durationMinutes: movie.duration_minutes,
      directors: movie.directors,
      genres: movie.genres,
    };
  }

  private toCinemaShowtime(
    screening: ScreeningApi,
    cinemaLinks: ReadonlyMap<string, string>,
  ): CinemaShowtime {
    return {
      startsAt: screening.showtime,
      ticketUrl: screening.ticket_url,
      language: screening.language,
      cinema: {
        id: screening.cinema_id,
        name: screening.cinema_name,
        link: cinemaLinks.get(screening.cinema_id) ?? null,
      },
    };
  }

  private async fetchJson<T>(path: string): Promise<T> {
    const response = await this.fetchImpl(this.baseUrl + path);
    if (!response.ok) {
      throw new HttpMarquiseClientError(path, response.status);
    }
    return (await response.json()) as T;
  }
}
