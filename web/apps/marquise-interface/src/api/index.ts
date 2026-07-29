import type { PosterMovie, PosterWallFilters } from '@marquise/components';
import type { CinemaGroup, MovieInfo } from './detailTypes';
import {
  fetchMoviesByDate as fetchMoviesByDateMock,
  fetchMovieDates as fetchMovieDatesMock,
  fetchMovieInfo as fetchMovieInfoMock,
  fetchMovieScreenings as fetchMovieScreeningsMock,
} from './mockApi';
import {
  fetchMoviesByDate as fetchMoviesByDateLive,
  fetchMovieDates as fetchMovieDatesLive,
  fetchMovieInfo as fetchMovieInfoLive,
  fetchMovieScreenings as fetchMovieScreeningsLive,
} from './liveApi';

export type { MovieInfo, CinemaGroup } from './detailTypes';

export const dataSource: 'mock' | 'live' = import.meta.env.VITE_DATA_SOURCE === 'live' ? 'live' : 'mock';

export function fetchMoviesByDate(filters: PosterWallFilters): Promise<PosterMovie[]> {
  return dataSource === 'live' ? fetchMoviesByDateLive(filters) : fetchMoviesByDateMock(filters);
}

export function fetchMovieDates(movieId: string, afterDate?: string, limit?: number): Promise<string[]> {
  return dataSource === 'live' ? fetchMovieDatesLive(movieId, afterDate, limit) : fetchMovieDatesMock(movieId, afterDate, limit);
}

export function fetchMovieInfo(movieId: string): Promise<MovieInfo> {
  return dataSource === 'live' ? fetchMovieInfoLive(movieId) : fetchMovieInfoMock(movieId);
}

export function fetchMovieScreenings(movieId: string, dateKey?: string): Promise<CinemaGroup[]> {
  return dataSource === 'live' ? fetchMovieScreeningsLive(movieId, dateKey) : fetchMovieScreeningsMock(movieId, dateKey);
}
