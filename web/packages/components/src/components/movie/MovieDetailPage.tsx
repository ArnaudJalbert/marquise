import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

import { cn } from "../../lib/utils";
import { Button } from "../ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { CinemaShowtimeGroups, groupByCinema } from "./CinemaShowtimes";
import { Calendar, formatDateLabel } from "./date-selector";
import { formatDuration } from "./format";
import { MoviePoster } from "./MoviePoster";
import type { CinemaShowtime } from "./cinema";
import type { MovieCardData } from "./movie";
import type { MovieDetailClient } from "./movie-detail-client";

/** Width of one date column, in px. The number of visible columns adapts to the container width. */
const COLUMN_WIDTH = 288;

/** Layout effects measure the DOM; on the server `useLayoutEffect` warns, so fall back to `useEffect`. */
const useIsomorphicLayoutEffect =
  typeof window === "undefined" ? useEffect : useLayoutEffect;

function DateColumn({
  date,
  showtimes,
  isPending,
  hasError,
  currentTime,
}: {
  date: string;
  showtimes: readonly CinemaShowtime[] | undefined;
  isPending: boolean;
  hasError: boolean;
  currentTime?: string;
}) {
  const groups = showtimes === undefined ? [] : groupByCinema(showtimes);
  return (
    <div className="flex h-full flex-col gap-3 border-l border-border pl-4">
      <h3 className="text-sm font-semibold">{formatDateLabel(date)}</h3>
      {showtimes === undefined ? (
        isPending ? (
          <div className="flex flex-col gap-2" role="status">
            <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
              <div className="animate-loading-bar h-full w-1/3 rounded-full bg-foreground" />
            </div>
            <span className="text-xs text-muted-foreground">
              Loading showtimes…
            </span>
          </div>
        ) : hasError ? (
          <p className="text-sm text-muted-foreground">Couldn't load showtimes.</p>
        ) : null
      ) : groups.length === 0 ? (
        <p className="text-sm text-muted-foreground">No screenings.</p>
      ) : (
        <CinemaShowtimeGroups groups={groups} currentTime={currentTime} />
      )}
    </div>
  );
}

