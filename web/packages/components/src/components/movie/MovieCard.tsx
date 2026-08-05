import { Fragment, useId, useState } from "react";
import { ChevronDown } from "lucide-react";

import { cn } from "../../lib/utils";
import { Card, CardContent } from "../ui/card";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "../ui/hover-card";
import { CinemaShowtimeGroups, groupByCinema, showtimeLinkClasses } from "./CinemaShowtimes";
import { compareByStart, formatDuration, formatTime, isPassed } from "./format";
import { MoviePoster } from "./MoviePoster";
import type { MovieCardProps } from "./movie-card";

/**
 * A standalone, presentational movie card: poster, title, meta and a flat list of
 * showtimes. It receives a single flat list of screenings (each carrying its
 * cinema) and groups them by cinema for the hover popover and inline widget — it
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
  const allShowtimesPanelId = useId();
  const groups = groupByCinema(showtimes);
  const hasShowtimes = groups.length > 0;
  const sortedShowtimes = [...showtimes].sort((a, b) =>
    compareByStart(a.startsAt, b.startsAt),
  );
  const upcomingShowtimes = sortedShowtimes.filter(
    (showtime) => !isPassed(showtime.startsAt, currentTime),
  );
  const visibleShowtimes =
    upcomingShowtimes.length > 0
      ? upcomingShowtimes.slice(0, maxShowtimes)
      : sortedShowtimes;
  const showHoverPopover = hasShowtimes && !allShowtimesOpen;

  const showtimesPanel = (
    <HoverCardContent className="w-72">
      <CinemaShowtimeGroups groups={groups} currentTime={currentTime} />
    </HoverCardContent>
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
    <HoverCard openDelay={hoverOpenDelay}>
      <Card
        style={backgroundColor ? { backgroundColor } : undefined}
        className={cn("gap-0 overflow-hidden rounded-none border-0 p-3", className)}
      >
        {showHoverPopover ? (
          <HoverCardTrigger asChild>{posterElement}</HoverCardTrigger>
        ) : (
          posterElement
        )}
        {hideDetails ? null : (
          <CardContent className="flex flex-col gap-2 border-t border-border px-0 pt-3">
            <div className="flex items-start justify-between gap-2">
              <h3 className="line-clamp-2 font-serif text-lg leading-snug font-medium">
                {showHoverPopover ? (
                  <HoverCardTrigger asChild>{titleElement}</HoverCardTrigger>
                ) : (
                  titleElement
                )}
              </h3>
              {hasShowtimes ? (
                <button
                  type="button"
                  onClick={() => setAllShowtimesOpen((open) => !open)}
                  aria-expanded={allShowtimesOpen}
                  aria-controls={allShowtimesOpen ? allShowtimesPanelId : undefined}
                  aria-label={`All showtimes for ${movie.title}`}
                  className="mt-1 shrink-0 cursor-pointer text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <ChevronDown
                    aria-hidden
                    className={cn(
                      "size-4 transition-transform",
                      allShowtimesOpen && "rotate-180",
                    )}
                  />
                </button>
              ) : null}
            </div>
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
                {visibleShowtimes.length < showtimes.length ? (
                  <button
                    type="button"
                    onClick={() => setAllShowtimesOpen((open) => !open)}
                    aria-expanded={allShowtimesOpen}
                    aria-controls={allShowtimesOpen ? allShowtimesPanelId : undefined}
                    aria-label={`More showtimes for ${movie.title}`}
                    className={cn(showtimeLinkClasses, "font-mono text-sm tabular-nums")}
                  >
                    ...
                  </button>
                ) : null}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">No showtimes yet</p>
            )}
            {allShowtimesOpen && hasShowtimes ? (
              <section id={allShowtimesPanelId} className="border-t pt-3">
                <CinemaShowtimeGroups groups={groups} currentTime={currentTime} />
              </section>
            ) : null}
          </CardContent>
        )}
      </Card>
      {showHoverPopover ? showtimesPanel : null}
    </HoverCard>
  );
}
