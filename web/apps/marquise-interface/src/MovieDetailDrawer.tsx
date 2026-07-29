import { useEffect, useState, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { PosterImage } from '@marquise/components';
import type { PosterMovie } from '@marquise/components';
import { X, ExternalLink, ChevronDown } from 'lucide-react';
import { fetchMovieScreenings, fetchMovieDates } from './api';
import type { CinemaGroup } from './api';
import { formatDateLabel } from './detailUtils';
import { montrealTodayKey } from './timezone';
import './MovieDetailDrawer.css';

const BATCH_SIZE = 3;

export interface MovieDetailDrawerProps {
  movie: PosterMovie;
  initialDate?: string;
  onClose: () => void;
}

export function MovieDetailDrawer({ movie, initialDate, onClose }: MovieDetailDrawerProps) {
  const [cinemaGroups, setCinemaGroups] = useState<CinemaGroup[] | null>(null);
  const [loadingScreenings, setLoadingScreenings] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState(initialDate ?? '');
  const [entered, setEntered] = useState(false);
  const [extraDates, setExtraDates] = useState<string[]>([]);
  const [loadingMore, setLoadingMore] = useState(false);
  const [allExtraLoaded, setAllExtraLoaded] = useState(false);
  const today = montrealTodayKey();

  const wallDates = useMemo(() => movie.dates.filter((d) => d >= today), [movie.dates, today]);

  const loadScreenings = useCallback((dateKey: string) => {
    setLoadingScreenings(true);
    setError(null);
    fetchMovieScreenings(movie.movieId, dateKey).then((groups) => {
      setCinemaGroups(groups);
      setLoadingScreenings(false);
    }).catch((err: unknown) => {
      setError(err instanceof Error ? err.message : 'Failed to load screenings');
      setLoadingScreenings(false);
    });
  }, [movie.movieId]);

  useEffect(() => {
    if (selectedDate) loadScreenings(selectedDate);
  }, [selectedDate, loadScreenings]);

  useEffect(() => {
    requestAnimationFrame(() => setEntered(true));
  }, []);

  const handleLoadMore = useCallback(() => {
    if (loadingMore) return;
    const last = extraDates.length > 0
      ? extraDates[extraDates.length - 1]
      : wallDates.length > 0
        ? wallDates[wallDates.length - 1]
        : undefined;
    if (!last && wallDates.length === 0) return;
    setLoadingMore(true);
    fetchMovieDates(movie.movieId, last, BATCH_SIZE).then((batch) => {
      const filtered = batch.filter((d) => d >= today);
      setExtraDates((prev) => [...prev, ...filtered]);
      if (filtered.length < BATCH_SIZE) setAllExtraLoaded(true);
      setLoadingMore(false);
    }).catch(() => {
      setLoadingMore(false);
    });
  }, [movie.movieId, wallDates, extraDates, loadingMore, today]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  }, [onClose]);

  return (
    <div className={`movie-detail-drawer-overlay ${entered ? 'movie-detail-drawer-overlay--visible' : ''}`} onClick={onClose} onKeyDown={handleKeyDown}>
      <div
        className={`movie-detail-drawer ${entered ? 'movie-detail-drawer--open' : ''}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Movie details"
      >
        <div className="movie-detail-drawer__header">
          <Link
            to={`/movie/${movie.movieId}${selectedDate ? `?date=${selectedDate}` : ''}`}
            className="movie-detail-drawer__full-link"
          >
            View full page
          </Link>
          <button className="movie-detail-drawer__close" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <div className="movie-detail-drawer__body">
          <div className="movie-detail-drawer__hero">
            <div className="movie-detail-drawer__poster">
              <PosterImage src={movie.poster} alt={movie.title} />
            </div>
            <div className="movie-detail-drawer__info">
              <h2 className="movie-detail-drawer__title">{movie.title}</h2>
              <p className="movie-detail-drawer__meta">
                {[movie.director, movie.year, `${movie.runtimeMin} min`].filter(Boolean).join(' · ')}
              </p>
              <div className="movie-detail-drawer__tags">
                <span className="movie-detail-drawer__tag">{movie.genre}</span>
              </div>
            </div>
          </div>

          <div className="movie-detail-drawer__dates">
            <div className="movie-detail-drawer__dates-scroll">
              {wallDates.map((d) => (
                <button
                  key={d}
                  className={`movie-detail-drawer__date-pill ${d === selectedDate ? 'movie-detail-drawer__date-pill--active' : ''}`}
                  onClick={() => setSelectedDate(d)}
                >
                  {formatDateLabel(d)}
                </button>
              ))}
            </div>

            {extraDates.length > 0 && (
              <div className="movie-detail-drawer__extra-dates">
                {extraDates.map((d) => (
                  <button
                    key={d}
                    className={`movie-detail-drawer__extra-date ${d === selectedDate ? 'movie-detail-drawer__extra-date--active' : ''}`}
                    onClick={() => setSelectedDate(d)}
                  >
                    {formatDateLabel(d)}
                  </button>
                ))}
              </div>
            )}

            {allExtraLoaded && extraDates.length > 0 ? (
              <p className="movie-detail-drawer__dates-end">All future dates loaded</p>
            ) : allExtraLoaded ? (
              <p className="movie-detail-drawer__dates-end">No more upcoming screenings</p>
            ) : (
              <button
                className="movie-detail-drawer__load-more"
                onClick={handleLoadMore}
                disabled={loadingMore}
              >
                {loadingMore ? 'Loading…' : <>More dates <ChevronDown size={14} /></>}
              </button>
            )}
          </div>

          {loadingScreenings && (
            <div className="movie-detail-drawer__loading">
              <div className="movie-detail-drawer__spinner" />
            </div>
          )}

          {error && (
            <p className="movie-detail-drawer__error">{error}</p>
          )}

          {cinemaGroups && !loadingScreenings && (
            <div className="movie-detail-drawer__screenings">
              {cinemaGroups.length === 0 ? (
                <p className="movie-detail-drawer__empty">No screenings on this date.</p>
              ) : (
                cinemaGroups.map((group) => (
                  <div key={group.cinemaName} className="movie-detail-drawer__cinema-group">
                    <h3 className="movie-detail-drawer__cinema-name">{group.cinemaName}</h3>
                    <div className="movie-detail-drawer__showtimes">
                      {group.screenings.map((s, i) => (
                        <span key={`${s.time}-${s.lang}-${i}`} className="movie-detail-drawer__showtime">
                          {s.ticketUrl ? (
                            <a
                              href={s.ticketUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="movie-detail-drawer__ticket-link"
                            >
                              {s.time}
                              <ExternalLink size={10} className="movie-detail-drawer__external-icon" />
                            </a>
                          ) : (
                            <span className="movie-detail-drawer__showtime-time">{s.time}</span>
                          )}
                          <span className="movie-detail-drawer__showtime-lang">{s.lang}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}