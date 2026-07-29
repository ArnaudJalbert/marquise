import { MarquiseApiClient } from '@marquise/api-client';
import type { MovieResponse, ScreeningResponse } from '@marquise/api-client';
import type { PosterMovie, PosterWallFilters, Screening } from '@marquise/components';
import { addDaysToDateKey } from '@marquise/components';
import type { MovieInfo, CinemaGroup } from '@marquise/components';
import { montrealDateKeyToUtcRange, montrealTodayKey } from '@marquise/components';

const client = new MarquiseApiClient({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? 'https://marquise-api.fly.dev',
});

const FETCH_PAGE_SIZE = 100;
// Matches the API's cap on ids per /v1/movies/by-ids call.
const MAX_MOVIE_IDS_PER_REQUEST = 100;
// How many days ahead of "today" to pull screenings for when no date filter
// is selected. The backend has thousands of screenings total (past and
// future); querying unbounded and taking the first page returns whatever the
// default sort happens to start at (in practice: the oldest screenings on
// record) — today's real screenings would never show up in that page at all.
const DEFAULT_WINDOW_DAYS_AHEAD = 21;

const SHOWTIME_FORMATTER = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/Toronto',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

const SHOWTIME_DATE_KEY_FORMATTER = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'America/Toronto',
});

/** `showtime` is a real UTC instant — convert to Montreal wall-clock time for display. */
function formatShowtime(iso: string): string {
  return SHOWTIME_FORMATTER.format(new Date(iso));
}

/** The Montreal calendar date a UTC showtime instant falls on (may differ from its UTC date near midnight Eastern). */
function showtimeDateKey(iso: string): string {
  return SHOWTIME_DATE_KEY_FORMATTER.format(new Date(iso));
}

/**
 * Backend `language` is free text (e.g. "V.O.", "French") with no fixed
 * enum — this is a best-effort mapping onto the design system's VO/VF
 * pair, not a guaranteed-correct one.
 */
function mapLanguage(language: string | null): 'VO' | 'VF' {
  if (!language) return 'VO';
  const normalized = language.toLowerCase();
  if (normalized.includes('vf') || normalized.includes('french') || normalized.includes('français')) return 'VF';
  return 'VO';
}

/** Backend genres are free text; take the first one or fall back to a default. */
function mapGenre(genres: string[] | null | undefined): string {
  if (genres && genres.length > 0) {
    return genres[0];
  }
  return 'Drama';
}

function groupIntoPosterMovies(screenings: ScreeningResponse[], moviesById: Map<string, MovieResponse>): PosterMovie[] {
  const groups = new Map<string, PosterMovie>();

  for (const s of screenings) {
    const movie = moviesById.get(s.movie_id);
    const key = `${s.movie_id}::${s.cinema_id}`;
    const day = showtimeDateKey(s.showtime);
    const screening: Screening = { time: formatShowtime(s.showtime), lang: mapLanguage(s.language), ticketUrl: s.ticket_url ?? undefined, showtime: s.showtime };

    const existing = groups.get(key);
    if (existing) {
      existing.screenings.push(screening);
      if (!existing.dates.includes(day)) existing.dates.push(day);
      continue;
    }

    groups.set(key, {
      id: key,
      movieId: s.movie_id,
      title: s.movie_title,
      director: movie?.directors?.[0] ?? 'Unknown',
      year: movie?.release_year ?? 0,
      runtimeMin: movie?.duration_minutes ?? 0,
      genre: mapGenre(movie?.genres),
      cinema: s.cinema_name,
      dates: [day],
      screenings: [screening],
      // An empty-string src on <img> is a browser footgun (triggers a
      // full-page-reload warning) — use a guaranteed-404 placeholder path
      // instead so PosterImage's onError fallback still kicks in normally.
      poster: movie?.poster_url || 'posters/unknown.webp',
    });
  }

  return [...groups.values()];
}

/**
 * The window sent to /v1/screenings. If the user has picked specific dates,
 * bound the query to exactly those dates (so navigating the calendar to a
 * different month actually fetches that month's data, instead of always
 * re-fetching the same fixed today→+21-day window regardless of what was
 * selected). Otherwise default to today (Montreal) → +DEFAULT_WINDOW_DAYS_AHEAD.
 * Bounds are the real UTC instants for the start/end of each Montreal
 * calendar day (see `montrealDateKeyToUtcRange`), not a literal offset-less
 * "Z" suffix on the date key.
 */
function resolveWindow(filters: PosterWallFilters): { from: Date; to: Date } {
  if (filters.dates.length > 0) {
    const sorted = [...filters.dates].sort();
    return {
      from: montrealDateKeyToUtcRange(sorted[0]).from,
      to: montrealDateKeyToUtcRange(sorted[sorted.length - 1]).to,
    };
  }

  const todayKey = montrealTodayKey();
  return {
    from: montrealDateKeyToUtcRange(todayKey).from,
    to: montrealDateKeyToUtcRange(addDaysToDateKey(todayKey, DEFAULT_WINDOW_DAYS_AHEAD)).to,
  };
}

