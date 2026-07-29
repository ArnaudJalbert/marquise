import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { PosterImage } from '@marquise/components';
import { ArrowLeft, ChevronDown, ExternalLink } from 'lucide-react';
import { fetchMovieInfo, fetchMovieScreenings, fetchMovieDates } from './api';
import type { MovieInfo, CinemaGroup } from './api';
import { formatDateLabel } from './detailUtils';
import { montrealTodayKey } from './timezone';
import './MovieDetailPage.css';

const BATCH_SIZE = 3;

export function MovieDetailPage() {
  const { movieId } = useParams<{ movieId: string }>();
  const [searchParams] = useSearchParams();
  const initialDate = searchParams.get('date') ?? montrealTodayKey();
  const today = montrealTodayKey();

  const wallDates = useMemo(() => {
    const dates = [initialDate];
    return dates.filter((d) => d >= today);
  }, [initialDate, today]);

  const [info, setInfo] = useState<MovieInfo | null>(null);
  const [cinemaGroups, setCinemaGroups] = useState<CinemaGroup[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingScreenings, setLoadingScreenings] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState(initialDate);
  const [extraDates, setExtraDates] = useState<string[]>([]);
  const [loadingMore, setLoadingMore] = useState(false);
  const [allExtraLoaded, setAllExtraLoaded] = useState(false);
  const fetchedInfoRef = useRef(false);

  useEffect(() => {
    fetchedInfoRef.current = false;
  }, [movieId]);

  useEffect(() => {
    if (!movieId) return;
    const isInitial = !fetchedInfoRef.current;
    if (isInitial) {
      setLoading(true);
    } else {
      setLoadingScreenings(true);
    }
    setError(null);

    const chain = isInitial
      ? fetchMovieInfo(movieId).then((movieInfo) => {
        setInfo(movieInfo);
        fetchedInfoRef.current = true;
      })
      : Promise.resolve();

    chain
      .then(() => fetchMovieScreenings(movieId, selectedDate))
      .then((groups) => {
        setCinemaGroups(groups);
        setLoading(false);
        setLoadingScreenings(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to load movie details');
        setLoading(false);
        setLoadingScreenings(false);
      });
  }, [movieId, selectedDate]);

  const handleLoadMore = useCallback(() => {
    if (!movieId || loadingMore) return;
    const last = extraDates.length > 0
      ? extraDates[extraDates.length - 1]
      : wallDates.length > 0
        ? wallDates[wallDates.length - 1]
        : undefined;
    if (!last && wallDates.length === 0) return;
    setLoadingMore(true);
    fetchMovieDates(movieId, last, BATCH_SIZE).then((batch) => {
      const filtered = batch.filter((d) => d >= today);
      setExtraDates((prev) => [...prev, ...filtered]);
      if (filtered.length < BATCH_SIZE) setAllExtraLoaded(true);
      setLoadingMore(false);
    }).catch(() => {
      setLoadingMore(false);
    });
  }, [movieId, wallDates, extraDates, loadingMore, today]);

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
        <Link to="/" className="movie-detail-page__back-link">
          <ArrowLeft size={16} /> Back to listings
        </Link>
        <p className="movie-detail-page__error-msg">{error ?? 'Movie not found'}</p>
      </div>
    );
  }

  const metaLine = [info.director, info.year, `${info.runtimeMin} min`].filter(Boolean).join(' · ');

  return (
    <div className="movie-detail-page">
      <Link to="/" className="movie-detail-page__back-link">
        <ArrowLeft size={16} /> Back to listings
      </Link>

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

      <div className="movie-detail-page__dates">
        <div className="movie-detail-page__dates-scroll">
          {wallDates.map((d) => (
            <button
              key={d}
              className={`movie-detail-page__date-pill ${d === selectedDate ? 'movie-detail-page__date-pill--active' : ''}`}
              onClick={() => setSelectedDate(d)}
            >
              {formatDateLabel(d)}
            </button>
          ))}
        </div>

        {extraDates.length > 0 && (
          <div className="movie-detail-page__extra-dates">
            {extraDates.map((d) => (
              <button
                key={d}
                className={`movie-detail-page__extra-date ${d === selectedDate ? 'movie-detail-page__extra-date--active' : ''}`}
                onClick={() => setSelectedDate(d)}
              >
                {formatDateLabel(d)}
              </button>
            ))}
          </div>
        )}

        {allExtraLoaded && extraDates.length > 0 ? (
          <p className="movie-detail-page__dates-end">All future dates loaded</p>
        ) : allExtraLoaded ? (
          <p className="movie-detail-page__dates-end">No more upcoming screenings</p>
        ) : (
          <button
            className="movie-detail-page__load-more"
            onClick={handleLoadMore}
            disabled={loadingMore}
          >
            {loadingMore ? 'Loading…' : <>More dates <ChevronDown size={14} /></>}
          </button>
        )}
      </div>

      {loadingScreenings && (
        <div className="movie-detail-page__loading">
          <div className="movie-detail-page__spinner" />
        </div>
      )}

      <div className="movie-detail-page__screenings">
        {cinemaGroups?.length === 0 ? (
          <p className="movie-detail-page__empty">No screenings on this date.</p>
        ) : (
          cinemaGroups?.map((group) => (
            <div key={group.cinemaName} className="movie-detail-page__cinema-group">
              <h2 className="movie-detail-page__cinema-name">{group.cinemaName}</h2>
              <div className="movie-detail-page__showtimes">
                {group.screenings.map((s, i) => (
                  <span key={`${s.time}-${s.lang}-${i}`} className="movie-detail-page__showtime">
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
          ))
        )}
      </div>
    </div>
  );
}