export type Genre = string;

export type Language = 'VO' | 'VF';

export interface Screening {
  /** 12-hour showtime label, e.g. "7:45 PM". */
  time: string;
  /** Language is a per-showtime attribute — the same movie/cinema can run both VO and VF tracks. */
  lang: Language;
  /** Link to purchase tickets for this screening. */
  ticketUrl?: string;
  /** Full ISO datetime string for date-based filtering. */
  showtime?: string;
}

export interface PosterMovie {
  id: string;
  /** Canonical movie identifier (UUID for live API, slug for mock). */
  movieId: string;
  title: string;
  director: string;
  year: number;
  runtimeMin: number;
  genre: Genre;
  cinema: string;
  /** "YYYY-MM-DD" date strings this movie is screening on. */
  dates: string[];
  screenings: Screening[];
  /** Poster image path/URL. May not resolve — PosterImage falls back to a placeholder. */
  poster: string;
}

export type PosterWallView = 'PW-01' | 'PW-02' | 'PW-03' | 'PW-04';

export interface PosterWallFilters {
  search: string;
  cinemas: string[];
  langs: Language[];
  genres: Genre[];
  /** "YYYY-MM-DD" date strings. */
  dates: string[];
  dateMode: 'single' | 'range';
  timeRange: [number, number];
}
