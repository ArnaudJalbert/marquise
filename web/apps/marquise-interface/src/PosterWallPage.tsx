import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FilterBar, PosterWall, filterMovies, montrealTodayKey } from '@marquise/components';
import type { PosterMovie, PosterWallFilters, PosterWallView } from '@marquise/components';
import { MovieDetailDrawer } from './MovieDetailDrawer';
import { fetchMoviesByDate } from './api';
import './PosterWallPage.css';

function createDefaultFilters(): PosterWallFilters {
  return {
    search: '',
    cinemas: [],
    langs: [],
    genres: [],
    dates: [montrealTodayKey()],
    dateMode: 'single',
    timeRange: [new Date().getHours(), 24],
  };
}

const VIEW_LABELS: Record<PosterWallView, string> = {
  'PW-01': 'Caption grid',
  'PW-02': 'Dense wall',
  'PW-03': 'Editorial grid',
  'PW-04': 'Listing hybrid',
};

function deriveFilterOptions(movies: PosterMovie[]): { cinemas: string[]; genres: string[]; languages: string[] } {
  const cinemaSet = new Set<string>();
  const genreSet = new Set<string>();
  const langSet = new Set<string>();
  for (const m of movies) {
    cinemaSet.add(m.cinema);
    genreSet.add(m.genre);
    for (const s of m.screenings) {
      langSet.add(s.lang);
    }
  }
  return {
    cinemas: [...cinemaSet].sort((a, b) => a.localeCompare(b)),
    genres: [...genreSet].sort((a, b) => a.localeCompare(b)),
    languages: [...langSet].sort((a, b) => a.localeCompare(b)),
  };
}

/** Composition root for the poster-wall live prototype: filter bar + wall, wired together. */
export function PosterWallPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<PosterWallFilters>(createDefaultFilters);
  const [view, setView] = useState<PosterWallView>('PW-01');
  const [allMovies, setAllMovies] = useState<PosterMovie[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMovie, setSelectedMovie] = useState<PosterMovie | null>(null);
  const requestId = useRef(0);

  const sortedDates = useMemo(() => [...filters.dates].sort(), [filters.dates]);
  const datesKey = useMemo(() => sortedDates.join(','), [sortedDates]);

  useEffect(() => {
    if (filters.dates.length === 0) return;
    const today = montrealTodayKey();
    const earliest = sortedDates[0];
    const startHour = earliest > today || earliest < today ? 0 : new Date().getHours();
    setFilters((prev) => ({ ...prev, timeRange: [startHour, 24] }));
  }, [sortedDates]);

  useEffect(() => {
    if (!datesKey) return;
    const thisRequest = ++requestId.current;
    setLoading(true);
    fetchMoviesByDate(filters).then((result) => {
      if (thisRequest !== requestId.current) return;
      setAllMovies(result);
      setLoading(false);
    });
  }, [datesKey]);

  const movies = useMemo(() => filterMovies(allMovies, filters), [allMovies, filters]);
  const filterOptions = useMemo(() => deriveFilterOptions(allMovies), [allMovies]);

  return (
    <div className="poster-wall-page">
      <header className="poster-wall-page__header">
        <div className="poster-wall-page__eyebrow-row">
          <span className="poster-wall-page__eyebrow">Marquise</span>
        </div>
        <h1 className="poster-wall-page__title">What's playing in <span className="poster-wall-page__city">Montréal</span></h1>
      </header>

      <FilterBar filters={filters} onFiltersChange={setFilters} view={view} onViewChange={setView} cinemas={filterOptions.cinemas} genres={filterOptions.genres} languages={filterOptions.languages} />

      <div className="poster-wall-page__count">
        {loading ? 'Loading…' : `${movies.length} screening${movies.length === 1 ? '' : 's'} · ${VIEW_LABELS[view]}`}
      </div>

      <div className="poster-wall-page__card">
        {loading ? <div className="poster-wall-page__spinner" /> : (
          <PosterWall view={view} movies={movies} onSelect={(movieId) => {
            const found = movies.find((m) => m.movieId === movieId);
            if (found) setSelectedMovie(found);
          }} />
        )}
      </div>

      {selectedMovie && (
        <MovieDetailDrawer
          movie={selectedMovie}
          initialDate={filters.dates.find((d) => selectedMovie.dates.includes(d)) ?? selectedMovie.dates[0] ?? filters.dates[0]}
          onClose={() => setSelectedMovie(null)}
          onViewFullPage={(movieId, date) => navigate(`/movie/${movieId}${date ? `?date=${date}` : ''}`)}
        />
      )}
    </div>
  );
}
