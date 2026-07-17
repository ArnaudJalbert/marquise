import type { PosterMovie, PosterWallFilters } from '@marquise/components';
import { fetchMovies as fetchMoviesMock } from './mockApi';
import { fetchMovies as fetchMoviesLive } from './liveApi';

export const dataSource: 'mock' | 'live' = import.meta.env.VITE_DATA_SOURCE === 'live' ? 'live' : 'mock';

/**
 * Picks the mock or live data source per VITE_DATA_SOURCE — see .env / .env.live.
 * `onCardsReady`, when given, is called with card-only data (title/cinema/dates/
 * screenings) as soon as it's available, ahead of the returned promise, which
 * resolves once poster/genre/director/year/runtime enrichment lands too. Only
 * the live source has a meaningful gap between the two; mock data is already
 * fully enriched in one shot.
 */
export function fetchMovies(
  filters: PosterWallFilters,
  onCardsReady?: (movies: PosterMovie[]) => void,
): Promise<PosterMovie[]> {
  return dataSource === 'live' ? fetchMoviesLive(filters, onCardsReady) : fetchMoviesMock(filters);
}