function JumpToDate({
  dates,
  selectedDate,
  onSelect,
}: {
  dates: readonly string[];
  selectedDate: string;
  onSelect: (date: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="Jump to a date"
          className="flex cursor-pointer items-center justify-center p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <CalendarDays aria-hidden className="size-4" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72">
        <Calendar
          dates={dates}
          selectedDate={selectedDate}
          initialMonth={selectedDate}
          onSelect={(date) => {
            onSelect(date);
            setOpen(false);
          }}
        />
      </PopoverContent>
    </Popover>
  );
}

export interface MovieDetailPageProps {
  movie: MovieCardData;
  /** Data source; showtimes are fetched per date as each column comes into view. */
  client: MovieDetailClient;
  /** Date shown first, as "YYYY-MM-DD"; defaults to the first available. */
  initialDate?: string;
  /** ISO-8601 timestamp treated as "now"; started showtimes are crossed out. */
  currentTime?: string;
  /** When set, renders a back button. */
  onBack?: () => void;
  className?: string;
}

/**
 * A movie detail page: poster, title and meta up top, then the movie's
 * showtimes laid out as one column per date. Columns slide left/right with the
 * arrows; the number of visible columns adapts to the container width, and each
 * date's showtimes are fetched only as its column scrolls into view.
 *
 * Both `movie` and `client` must stay referentially stable across renders
 * (pass state or memoized values). A changed `movie` reference resets the page
 * and refetches everything for the new movie; a changed `client` reference is
 * read through a ref and does not refetch.
 */
export function MovieDetailPage({
  movie,
  client,
  initialDate,
  currentTime,
  onBack,
  className,
}: MovieDetailPageProps) {
  const [dates, setDates] = useState<string[]>([]);
  const [datesLoading, setDatesLoading] = useState(true);
  const [datesError, setDatesError] = useState<string | null>(null);
  const [cache, setCache] = useState<Map<string, CinemaShowtime[]>>(new Map());
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [errorDates, setErrorDates] = useState<Set<string>>(new Set());
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [datesRetryNonce, setDatesRetryNonce] = useState(0);
  const [fetchRetryNonce, setFetchRetryNonce] = useState(0);
  const requestedRef = useRef<Set<string>>(new Set());
  const [offset, setOffset] = useState(0);
  const [viewportWidth, setViewportWidth] = useState<number | null>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const clientRef = useRef(client);
  const movieRef = useRef(movie);

  useEffect(() => {
    clientRef.current = client;
  });

  useIsomorphicLayoutEffect(() => {
    if (movieRef.current === movie) {
      return;
    }
    movieRef.current = movie;
    setDates([]);
    setDatesLoading(true);
    setDatesError(null);
    setCache(new Map());
    setPending(new Set());
    setErrorDates(new Set());
    setFetchError(null);
    requestedRef.current = new Set();
    setOffset(0);
  }, [movie]);

  useEffect(() => {
    let stale = false;
    setDatesLoading(true);
    setDatesError(null);
    clientRef.current
      .listDates(movie)
      .then((available) => {
        if (stale) {
          return;
        }
        const sorted = [...available].sort();
        setDates(sorted);
        setDatesLoading(false);
        const index = initialDate !== undefined ? sorted.indexOf(initialDate) : 0;
        setOffset(Math.max(0, index));
      })
      .catch(() => {
        if (stale) {
          return;
        }
        setDatesLoading(false);
        setDatesError("Could not load the movie's screening dates.");
      });
    return () => {
      stale = true;
    };
  }, [movie, initialDate, datesRetryNonce]);

  const stripReady = !datesLoading && dates.length > 0;

  useIsomorphicLayoutEffect(() => {
    if (!stripReady) {
      return;
    }
    const viewport = viewportRef.current;
    if (viewport === null) {
      return;
    }
    const observer = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect !== undefined) {
        setViewportWidth(rect.width);
      }
    });
    observer.observe(viewport);
    return () => observer.disconnect();
  }, [stripReady]);

  const columnWidth =
    viewportWidth === null ? COLUMN_WIDTH : Math.min(COLUMN_WIDTH, viewportWidth);
  const visibleCount =
    viewportWidth === null
      ? 1
      : Math.max(1, Math.floor(viewportWidth / columnWidth));
  const maxOffset = Math.max(0, dates.length - visibleCount);
  const safeOffset = Math.min(offset, maxOffset);

  useEffect(() => {
    setOffset((current) => Math.min(current, maxOffset));
  }, [maxOffset]);

  useEffect(() => {
    const start = Math.max(0, safeOffset);
    const end = Math.min(dates.length, safeOffset + visibleCount + 1);
    for (let index = start; index < end; index++) {
      const date = dates[index];
      if (date === undefined || requestedRef.current.has(date)) {
        continue;
      }
      requestedRef.current.add(date);
      setPending((current) => new Set(current).add(date));
      clientRef.current
        .fetchShowtimes(movie, date)
        .then((showtimes) => {
          if (movieRef.current !== movie) {
            return;
          }
          setCache((current) => new Map(current).set(date, [...showtimes]));
          setErrorDates((current) => {
            if (!current.has(date)) {
              return current;
            }
            const next = new Set(current);
            next.delete(date);
            return next;
          });
          setPending((current) => {
            const next = new Set(current);
            next.delete(date);
            return next;
          });
          setFetchError(null);
        })
        .catch(() => {
          if (movieRef.current !== movie) {
            return;
          }
          requestedRef.current.delete(date);
          setPending((current) => {
            const next = new Set(current);
            next.delete(date);
            return next;
          });
          setErrorDates((current) => new Set(current).add(date));
          setFetchError(`Could not load showtimes for ${formatDateLabel(date)}.`);
        });
    }
  }, [movie, dates, safeOffset, visibleCount, fetchRetryNonce]);

  const retry = () => {
    setFetchError(null);
    setErrorDates(new Set());
    setFetchRetryNonce((nonce) => nonce + 1);
  };

  const retryDates = () => {
    setDatesError(null);
    setDatesRetryNonce((nonce) => nonce + 1);
  };

  const meta = [
    movie.releaseYear != null ? String(movie.releaseYear) : null,
    movie.durationMinutes != null ? formatDuration(movie.durationMinutes) : null,
    movie.directors && movie.directors.length > 0 ? movie.directors.join(", ") : null,
    movie.genres && movie.genres.length > 0 ? movie.genres.join(", ") : null,
  ].filter((part): part is string => part !== null);

  const selectedDate = dates[safeOffset] ?? dates[0] ?? "";

  const showtimesColumns = (
    <div className="flex items-stretch gap-1">
      <button
        type="button"
        aria-label="Earlier dates"
        disabled={safeOffset === 0}
        onClick={() => setOffset(Math.max(0, safeOffset - 1))}
        className="flex cursor-pointer items-center justify-center p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-40"
      >
        <ChevronLeft aria-hidden className="size-4" />
      </button>
      <div ref={viewportRef} className="min-w-0 flex-1 overflow-hidden">
        <div
          className="flex"
          style={{
            transform: `translateX(${-safeOffset * columnWidth}px)`,
            transition: "transform 300ms ease",
          }}
        >
          {dates.map((date) => (
            <div key={date} className="shrink-0" style={{ width: columnWidth }}>
              <DateColumn
                date={date}
                showtimes={cache.get(date)}
                isPending={pending.has(date)}
                hasError={errorDates.has(date)}
                currentTime={currentTime}
              />
            </div>
          ))}
        </div>
      </div>
      <button
        type="button"
        aria-label="Later dates"
        disabled={safeOffset >= maxOffset}
        onClick={() => setOffset(Math.min(maxOffset, safeOffset + 1))}
        className="flex cursor-pointer items-center justify-center p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-40"
      >
        <ChevronRight aria-hidden className="size-4" />
      </button>
    </div>
  );

  return (
    <div className={cn("flex flex-col gap-6", className)}>
      {onBack ? (
        <button
          type="button"
          onClick={onBack}
          className="flex w-fit cursor-pointer items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground hover:underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ArrowLeft aria-hidden className="size-4" />
          Back to listings
        </button>
      ) : null}

      <header className="flex gap-6">
        <MoviePoster
          title={movie.title}
          posterUrl={movie.posterUrl}
          className="w-40 shrink-0 md:w-48"
        />
        <div className="flex min-w-0 flex-col gap-3">
          <h1 className="font-serif text-3xl leading-tight font-medium">
            {movie.title}
          </h1>
          {meta.length > 0 ? (
            <p className="text-muted-foreground text-sm">{meta.join(" · ")}</p>
          ) : null}
        </div>
      </header>

      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold tracking-wider text-muted-foreground uppercase">
            Showtimes
          </h2>
          {dates.length > 0 ? (
            <JumpToDate
              dates={dates}
              selectedDate={selectedDate}
              onSelect={(date) => {
                const index = dates.indexOf(date);
                if (index !== -1) {
                  setOffset(Math.min(index, maxOffset));
                }
              }}
            />
          ) : null}
        </div>

        {datesError !== null ? (
          <div
            className="flex min-h-32 flex-col items-center justify-center gap-3"
            role="alert"
          >
            <span className="text-sm text-muted-foreground">{datesError}</span>
            <Button variant="outline" size="sm" onClick={retryDates}>
              Retry
            </Button>
          </div>
        ) : (
          <>
            {fetchError !== null ? (
              <div
                className="flex flex-col items-center justify-center gap-3"
                role="alert"
              >
                <span className="text-sm text-muted-foreground">{fetchError}</span>
                <Button variant="outline" size="sm" onClick={retry}>
                  Retry
                </Button>
              </div>
            ) : null}
            {datesLoading ? (
              <div
                role="status"
                className="flex min-h-32 flex-col items-center justify-center gap-4"
              >
                <div className="h-1 w-full max-w-xs overflow-hidden rounded-full bg-muted">
                  <div className="animate-loading-bar h-full w-1/3 rounded-full bg-foreground" />
                </div>
                <span aria-live="polite" className="text-sm text-muted-foreground">
                  Loading showtimes…
                </span>
              </div>
            ) : dates.length === 0 ? (
              <p role="status" className="text-sm text-muted-foreground">
                No screenings scheduled.
              </p>
            ) : (
              showtimesColumns
            )}
          </>
        )}
      </section>
    </div>
  );
}
