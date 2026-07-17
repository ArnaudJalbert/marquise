import { describe, expect, it } from 'vitest';
import { filterMovies } from './filterMovies';
import type { PosterMovie, PosterWallFilters } from './types';

const baseMovie = (overrides: Partial<PosterMovie> = {}): PosterMovie => ({
  id: 'm1',
  title: 'Test Movie',
  director: 'Test Director',
  year: 2026,
  runtimeMin: 120,
  format: 'DCP',
  genre: 'Drama',
  cinema: 'Cinéma A',
  dates: ['2026-07-15'],
  screenings: [{ time: '7:00 PM', lang: 'VO' }],
  poster: 'https://example.com/poster.jpg',
  ...overrides,
});

const defaultFilters: PosterWallFilters = {
  search: '',
  cinemas: [],
  langs: [],
  genres: [],
  dates: [],
  dateMode: 'multiple',
  timeRange: [8, 24],
};

describe('filterMovies', () => {
  it('returns all movies when no filters are active', () => {
    const movies = [baseMovie(), baseMovie({ id: 'm2', title: 'Another Movie' })];
    expect(filterMovies(movies, defaultFilters)).toHaveLength(2);
  });

  it('filters by cinema', () => {
    const movies = [
      baseMovie({ id: 'm1', cinema: 'Cinéma A' }),
      baseMovie({ id: 'm2', cinema: 'Cinéma B' }),
    ];
    const result = filterMovies(movies, { ...defaultFilters, cinemas: ['Cinéma A'] });
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('m1');
  });

  it('filters by genre', () => {
    const movies = [
      baseMovie({ id: 'm1', genre: 'Drama' }),
      baseMovie({ id: 'm2', genre: 'Comedy' }),
    ];
    const result = filterMovies(movies, { ...defaultFilters, genres: ['Comedy'] });
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('m2');
  });

  it('filters by date', () => {
    const movies = [
      baseMovie({ id: 'm1', dates: ['2026-07-15'] }),
      baseMovie({ id: 'm2', dates: ['2026-07-16'] }),
    ];
    const result = filterMovies(movies, { ...defaultFilters, dates: ['2026-07-15'] });
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('m1');
  });

  it('filters by language', () => {
    const movies = [
      baseMovie({ id: 'm1', screenings: [{ time: '7:00 PM', lang: 'VO' }] }),
      baseMovie({ id: 'm2', screenings: [{ time: '7:00 PM', lang: 'VF' }] }),
    ];
    const result = filterMovies(movies, { ...defaultFilters, langs: ['VF'] });
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('m2');
  });

  it('filters by time range', () => {
    const movies = [
      baseMovie({ id: 'm1', screenings: [{ time: '7:00 PM', lang: 'VO' }] }),
      baseMovie({ id: 'm2', screenings: [{ time: '10:00 AM', lang: 'VO' }] }),
    ];
    const result = filterMovies(movies, { ...defaultFilters, timeRange: [12, 24] });
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('m1');
  });

  it('filters by search query across title, director, and cinema', () => {
    const movies = [
      baseMovie({ id: 'm1', title: 'Dune', director: 'Denis Villeneuve', cinema: 'Cinéma A' }),
      baseMovie({ id: 'm2', title: 'The Batman', director: 'Matt Reeves', cinema: 'Cinéma B' }),
    ];
    expect(filterMovies(movies, { ...defaultFilters, search: 'Dune' })).toHaveLength(1);
    expect(filterMovies(movies, { ...defaultFilters, search: 'Villeneuve' })).toHaveLength(1);
    expect(filterMovies(movies, { ...defaultFilters, search: 'Cinéma A' })).toHaveLength(1);
    expect(filterMovies(movies, { ...defaultFilters, search: 'Batman' })).toHaveLength(1);
    expect(filterMovies(movies, { ...defaultFilters, search: 'xyz' })).toHaveLength(0);
  });

  it('merges same-title movies from different cinemas into one entry', () => {
    const movies = [
      baseMovie({ id: 'm1', title: 'Dune', cinema: 'Cinéma A', dates: ['2026-07-15'], screenings: [{ time: '7:00 PM', lang: 'VO' }] }),
      baseMovie({ id: 'm2', title: 'Dune', cinema: 'Cinéma B', dates: ['2026-07-16'], screenings: [{ time: '9:00 PM', lang: 'VO' }] }),
    ];
    const result = filterMovies(movies, defaultFilters);
    expect(result).toHaveLength(1);
    expect(result[0].screenings).toHaveLength(2);
    // Screenings sorted by hour
    expect(result[0].screenings[0].time).toBe('7:00 PM');
    expect(result[0].screenings[1].time).toBe('9:00 PM');
  });

  it('deduplicates screenings after merge', () => {
    const movies = [
      baseMovie({ id: 'm1', title: 'Dune', cinema: 'Cinéma A', screenings: [{ time: '7:00 PM', lang: 'VO' }, { time: '7:00 PM', lang: 'VO' }] }),
    ];
    const result = filterMovies(movies, defaultFilters);
    expect(result).toHaveLength(1);
    expect(result[0].screenings).toHaveLength(1);
  });

  it('drops non-matching screenings per-movie after filtering', () => {
    const movies = [
      baseMovie({
        id: 'm1',
        screenings: [
          { time: '7:00 PM', lang: 'VO' },
          { time: '9:00 PM', lang: 'VF' },
        ],
      }),
    ];
    const result = filterMovies(movies, { ...defaultFilters, langs: ['VF'] });
    expect(result).toHaveLength(1);
    expect(result[0].screenings).toHaveLength(1);
    expect(result[0].screenings[0].lang).toBe('VF');
  });
});
