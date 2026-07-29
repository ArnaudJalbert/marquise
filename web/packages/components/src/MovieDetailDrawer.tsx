import { useEffect, useState, useCallback } from 'react';
import { PosterImage } from './PosterImage';
import type { PosterMovie } from './types';
import type { CinemaGroup } from './detailTypes';
import { X, ExternalLink, ChevronDown } from 'lucide-react';
import { formatDateLabel, isPastShowtime } from './detailUtils';
import { montrealTodayKey } from './timezone';
import './MovieDetailDrawer.css';

const BATCH_SIZE = 3;

interface DateGroup {
  dateKey: string;
  cinemaGroups: CinemaGroup[];
}

export interface MovieDetailDrawerProps {
  movie: PosterMovie;
  initialDate?: string;
  onClose: () => void;
  onViewFullPage?: (movieId: string, date?: string) => void;
  fetchMovieScreenings: (movieId: string, dateKey?: string) => Promise<CinemaGroup[]>;
  fetchMovieDates: (movieId: string, afterDate?: string, limit?: number) => Promise<string[]>;
}

export function MovieDetailDrawer({ movie, initialDate, onClose, onViewFullPage, fetchMovieScreenings, fetchMovieDates }: MovieDetailDrawerProps) {
  const [dateGroups, setDateGroups] = useState<DateGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entered, setEntered] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [allExtraLoaded, setAllExtraLoaded] = useState(false);
  const today = montrealTodayKey();

  useEffect(() => {
    const date = initialDate ?? '';
    if (!date) return;
    setLoading(true);
    fetchMovieScreenings(movie.movieId, date).then((groups) => {
      setDateGroups([{ dateKey: date, cinemaGroups: groups }]);
      setLoading(false);
    }).catch((err: unknown) => {
      setError(err instanceof Error ? err.message : 'Failed to load screenings');
      setLoading(false);
    });
  }, [movie.movieId, initialDate, fetchMovieScreenings]);

  useEffect(() => {
    requestAnimationFrame(() => setEntered(true));
  }, []);

  const handleLoadMore = useCallback(() => {
    if (loadingMore) return;
    const lastDate = dateGroups[dateGroups.length - 1]?.dateKey;
    if (!lastDate) return;
    setLoadingMore(true);
    fetchMovieDates(movie.movieId, lastDate, BATCH_SIZE).then(async (dates) => {
      const futureDates = dates.filter((d) => d >= today);
      if (futureDates.length === 0) {
        setAllExtraLoaded(true);
        setLoadingMore(false);
        return;
      }
      const results = await Promise.all(
        futureDates.map((d) => fetchMovieScreenings(movie.movieId, d)),
      );
      setDateGroups((prev) => [
        ...prev,
        ...futureDates.map((d, i) => ({ dateKey: d, cinemaGroups: results[i] })),
      ]);
      if (futureDates.length < BATCH_SIZE) setAllExtraLoaded(true);
      setLoadingMore(false);
    }).catch(() => {
      setLoadingMore(false);
    });
  }, [movie.movieId, dateGroups, loadingMore, today, fetchMovieDates, fetchMovieScreenings]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  }, [onClose]);

  return (
    <div
      className={`movie-detail-drawer-overlay ${entered ? 'movie-detail-drawer-overlay--visible' : ''}`}
      onClick={onClose}
      onKeyDown={handleKeyDown}
    >
      <div
        className={`movie-detail-drawer ${entered ? 'movie-detail-drawer--open' : ''}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Movie details"
      >
        <div className="movie-detail-drawer__header">
          {onViewFullPage && (
            <button
              className="movie-detail-drawer__full-link"
              onClick={() => onViewFullPage(movie.movieId, initialDate)}
            >
              View full page
            </button>
          )}
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

          {error && <p className="movie-detail-drawer__error">{error}</p>}

          {loading && (
            <div className="movie-detail-drawer__loading">
              <div className="movie-detail-drawer__spinner" />
            </div>
          )}

          <div className="movie-detail-drawer__date-groups">
            {dateGroups.map((dg) => (
              <div key={dg.dateKey} className="movie-detail-drawer__date-group">
                <h3 className="movie-detail-drawer__date-group-label">{formatDateLabel(dg.dateKey)}</h3>
                {dg.cinemaGroups.length === 0 ? (
                  <p className="movie-detail-drawer__empty">No screenings on this date.</p>
                ) : (
                  dg.cinemaGroups.map((group) => (
                    <div key={group.cinemaName} className="movie-detail-drawer__cinema-group">
                      <h4 className="movie-detail-drawer__cinema-name">{group.cinemaName}</h4>
                      <div className="movie-detail-drawer__showtimes">
                        {group.screenings.map((s, i) => (
                          <span key={`${s.time}-${s.lang}-${i}`} className={`movie-detail-drawer__showtime${isPastShowtime(s) ? ' movie-detail-drawer__showtime--past' : ''}`}>
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
            ))}
          </div>

          {!loading && dateGroups.length > 0 && (
            <div className="movie-detail-drawer__load-area">
              {allExtraLoaded ? (
                <p className="movie-detail-drawer__dates-end">
                  {dateGroups.length > 1 ? 'All future dates loaded' : 'No more upcoming screenings'}
                </p>
              ) : loadingMore ? (
                <div className="movie-detail-drawer__loading">
                  <div className="movie-detail-drawer__spinner" />
                </div>
              ) : (
                <button
                  className="movie-detail-drawer__load-more"
                  onClick={handleLoadMore}
                >
                  More dates <ChevronDown size={14} />
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
