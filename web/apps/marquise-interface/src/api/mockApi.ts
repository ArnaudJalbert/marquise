import type { PosterMovie, PosterWallFilters, Screening } from '@marquise/components';
import type { MovieInfo, CinemaGroup } from '@marquise/components';
import { MOVIES } from '../data/movies';

const MIN_LATENCY_MS = 350;
const MAX_LATENCY_MS = 700;

function randomLatency(): number {
  return MIN_LATENCY_MS + Math.random() * (MAX_LATENCY_MS - MIN_LATENCY_MS);
}

function parseShowtimeHour(time: string): number {
  const match24 = time.match(/^(\d{1,2}):\d{2}$/);
  if (match24) return Number(match24[1]);
  const match12 = time.match(/(\d+):(\d+)\s*(AM|PM)/i);
  if (!match12) return 0;
  let hour = Number(match12[1]) % 12;
  if (/PM/i.test(match12[3])) hour += 12;
  return hour;
}

function slugifyTitle(title: string): string {
  return title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function groupMockScreenings(entries: PosterMovie[]): CinemaGroup[] {
  const cinemaMap = new Map<string, Screening[]>();
  for (const entry of entries) {
    const group = cinemaMap.get(entry.cinema) ?? [];
    for (const s of entry.screenings) {
      group.push({ ...s });
    }
    group.sort((a, b) => parseShowtimeHour(a.time) - parseShowtimeHour(b.time));
    cinemaMap.set(entry.cinema, group);
  }

  const cinemaGroups: CinemaGroup[] = [];
  for (const [cinemaName, screenings] of cinemaMap) {
    cinemaGroups.push({ cinemaName, screenings });
  }
  return cinemaGroups;
}

/**
 * Fetch the full dataset for the selected dates only — no merging or non-date
 * filters applied. Used by PosterWallPage as the cached data source;
 * `filterMovies` in `PosterWallPage` handles merging + client-side filtering.
 */
export function fetchMoviesByDate(filters: PosterWallFilters): Promise<PosterMovie[]> {
  return new Promise((resolve) => {
    const dateSet = new Set(filters.dates);
    const filtered = dateSet.size > 0
      ? MOVIES.filter((m) => m.dates.some((d) => dateSet.has(d)))
      : MOVIES;
    setTimeout(() => resolve(filtered), randomLatency());
  });
}

/** Fetch screenings for a movie grouped by cinema. When `dateKey` is provided, scoped to that day. */
export async function fetchMovieScreenings(movieId: string, dateKey?: string): Promise<CinemaGroup[]> {
  const entries = MOVIES.filter(
    (m) => m.movieId === movieId || slugifyTitle(m.title) === movieId,
  );
  if (entries.length === 0) {
    throw new Error(`Movie not found: ${movieId}`);
  }

  const scoped = dateKey
    ? entries.filter((m) => m.dates.includes(dateKey))
    : entries;

  return groupMockScreenings(scoped);
}

/** Fetch dates a movie has screenings on. When `afterDate` is set, returns
 * only dates strictly greater than `afterDate`. When `limit` is set, returns
 * at most that many results.
 */
export async function fetchMovieDates(movieId: string, afterDate?: string, limit?: number): Promise<string[]> {
  const entries = MOVIES.filter(
    (m) => m.movieId === movieId || slugifyTitle(m.title) === movieId,
  );
  if (entries.length === 0) {
    throw new Error(`Movie not found: ${movieId}`);
  }
  const dateSet = new Set<string>();
  for (const entry of entries) {
    for (const d of entry.dates) {
      dateSet.add(d);
    }
  }
  let sorted = [...dateSet].sort();
  if (afterDate) sorted = sorted.filter((d) => d > afterDate);
  if (limit) sorted = sorted.slice(0, limit);
  return sorted;
}

/** Fetch movie basic info (metadata only, no screenings). */
export async function fetchMovieInfo(movieId: string): Promise<MovieInfo> {
  const entries = MOVIES.filter(
    (m) => m.movieId === movieId || slugifyTitle(m.title) === movieId,
  );

  if (entries.length === 0) {
    throw new Error(`Movie not found: ${movieId}`);
  }

  const first = entries[0];
  return {
    id: movieId,
    title: first.title,
    director: first.director,
    year: first.year,
    runtimeMin: first.runtimeMin,
    genre: first.genre,
    poster: first.poster,
  };
}


