import { Fragment, useState } from "react";
import { ChevronDown, X } from "lucide-react";

import { cn } from "../../lib/utils";
import { Card, CardContent } from "../ui/card";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "../ui/hover-card";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import {
  CinemaShowtimeGroups,
  ShowtimeTime,
  groupByCinema,
} from "./CinemaShowtimes";
import { compareByStart, formatDuration } from "./format";
import { MoviePoster } from "./MoviePoster";
import type { MovieCardProps } from "./movie-card";

/** Presentational movie card with compact and expanded showtimes. */
export function MovieCard({
  movie,
  showtimes = [],
  showtimesUrl,
  maxShowtimes = 3,
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
  const [hoverOpen, setHoverOpen] = useState(false);
  const groups = groupByCinema(showtimes);
  const hasShowtimes = groups.length > 0;
  const visibleShowtimes = [...showtimes]
    .sort((a, b) => compareByStart(a.startsAt, b.startsAt))
    .slice(0, maxShowtimes);

  const titleSize =
    movie.title.length > 40
      ? "text-sm"
      : movie.title.length > 26
        ? "text-base"
        : "text-lg";

  const meta = [
    movie.releaseYear != null ? String(movie.releaseYear) : null,
    movie.durationMinutes != null ? formatDuration(movie.durationMinutes) : null,
  ].filter((part): part is string => part !== null);

  const titleElement = onMovieClick ? (
    <button
      type="button"
      onClick={() => onMovieClick(movie)}
      title={movie.title}
      className="block w-full truncate cursor-pointer hover:underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {movie.title}
    </button>
  ) : (
    <a
      href={showtimesUrl}
      target="_blank"
      rel="noreferrer"
      title={movie.title}
      className="block w-full truncate hover:underline underline-offset-4"
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
    <Popover
      open={allShowtimesOpen}
      onOpenChange={(open) => {
        setAllShowtimesOpen(open);
        if (open) setHoverOpen(false);
      }}
    >
      <Card
        style={backgroundColor ? { backgroundColor } : undefined}
        className={cn("gap-0 overflow-hidden rounded-none border-0 p-3", className)}
      >
        <HoverCard
          open={hoverOpen && !allShowtimesOpen}
          onOpenChange={setHoverOpen}
          openDelay={hoverOpenDelay}
          closeDelay={100}
        >
          <HoverCardTrigger asChild>{posterElement}</HoverCardTrigger>
          {hasShowtimes ? (
            <HoverCardContent
              align="end"
              className="max-h-[calc(100dvh-2rem)] w-72 overflow-y-auto shadow-sm"
            >
              <CinemaShowtimeGroups groups={groups} currentTime={currentTime} />
            </HoverCardContent>
          ) : null}
        </HoverCard>

        <CardContent className="flex flex-col gap-2 border-t border-border px-0 pt-3">
          <div className="relative flex items-start justify-center">
            <h3
              className={cn(
                "w-full min-w-0 px-6 text-center font-serif leading-snug font-medium",
                titleSize,
              )}
            >
              {titleElement}
            </h3>
            {!hideDetails && hasShowtimes ? (
              <PopoverTrigger asChild>
                <button
                  type="button"
                  aria-label={`All showtimes for ${movie.title}`}
                  aria-expanded={allShowtimesOpen}
                  className="absolute top-1 right-0 cursor-pointer text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <ChevronDown
                    aria-hidden
                    className={cn(
                      "size-4 transition-transform",
                      allShowtimesOpen && "rotate-180",
                    )}
                  />
                </button>
              </PopoverTrigger>
            ) : null}
          </div>
          {hideDetails ? null : (
            <>
              {meta.length > 0 ? (
                <p className="text-muted-foreground text-xs">{meta.join(" · ")}</p>
              ) : null}
              {visibleShowtimes.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {visibleShowtimes.map((showtime, index) => {
                    const key = `${showtime.startsAt}-${index}`;
                    return renderShowtime ? (
                      <Fragment key={key}>{renderShowtime(showtime)}</Fragment>
                    ) : (
                      <ShowtimeTime
                        key={key}
                        showtime={showtime}
                        currentTime={currentTime}
                        className="text-xs"
                        onClick={
                          onShowtimeClick
                            ? () => onShowtimeClick(showtime)
                            : undefined
                        }
                      />
                    );
                  })}
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">No showtimes yet</p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <PopoverContent
        role="dialog"
        aria-label={`All showtimes for ${movie.title}`}
        align="end"
        className="max-h-[calc(100dvh-2rem)] w-72 overflow-y-auto border border-border shadow-sm"
      >
        <div className="mb-2 flex items-center justify-between border-b border-border pb-2">
          <span className="text-sm font-semibold">Showtimes</span>
          <button
            type="button"
            onClick={() => setAllShowtimesOpen(false)}
            aria-label={`Close all showtimes for ${movie.title}`}
            className="flex size-6 cursor-pointer items-center justify-center rounded-sm border border-border bg-card text-muted-foreground shadow-sm hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X aria-hidden className="size-4" />
          </button>
        </div>
        <CinemaShowtimeGroups groups={groups} currentTime={currentTime} />
      </PopoverContent>
    </Popover>
  );
}
