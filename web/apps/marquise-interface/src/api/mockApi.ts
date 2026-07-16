import type { PosterMovie, PosterWallFilters } from '@marquise/components';
import { filterMovies } from '@marquise/components';
import { MOVIES } from '../data/movies';

const MIN_LATENCY_MS = 350;
const MAX_LATENCY_MS = 700;

function randomLatency(): number {
  return MIN_LATENCY_MS + Math.random() * (MAX_LATENCY_MS - MIN_LATENCY_MS);
}

/**
 * Stands in for a future real API call — same filtering the real backend
 * would do server-side, plus a simulated network round-trip. This is what
 * `PosterWallPage` awaits, so every filter change (and the initial mount)
 * has a real loading window for the skeleton state to fill.
 */
export function fetchMovies(filters: PosterWallFilters): Promise<PosterMovie[]> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(filterMovies(MOVIES, filters)), randomLatency());
  });
}
