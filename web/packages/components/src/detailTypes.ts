import type { Screening } from './types';

export interface CinemaGroup {
  cinemaName: string;
  screenings: Screening[];
}

export interface MovieInfo {
  id: string;
  title: string;
  director: string;
  year: number;
  runtimeMin: number;
  genre: string;
  poster: string;
}
