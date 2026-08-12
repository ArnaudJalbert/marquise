import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, X } from "lucide-react";

import { cn } from "../../lib/utils";
import { Card, CardContent } from "../ui/card";
import { CinemaShowtimeGroups, groupByCinema, showtimeLinkClasses } from "./CinemaShowtimes";
import { compareByStart, formatDuration, formatTime, isPassed } from "./format";
import { MoviePoster } from "./MoviePoster";
import type { MovieCardProps } from "./movie-card";

type ShowtimesPopoverPosition = {
  left: number;
  top?: number;
  bottom?: number;
};

function overlayPosition(rect: DOMRect, width: number): ShowtimesPopoverPosition {
  const viewportMargin = 16;
  const spaceBelow = window.innerHeight - rect.bottom;
  return {
    left: Math.max(
      viewportMargin,
      Math.min(rect.right - width, window.innerWidth - width - viewportMargin),
    ),
    ...(spaceBelow >= 320
      ? { top: rect.bottom + 8 }
      : { bottom: window.innerHeight - rect.top + 8 }),
  };
}

/**
 * A standalone, presentational movie card: poster, title, meta and a flat list of
 * showtimes. It receives a single flat list of screenings (each carrying its
 * cinema) and groups them by cinema for the hover preview and expanded popover — it
 * never fetches or routes on its own.
 */
