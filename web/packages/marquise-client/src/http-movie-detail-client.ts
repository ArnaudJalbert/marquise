import type { CinemaShowtime } from "./cinema";
import { HttpMovieGridClientError } from "./http-client";
import type { MovieCardData } from "./movie";
import {
  MovieNotFoundError,
  type MovieDetailClient,
} from "./movie-detail-client";
import { addDays, montrealDayRange, toMontrealIsoDate } from "./montreal-date";
import type { CinemaApi, MovieApi, Page, ScreeningApi } from "./api-types";

const DEFAULT_HORIZON_DAYS = 7;
const SCREENING_PAGE_SIZE = 100;

export interface HttpMovieDetailClientOptions {
  /**
   * API origin, e.g. "https://marquise-api.fly.dev". May be empty to target a
   * same-origin API (e.g. behind a dev-server proxy).
   */
  baseUrl: string;
  /** Number of upcoming days offered as selectable dates; defaults to 7. */
  horizonDays?: number;
  /** Clock used to compute "today"; defaults to `new Date()`. Test seam. */
  now?: () => Date;
  /** Custom fetch implementation; defaults to the global fetch. */
  fetch?: typeof fetch;
}

/**
 * A {@link MovieDetailClient} backed by the Marquise read-only REST API.
 *
 * Dates represent Montréal calendar days. Requests use inclusive UTC instants
 * covering those days. `listDates` runs one range query over the horizon
 * filtered to the movie; each date's showtimes are fetched separately, so only
 * the displayed date hits the network.
 */
export class HttpMovieDetailClient implements MovieDetailClient {
  private readonly baseUrl: string;
  private readonly horizonDays: number;
  private readonly now: () => Date;
  private readonly fetchImpl: typeof fetch;
  private readonly cinemaWebsites = new Map<string, string>();
  private cinemaWebsitesLoaded = false;

  constructor(options: HttpMovieDetailClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.horizonDays = options.horizonDays ?? DEFAULT_HORIZON_DAYS;
    this.now = options.now ?? (() => new Date());
    this.fetchImpl = (options.fetch ?? globalThis.fetch).bind(globalThis);
  }

  async fetchMovie(movieId: string): Promise<MovieCardData> {
    let movie: MovieApi;
    try {
      movie = await this.fetchJson<MovieApi>(
        `/v1/movies/${encodeURIComponent(movieId)}`,
      );
    } catch (error) {
      if (error instanceof HttpMovieGridClientError && error.status === 404) {
        throw new MovieNotFoundError(movieId);
      }
      throw error;
    }
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

  async listDates(movie: MovieCardData): Promise<readonly string[]> {
    if (movie.id === undefined) {
      return [];
    }
    if (this.horizonDays <= 0) {
      return [];
    }
    const today = toMontrealIsoDate(this.now());
    const { to } = montrealDayRange(addDays(today, this.horizonDays - 1));
    const screenings = await this.fetchScreenings(
      movie.id,
      montrealDayRange(today).from,
      to,
    );
    return [
      ...new Set(
        screenings.map((screening) =>
          toMontrealIsoDate(new Date(screening.showtime)),
        ),
      ),
    ].sort();
  }

  async fetchShowtimes(
    movie: MovieCardData,
    date: string,
  ): Promise<readonly CinemaShowtime[]> {
    if (movie.id === undefined) {
      return [];
    }
    const { from, to } = montrealDayRange(date);
    const screenings = await this.fetchScreenings(movie.id, from, to);
    const cinemaLink = await this.loadCinemaWebsiteLinks();
    return screenings.map((screening) => this.toCinemaShowtime(screening, cinemaLink));
  }

  private async fetchScreenings(
    movieId: string,
    from: string,
    to: string,
  ): Promise<ScreeningApi[]> {
    const items: ScreeningApi[] = [];
    let page = 1;
    for (;;) {
      const result = await this.fetchJson<Page<ScreeningApi>>(
        `/v1/screenings?movie_id=${encodeURIComponent(movieId)}&from=${from}&to=${to}&page=${page}&size=${SCREENING_PAGE_SIZE}`,
      );
      items.push(...result.items);
      if (result.items.length === 0 || items.length >= result.total) {
        break;
      }
      page += 1;
    }
    return items;
  }

  /**
   * Resolve cinema ids to their official websites so the cinema name in the
   * UI links somewhere real. Best-effort: a failing cinemas request never
   * fails the showtimes fetch — links fall back to empty.
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
      // The primary screenings data already loaded; links are optional.
    }
    return this.cinemaWebsites;
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
