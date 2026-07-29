import type { PosterMovie, PosterWallFilters, Screening } from './types';

function parseShowtimeHour(time: string): number {
  const match24 = time.match(/^(\d{1,2}):\d{2}$/);
  if (match24) return Number(match24[1]);
  const match12 = time.match(/(\d+):(\d+)\s*(AM|PM)/i);
  if (!match12) return 0;
  let hour = Number(match12[1]) % 12;
  if (/PM/i.test(match12[3])) hour += 12;
  return hour;
}

function mergeByTitle(movies: PosterMovie[]): PosterMovie[] {
  const merged = new Map<string, PosterMovie>();

  for (const movie of movies) {
    const key = movie.title.trim().toLowerCase();
    const existing = merged.get(key);
    if (!existing) {
      merged.set(key, { ...movie, dates: [...movie.dates], screenings: [...movie.screenings] });
      continue;
    }
    for (const date of movie.dates) {
      if (!existing.dates.includes(date)) existing.dates.push(date);
    }
    existing.screenings.push(...movie.screenings);
  }

  const screeningKey = (s: Screening) => `${s.time}|${s.lang}`;
  for (const movie of merged.values()) {
    const seen = new Set<string>();
    const deduped: Screening[] = [];
    for (const s of movie.screenings) {
      const key = screeningKey(s);
      if (seen.has(key)) continue;
      seen.add(key);
      deduped.push(s);
    }
    movie.screenings = deduped.sort((a, b) => parseShowtimeHour(a.time) - parseShowtimeHour(b.time));
    movie.dates.sort();
  }

  return [...merged.values()];
}

export function filterMovies(movies: PosterMovie[], filters: PosterWallFilters): PosterMovie[] {
  const query = filters.search.trim().toLowerCase();

  const [start, end] = filters.timeRange;
  const matchesScreening = (s: Screening) => {
    if (filters.langs.length > 0 && !filters.langs.includes(s.lang)) return false;
    const hour = parseShowtimeHour(s.time);
    return hour >= start && hour <= end;
  };

  const filtered = movies
    .filter((movie) => {
      if (filters.cinemas.length > 0 && !filters.cinemas.includes(movie.cinema)) return false;
      if (filters.genres.length > 0 && !filters.genres.includes(movie.genre)) return false;
      if (filters.dates.length > 0 && !movie.dates.some((d) => filters.dates.includes(d))) return false;

      if (!movie.screenings.some(matchesScreening)) return false;

      if (query) {
        const haystack = [movie.title, movie.director, movie.cinema].join(' ').toLowerCase();
        if (!haystack.includes(query)) return false;
      }

      return true;
    })
    .map((movie) => ({ ...movie, screenings: movie.screenings.filter(matchesScreening) }));

  return mergeByTitle(filtered);
}