export function MovieCard({
  movie,
  showtimes = [],
  showtimesUrl,
  maxShowtimes = 5,
  hoverOpenDelay = 200,
  renderShowtime,
  onShowtimeClick,
  onMovieClick,
  currentTime,
  backgroundColor,
  hideDetails,
  className,
}: MovieCardProps) {
  const [allShowtimesOpen, setAllShowtimesOpen] = useState(false);
  const [showtimesPopoverPosition, setShowtimesPopoverPosition] =
    useState<ShowtimesPopoverPosition | null>(null);
  const [hoverPreviewPosition, setHoverPreviewPosition] =
    useState<ShowtimesPopoverPosition | null>(null);
  const showtimesButtonRef = useRef<HTMLButtonElement>(null);
  const posterAreaRef = useRef<HTMLDivElement>(null);
  const hoverOpenTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hoverCloseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const groups = groupByCinema(showtimes);
  const hasShowtimes = groups.length > 0;
  const sortedShowtimes = [...showtimes].sort((a, b) =>
    compareByStart(a.startsAt, b.startsAt),
  );
  const visibleShowtimes = sortedShowtimes.slice(0, maxShowtimes);

  const clearHoverTimer = (timerRef: typeof hoverOpenTimerRef) => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const closeHoverPreview = () => {
    clearHoverTimer(hoverOpenTimerRef);
    clearHoverTimer(hoverCloseTimerRef);
    setHoverPreviewPosition(null);
  };

  const scheduleHoverPreview = () => {
    if (!hasShowtimes || allShowtimesOpen) return;
    clearHoverTimer(hoverCloseTimerRef);
    clearHoverTimer(hoverOpenTimerRef);
    hoverOpenTimerRef.current = setTimeout(() => {
      const posterArea = posterAreaRef.current;
      if (posterArea !== null) {
        setHoverPreviewPosition(
          overlayPosition(posterArea.getBoundingClientRect(), 288),
        );
      }
    }, hoverOpenDelay);
  };

  const scheduleHoverPreviewClose = () => {
    clearHoverTimer(hoverOpenTimerRef);
    clearHoverTimer(hoverCloseTimerRef);
    hoverCloseTimerRef.current = setTimeout(() => {
      setHoverPreviewPosition(null);
    }, 100);
  };

  const closeAllShowtimes = () => {
    setAllShowtimesOpen(false);
    setShowtimesPopoverPosition(null);
  };

  const openAllShowtimes = () => {
    const button = showtimesButtonRef.current;
    if (button === null) return;
    closeHoverPreview();
    setShowtimesPopoverPosition(overlayPosition(button.getBoundingClientRect(), 288));
    setAllShowtimesOpen(true);
  };

  useEffect(() => {
    if (!allShowtimesOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeAllShowtimes();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [allShowtimesOpen]);

  useEffect(
    () => () => {
      clearHoverTimer(hoverOpenTimerRef);
      clearHoverTimer(hoverCloseTimerRef);
    },
    [],
  );

  const showtimesTrigger = (
    label: string,
    children: ReactNode,
    className: string,
    primary = false,
  ) => (
    <button
      type="button"
      ref={primary ? showtimesButtonRef : undefined}
      onClick={() => (allShowtimesOpen ? closeAllShowtimes() : openAllShowtimes())}
      aria-label={label}
      aria-expanded={allShowtimesOpen}
      className={className}
    >
      {children}
    </button>
  );

  const meta = [
    movie.releaseYear != null ? String(movie.releaseYear) : null,
    movie.durationMinutes != null ? formatDuration(movie.durationMinutes) : null,
    movie.directors && movie.directors.length > 0 ? movie.directors.join(", ") : null,
  ].filter((part): part is string => part !== null);

  const titleElement = onMovieClick ? (
    <button
      type="button"
      onClick={() => onMovieClick(movie)}
      className="cursor-pointer hover:underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {movie.title}
    </button>
  ) : (
    <a
      href={showtimesUrl}
      target="_blank"
      rel="noreferrer"
      className="hover:underline underline-offset-4"
    >
      {movie.title}
    </a>
  );

  const posterElement = onMovieClick ? (
    <MoviePoster
      title={movie.title}
      posterUrl={movie.posterUrl}
      onClick={() => onMovieClick(movie)}
    />
  ) : (
    <MoviePoster title={movie.title} posterUrl={movie.posterUrl} href={showtimesUrl} />
  );

  return (
    <>
      <Card
        style={backgroundColor ? { backgroundColor } : undefined}
        className={cn("gap-0 overflow-hidden rounded-none border-0 p-3", className)}
      >
        <div
          ref={posterAreaRef}
          onPointerEnter={scheduleHoverPreview}
          onPointerLeave={scheduleHoverPreviewClose}
        >
          {posterElement}
        </div>
              <CardContent className="flex flex-col gap-2 border-t border-border px-0 pt-3">
                <div className="relative flex items-start justify-center">
                  <h3 className="line-clamp-2 w-full px-6 text-center font-serif text-lg leading-snug font-medium">
                    {titleElement}
                  </h3>
                  {!hideDetails && hasShowtimes
                    ? showtimesTrigger(
                        `All showtimes for ${movie.title}`,
                        <ChevronDown
                          aria-hidden
                          className={cn(
                            "size-4 transition-transform",
                            allShowtimesOpen && "rotate-180",
                          )}
                        />,
                        "absolute top-1 right-0 cursor-pointer text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                        true,
                      )
                    : null}
                </div>
                {hideDetails ? null : (
                  <>
                    {meta.length > 0 ? (
                      <p className="text-muted-foreground text-xs">{meta.join(" · ")}</p>
                    ) : null}
                    {visibleShowtimes.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {visibleShowtimes.map((showtime, index) => {
                          const key = `${showtime.startsAt}-${index}`;
                          if (renderShowtime) {
                            return <Fragment key={key}>{renderShowtime(showtime)}</Fragment>;
                          }
                          return (
                            <a
                              key={key}
                              href={showtime.ticketUrl}
                              target="_blank"
                              rel="noreferrer"
                              onClick={onShowtimeClick ? () => onShowtimeClick(showtime) : undefined}
                              className={showtimeLinkClasses}
                            >
                              <span
                                className={cn(
                                  "font-mono text-sm tabular-nums",
                                  isPassed(showtime.startsAt, currentTime) &&
                                    "text-muted-foreground line-through",
                                )}
                              >
                                {formatTime(showtime.startsAt)}
                              </span>
                            </a>
                          );
                        })}
                        {visibleShowtimes.length < showtimes.length
                          ? showtimesTrigger(
                              `More showtimes for ${movie.title}`,
                              "...",
                              cn(showtimeLinkClasses, "font-mono text-sm tabular-nums"),
                            )
                          : null}
                      </div>
                    ) : (
                      <p className="text-muted-foreground text-sm">No showtimes yet</p>
                    )}
                  </>
                )}
              </CardContent>
      </Card>
      {allShowtimesOpen &&
      showtimesPopoverPosition !== null &&
      typeof document !== "undefined"
        ? createPortal(
            <>
              <div className="fixed inset-0 z-40" onMouseDown={closeAllShowtimes} />
              <section
                role="dialog"
                aria-modal="false"
                aria-label={`All showtimes for ${movie.title}`}
                onMouseDown={(event) => event.stopPropagation()}
                className="fixed z-50 w-72 border border-border bg-card p-3 text-foreground shadow-sm outline-none"
                style={{
                  left: `${showtimesPopoverPosition.left}px`,
                  top:
                    showtimesPopoverPosition.top === undefined
                      ? undefined
                      : `${showtimesPopoverPosition.top}px`,
                  bottom:
                    showtimesPopoverPosition.bottom === undefined
                      ? undefined
                      : `${showtimesPopoverPosition.bottom}px`,
                  maxHeight: "calc(100dvh - 2rem)",
                }}
              >
          <div className="mb-2 flex items-center justify-between border-b border-border pb-2">
            <span className="text-sm font-semibold">Showtimes</span>
            <button
              type="button"
              onClick={closeAllShowtimes}
              aria-label={`Close all showtimes for ${movie.title}`}
              className="flex size-6 cursor-pointer items-center justify-center rounded-sm border border-border bg-card text-muted-foreground shadow-sm hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <X aria-hidden className="size-4" />
            </button>
          </div>
          <div
            className="overflow-y-auto"
            style={{
              maxHeight: "calc(100dvh - 5.5rem)",
            }}
          >
            <CinemaShowtimeGroups groups={groups} currentTime={currentTime} />
          </div>
              </section>
            </>,
            document.body,
          )
        : null}
      {hoverPreviewPosition !== null &&
      !allShowtimesOpen &&
      typeof document !== "undefined"
        ? createPortal(
            <aside
              onPointerEnter={() => {
                clearHoverTimer(hoverCloseTimerRef);
              }}
              onPointerLeave={scheduleHoverPreviewClose}
              className="fixed z-50 w-72 bg-card px-4 py-3 text-foreground shadow-sm"
              style={{
                left: `${hoverPreviewPosition.left}px`,
                top:
                  hoverPreviewPosition.top === undefined
                    ? undefined
                    : `${hoverPreviewPosition.top}px`,
                bottom:
                  hoverPreviewPosition.bottom === undefined
                    ? undefined
                    : `${hoverPreviewPosition.bottom}px`,
                maxHeight: "calc(100dvh - 2rem)",
                overflowY: "auto",
              }}
            >
              <CinemaShowtimeGroups groups={groups} currentTime={currentTime} />
            </aside>,
            document.body,
          )
        : null}
    </>
  );
}