/**
 * Fetch every screening in [from, to], following `/v1/screenings`' pagination
 * (`page`/`pages`) rather than taking only the first `FETCH_PAGE_SIZE` rows.
 * The backend sorts by showtime only (no cinema-aware ordering), so a single
 * page silently truncates lower-volume cinemas (e.g. repertory houses like
 * Cinémathèque québécoise or Cinéma Moderne) once a 21-day window's screening
 * count exceeds one page — they'd be entirely or partially missing with no
 * error, since request-level failures aren't the failure mode here.
 */
async function fetchAllScreenings(from: Date, to: Date): Promise<ScreeningResponse[]> {
  const first = await client.screenings.search({ from, to, size: FETCH_PAGE_SIZE, page: 1 });
  const items = [...first.items];
  for (let page = 2; page <= first.pages; page++) {
    const next = await client.screenings.search({ from, to, size: FETCH_PAGE_SIZE, page });
    items.push(...next.items);
  }
  return items;
}

/**
 * Fetch movies for every id in `movieIds` in as few requests as possible,
 * via `/v1/movies/by-ids` (chunked to the API's per-call id cap). Ids with
 * no matching movie are simply absent from the result map.
 */
async function fetchMoviesByIds(movieIds: string[]): Promise<Map<string, MovieResponse>> {
  const chunks: string[][] = [];
  for (let i = 0; i < movieIds.length; i += MAX_MOVIE_IDS_PER_REQUEST) {
    chunks.push(movieIds.slice(i, i + MAX_MOVIE_IDS_PER_REQUEST));
  }

  const results = await Promise.all(chunks.map((chunk) => client.movies.getByIds(chunk)));
  return new Map(results.flat().map((movie) => [movie.id, movie]));
}

/**
 * Fetch the full enriched dataset for the selected dates only — no non-date
 * filters applied. Used by PosterWallPage as the cached data source;
 * client-side filtering handles search, cinema, genre, lang, and time range.
 */
export function fetchMoviesByDate(filters: PosterWallFilters): Promise<PosterMovie[]> {
  const { from, to } = resolveWindow(filters);

  return fetchAllScreenings(from, to).then(async (screenings) => {
    const movieIds = [...new Set(screenings.map((s) => s.movie_id))];
    const moviesById = await fetchMoviesByIds(movieIds);
    return groupIntoPosterMovies(screenings, moviesById);
  });
}

async function fetchRawMovieScreenings(movieId: string, dateKey?: string): Promise<ScreeningResponse[]> {
  const params: Parameters<typeof client.screenings.search>[0] = { movie_id: movieId, size: FETCH_PAGE_SIZE, page: 1 };
  if (dateKey) {
    const range = montrealDateKeyToUtcRange(dateKey);
    params.from = range.from;
    params.to = range.to;
  }
  const first = await client.screenings.search(params);
  const items = [...first.items];
  for (let page = 2; page <= first.pages; page++) {
    const next = await client.screenings.search({ ...params, page });
    items.push(...next.items);
  }
  return items;
}

function groupScreeningsIntoCinemas(screenings: ScreeningResponse[]): CinemaGroup[] {
  const cinemaMap = new Map<string, Screening[]>();
  for (const s of screenings) {
    const group = cinemaMap.get(s.cinema_name) ?? [];
    group.push({ time: formatShowtime(s.showtime), lang: mapLanguage(s.language), ticketUrl: s.ticket_url ?? undefined, showtime: s.showtime });
    cinemaMap.set(s.cinema_name, group);
  }

  const cinemaGroups: CinemaGroup[] = [];
  for (const [cinemaName, group] of cinemaMap) {
    group.sort((a, b) => {
      const hA = Number(a.time.match(/(\d+)/)?.[1] ?? 0);
      const hB = Number(b.time.match(/(\d+)/)?.[1] ?? 0);
      return hA - hB;
    });
    cinemaGroups.push({ cinemaName, screenings: group });
  }
  return cinemaGroups;
}

/** Fetch screenings for a movie grouped by cinema. When `dateKey` is provided, scoped to that day. */
export async function fetchMovieScreenings(movieId: string, dateKey?: string): Promise<CinemaGroup[]> {
  const raw = await fetchRawMovieScreenings(movieId, dateKey);
  return groupScreeningsIntoCinemas(raw);
}

/** Fetch dates a movie has screenings on. When `afterDate` is set, returns
 * only dates strictly greater than `afterDate`. When `limit` is set, returns
 * at most that many results.
 */
export async function fetchMovieDates(movieId: string, afterDate?: string, limit?: number): Promise<string[]> {
  const screenings = await fetchRawMovieScreenings(movieId);
  const dateSet = new Set<string>();
  for (const s of screenings) {
    dateSet.add(showtimeDateKey(s.showtime));
  }
  let sorted = [...dateSet].sort();
  if (afterDate) sorted = sorted.filter((d) => d > afterDate);
  if (limit) sorted = sorted.slice(0, limit);
  return sorted;
}

/** Fetch movie basic info (metadata only, no screenings). */
export async function fetchMovieInfo(movieId: string): Promise<MovieInfo> {
  const movieRes = await client.movies.get(movieId);
  return {
    id: movieRes.id,
    title: movieRes.title,
    director: movieRes.directors?.[0] ?? 'Unknown',
    year: movieRes.release_year ?? 0,
    runtimeMin: movieRes.duration_minutes ?? 0,
    genre: mapGenre(movieRes.genres),
    poster: movieRes.poster_url || 'posters/unknown.webp',
  };
}


