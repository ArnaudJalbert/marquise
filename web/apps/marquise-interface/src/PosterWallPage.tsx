import { useEffect, useRef, useState } from 'react';
import { FilterBar, PosterWall, PosterWallSkeleton } from '@marquise/components';
import type { PosterMovie, PosterWallFilters, PosterWallView } from '@marquise/components';
import { fetchMovies, dataSource } from './api';
import { montrealTodayKey } from './timezone';
import './PosterWallPage.css';

function createDefaultFilters(): PosterWallFilters {
  return {
    search: '',
    cinemas: [],
    langs: [],
    genres: [],
    // Default to today (Montreal time), not "every date" — matches how a
    // cinema listings page should open (what's playing today), not an
    // unfiltered dump of the whole schedule. The mock fixture is anchored to
    // this same date (see data/movies.ts), so this is never an empty result
    // in mock mode either.
    dates: [montrealTodayKey()],
    dateMode: 'multiple',
    timeRange: [8, 24],
  };
}

const VIEW_LABELS: Record<PosterWallView, string> = {
  'PW-01': 'Caption grid',
  'PW-02': 'Dense wall',
  'PW-03': 'Editorial grid',
  'PW-04': 'Listing hybrid',
};

/** Composition root for the poster-wall live prototype: filter bar + wall, wired together. */
export function PosterWallPage() {
  const [filters, setFilters] = useState<PosterWallFilters>(createDefaultFilters);
  const [view, setView] = useState<PosterWallView>('PW-01');
  const [movies, setMovies] = useState<PosterMovie[]>([]);
  const [loading, setLoading] = useState(true);
  const requestId = useRef(0);

  useEffect(() => {
    const thisRequest = ++requestId.current;
    setLoading(true);
    fetchMovies(filters, (cards) => {
      // Cards (title/cinema/dates/screenings) are ready before poster/genre/
      // director/year enrichment — paint them immediately instead of holding
      // the skeleton up for thumbnails.
      if (thisRequest !== requestId.current) return;
      setMovies(cards);
      setLoading(false);
    }).then((result) => {
      // Ignore stale responses if a newer filter change fired before this one resolved.
      if (thisRequest !== requestId.current) return;
      setMovies(result);
      setLoading(false);
    });
  }, [filters]);

  return (
    <div className="poster-wall-page">
      <header className="poster-wall-page__header">
        <div className="poster-wall-page__eyebrow-row">
          <span className="poster-wall-page__eyebrow">Marquise</span>
          <span className={`poster-wall-page__source-badge poster-wall-page__source-badge--${dataSource}`}>
            {dataSource === 'live' ? 'Live API' : 'Mock data'}
          </span>
        </div>
        <h1 className="poster-wall-page__title">What's playing</h1>
      </header>

      <FilterBar movies={movies} filters={filters} onFiltersChange={setFilters} view={view} onViewChange={setView} />

      <div className="poster-wall-page__count">
        {loading ? 'Loading…' : `${movies.length} screening${movies.length === 1 ? '' : 's'} · ${VIEW_LABELS[view]}`}
      </div>

      <div className="poster-wall-page__card">
        {loading ? <PosterWallSkeleton view={view} /> : <PosterWall view={view} movies={movies} />}
      </div>
    </div>
  );
}
