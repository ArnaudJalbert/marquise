import type { CinemaShowtime } from "./cinema";
import type { MovieCardGridItem, MovieGridClient } from "./movie-grid-client";

import type { CinemaApi, MovieApi, Page, ScreeningApi } from "./api-types";

/** Thrown when a request to the REST API fails with a non-2xx status. */
export class HttpMovieGridClientError extends Error {
  /** The HTTP status code returned by the API. */
  readonly status: number;
  /** The request path, e.g. `/v1/screenings?from=2026-08-05`. */
  readonly path: string;

  constructor(path: string, status: number) {
    super(`Marquise API request failed: GET ${path} returned ${status}`);
    this.name = "HttpMovieGridClientError";
    this.status = status;
    this.path = path;
  }
}

export interface HttpMovieGridClientOptions {
  /** API origin, e.g. "https://marquise-api.fly.dev". */
  baseUrl: string;
  /** Number of upcoming days offered as selectable dates; defaults to 7. */
  horizonDays?: number;
  /** Largest number of screenings fetched for a single date; defaults to 500. */
  maxScreenings?: number;
  /** Clock used to compute "today"; defaults to `new Date()`. Test seam. */
  now?: () => Date;
  /** Custom fetch implementation; defaults to the global fetch. */
  fetch?: typeof fetch;
}

const DEFAULT_HORIZON_DAYS = 7;
const DEFAULT_MAX_SCREENINGS = 500;
const SCREENING_PAGE_SIZE = 100;
const MOVIE_BULK_LIMIT = 100;

/**
 * A {@link MovieGridClient} backed by the Marquise read-only REST API.
 *
 * Dates are expressed in UTC, which matches the API's own date filtering —
 * `GET /v1/screenings?from=&to=` resolves dates to midnight UTC.
 */
export class HttpMovieGridClient implements MovieGridClient {
  private readonly baseUrl: string;
  private readonly horizonDays: number;
  private readonly maxScreenings: number;
  private readonly now: () => Date;
  private readonly fetchImpl: typeof fetch;
  private readonly cinemaWebsites = new Map<string, string>();
  private cinemaWebsitesLoaded = false;

  constructor(options: HttpMovieGridClientOptions) {
    if (options.baseUrl.trim() === "") {
      throw new Error("baseUrl must not be empty");
    }
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.horizonDays = options.horizonDays ?? DEFAULT_HORIZON_DAYS;
    this.maxScreenings = options.maxScreenings ?? DEFAULT_MAX_SCREENINGS;
    this.now = options.now ?? (() => new Date());
    this.fetchImpl = (options.fetch ?? globalThis.fetch).bind(globalThis);
  }

  async listDates(): Promise<readonly string[]> {
    const today = toUtcDateString(this.now());
    const dates: string[] = [];
    for (let day = 0; day < this.horizonDays; day++) {
      const date = addUtcDays(today, day);
      const page = await this.fetchJson<Page<ScreeningApi>>(
        `/v1/screenings?from=${date}&to=${date}&size=1`,
      );
      if (page.total > 0) {
        dates.push(date);
      }
    }
    return dates;
  }

  async fetchForDate(date: string): Promise<readonly MovieCardGridItem[]> {
    const screenings = await this.fetchScreeningsForDate(date);
    const screeningsByMovie = new Map<string, ScreeningApi[]>();
    for (const screening of screenings) {
      const list = screeningsByMovie.get(screening.movie_id) ?? [];
      list.push(screening);
      screeningsByMovie.set(screening.movie_id, list);
    }
    const movieIds = [...screeningsByMovie.keys()];
    const movies = await this.fetchMoviesByIds(movieIds);
    const movieById = new Map(movies.map((movie) => [movie.id, movie]));
    const cinemaLink = await this.loadCinemaWebsiteLinks();
    return movieIds.map((movieId) => {
      const movie = movieById.get(movieId);
      const movieScreenings = screeningsByMovie.get(movieId) ?? [];
      return this.toMovieGridItem(movie, movieScreenings, cinemaLink);
    });
  }

  private async fetchScreeningsForDate(date: string): Promise<ScreeningApi[]> {
    const items: ScreeningApi[] = [];
    let page = 1;
    for (;;) {
      const result = await this.fetchJson<Page<ScreeningApi>>(
        `/v1/screenings?from=${date}&to=${date}&page=${page}&size=${SCREENING_PAGE_SIZE}`,
      );
      items.push(...result.items);
      if (
        result.items.length === 0 ||
        items.length >= result.total ||
        items.length >= this.maxScreenings
      ) {
        break;
      }
      page += 1;
    }
    return items.slice(0, this.maxScreenings);
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

  /**
   * Resolve cinema ids to their official websites so the cinema name in the
   * UI links somewhere real. Best-effort: a failing cinemas request never
   * fails the movie fetch — links fall back to empty.
   */
  private async loadCinemaWebsiteLinks(): Promise<ReadonlyMap<string, string>> {
    if (this.cinemaWebsitesLoaded) {
      return this.cinemaWebsites;
    }
    this.cinemaWebsitesLoaded = true;
    try {
      const result = await this.fetchJson<Page<CinemaApi>>("/v1/cinemas?size=100");
      for (const cinema of result.items) {
        if (cinema.website) {
          this.cinemaWebsites.set(cinema.id, cinema.website);
        }
      }
    } catch {
      // The primary screenings/movies data already loaded; links are optional.
    }
    return this.cinemaWebsites;
  }

  private toMovieGridItem(
    movie: MovieApi | undefined,
    screenings: readonly ScreeningApi[],
    cinemaLink: ReadonlyMap<string, string>,
  ): MovieCardGridItem {
    return {
      key: movie?.id,
      movie: {
        title: movie?.title ?? screenings[0]?.movie_title ?? "Unknown title",
        posterUrl: movie?.poster_url ?? null,
        releaseYear: movie?.release_year ?? null,
        durationMinutes: movie?.duration_minutes ?? null,
        directors: movie?.directors ?? null,
        genres: movie?.genres ?? null,
      },
      showtimesUrl: "#",
      showtimes: screenings.map((screening) =>
        this.toCinemaShowtime(screening, cinemaLink),
      ),
    };
  }

  private toCinemaShowtime(
    screening: ScreeningApi,
    cinemaLink: ReadonlyMap<string, string>,
  ): CinemaShowtime {
    return {
      startsAt: screening.showtime,
      ticketUrl: screening.ticket_url ?? "#",
      language: screening.language,
      cinema: {
        id: screening.cinema_id,
        name: screening.cinema_name,
        link: cinemaLink.get(screening.cinema_id) ?? "",
      },
    };
  }

  private async fetchJson<T>(path: string): Promise<T> {
    const response = await this.fetchImpl(this.baseUrl + path);
    if (!response.ok) {
      throw new HttpMovieGridClientError(path, response.status);
    }
    return (await response.json()) as T;
  }
}

function toUtcDateString(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function addUtcDays(date: string, days: number): string {
  const parts = date.split("-").map(Number);
  const value = new Date(
    Date.UTC(parts[0] ?? 0, (parts[1] ?? 1) - 1, (parts[2] ?? 1) + days),
  );
  return value.toISOString().slice(0, 10);
}
