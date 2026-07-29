import { useEffect, useState, useCallback } from 'react';
import { PosterImage } from './PosterImage';
import type { CinemaGroup, MovieInfo } from './detailTypes';
import { ChevronDown, ExternalLink } from 'lucide-react';
import { formatDateLabel, isPastShowtime } from './detailUtils';
import { montrealTodayKey } from './timezone';
import './MovieDetailPage.css';

const BATCH_SIZE = 3;

interface DateGroup {
  dateKey: string;
  cinemaGroups: CinemaGroup[];
}

export interface MovieDetailPageProps {
  movieId: string;
  initialDate?: string;
  onBack?: () => void;
  fetchMovieInfo: (movieId: string) => Promise<MovieInfo>;
  fetchMovieScreenings: (movieId: string, dateKey?: string) => Promise<CinemaGroup[]>;
  fetchMovieDates: (movieId: string, afterDate?: string, limit?: number) => Promise<string[]>;
}

export function MovieDetailPage({ movieId, initialDate, onBack, fetchMovieInfo, fetchMovieScreenings, fetchMovieDates }: MovieDetailPageProps) {
  const today = montrealTodayKey();
  const resolvedInitial = initialDate && initialDate >= today ? initialDate : today;

  const [info, setInfo] = useState<MovieInfo | null>(null);
  const [dateGroups, setDateGroups] = useState<DateGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [allExtraLoaded, setAllExtraLoaded] = useState(false);

  useEffect(() => {
    if (!movieId) return;
    setLoading(true);
    setError(null);
    fetchMovieInfo(movieId)
      .then((movieInfo) => {
        setInfo(movieInfo);
        return fetchMovieScreenings(movieId, resolvedInitial);
      })
      .then((groups) => {
        setDateGroups([{ dateKey: resolvedInitial, cinemaGroups: groups }]);
        setLoading(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to load movie details');
        setLoading(false);
      });
  }, [movieId, resolvedInitial, fetchMovieInfo, fetchMovieScreenings]);

  const handleLoadMore = useCallback(() => {
    if (!movieId || loadingMore) return;
    const lastDate = dateGroups[dateGroups.length - 1]?.dateKey;
    if (!lastDate) return;
    setLoadingMore(true);
    fetchMovieDates(movieId, lastDate, BATCH_SIZE)
      .then(async (dates) => {
        const futureDates = dates.filter((d) => d >= today);
        if (futureDates.length === 0) {
          setAllExtraLoaded(true);
          setLoadingMore(false);
          return;
        }
        const results = await Promise.all(
          futureDates.map((d) => fetchMovieScreenings(movieId, d)),
        );
        setDateGroups((prev) => [
          ...prev,
          ...futureDates.map((d, i) => ({ dateKey: d, cinemaGroups: results[i] })),
        ]);
        if (futureDates.length < BATCH_SIZE) setAllExtraLoaded(true);
        setLoadingMore(false);
      })
      .catch(() => {
        setLoadingMore(false);
      });
  }, [movieId, dateGroups, loadingMore, today, fetchMovieDates, fetchMovieScreenings]);

  if (loading) {
    return (
      <div className="movie-detail-page movie-detail-page--loading">
        <div className="movie-detail-page__skeleton" />
      </div>
    );
  }

  if (error || !info) {
    return (
      <div className="movie-detail-page movie-detail-page--error">
        {onBack && (
          <button className="movie-detail-page__back-btn" onClick={onBack}>
            Back to listings
          </button>
        )}
        <p className="movie-detail-page__error-msg">{error ?? 'Movie not found'}</p>
      </div>
    );
  }

  const metaLine = [info.director, info.year, `${info.runtimeMin} min`].filter(Boolean).join(' · ');

  return (
    <div className="movie-detail-page">
      {onBack && (
        <button className="movie-detail-page__back-btn" onClick={onBack}>
          Back to listings
        </button>
      )}

      <div className="movie-detail-page__hero">
        <div className="movie-detail-page__poster">
          <PosterImage src={info.poster} alt={info.title} />
        </div>
        <div className="movie-detail-page__info">
          <h1 className="movie-detail-page__title">{info.title}</h1>
          <p className="movie-detail-page__meta">{metaLine}</p>
          <div className="movie-detail-page__tags">
            <span className="movie-detail-page__tag">{info.genre}</span>
          </div>
        </div>
      </div>

      <div className="movie-detail-page__date-groups">
        {dateGroups.map((dg) => (
          <div key={dg.dateKey} className="movie-detail-page__date-group">
            <h2 className="movie-detail-page__date-group-label">{formatDateLabel(dg.dateKey)}</h2>
            {dg.cinemaGroups.length === 0 ? (
              <p className="movie-detail-page__empty">No screenings on this date.</p>
            ) : (
              <div className="movie-detail-page__screenings">
                {dg.cinemaGroups.map((group) => (
                  <div key={group.cinemaName} className="movie-detail-page__cinema-group">
                    <h3 className="movie-detail-page__cinema-name">{group.cinemaName}</h3>
                    <div className="movie-detail-page__showtimes">
                      {group.screenings.map((s, i) => (
                        <span key={`${s.time}-${s.lang}-${i}`} className={`movie-detail-page__showtime${isPastShowtime(s) ? ' movie-detail-page__showtime--past' : ''}`}>
                          {s.ticketUrl ? (
                            <a
                              href={s.ticketUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="movie-detail-page__ticket-link"
                            >
                              {s.time}
                              <ExternalLink size={12} className="movie-detail-page__external-icon" />
                            </a>
                          ) : (
                            <span className="movie-detail-page__showtime-time">{s.time}</span>
                          )}
                          <span className="movie-detail-page__showtime-lang">{s.lang}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {!loading && dateGroups.length > 0 && (
        <div className="movie-detail-page__load-area">
          {allExtraLoaded ? (
            <p className="movie-detail-page__dates-end">
              {dateGroups.length > 1 ? 'All future dates loaded' : 'No more upcoming screenings'}
            </p>
          ) : loadingMore ? (
            <div className="movie-detail-page__loading">
              <div className="movie-detail-page__spinner" />
            </div>
          ) : (
            <button className="movie-detail-page__load-more" onClick={handleLoadMore}>
              More dates <ChevronDown size={14} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
