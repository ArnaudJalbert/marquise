import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import type {
  CinemaShowtime,
  MovieCardData,
  MovieGridClient,
} from "marquise-client";

import { cn } from "../../lib/utils";
import { Button } from "../ui/button";
import { MovieCardGrid } from "./MovieCardGrid";
import { MovieFilterPanel } from "./MovieFilterPanel";
import type { MovieFilters } from "./movie-grid-filter";
import { useMovieFilters } from "./use-movie-filters";

export interface MovieGridControllerProps {
  /** Data source; only date changes ever hit it. */
  client: MovieGridClient;
  /** Date selected on first render, as "YYYY-MM-DD"; defaults to the first available. */
  initialDate?: string;
  /** Local filters selected on first render. */
  initialFilters?: Partial<MovieFilters>;
  /** Reports resolved and user-selected dates. */
  onSelectedDateChange?: (
    date: string,
    reason: "user" | "normalization",
  ) => void;
  /** Reports every local filter-state change, including automatic time resets. */
  onFiltersChange?: (filters: MovieFilters) => void;
  /** Side of the grid the vertical filter panel sits on. */
  side?: "left" | "right";
  /** Forwarded to every movie card: ISO-8601 timestamp treated as "now". */
  currentTime?: string;
  hoverOpenDelay?: number;
  maxShowtimes?: number;
  backgroundColor?: string;
  renderShowtime?: (showtime: CinemaShowtime) => ReactNode;
  onShowtimeClick?: (showtime: CinemaShowtime) => void;
  /** Invoked when a card's poster or title is clicked. */
  onMovieClick?: (movie: MovieCardData) => void;
  pageSize?: number | "auto";
  /** Zero-based grid page selected on first render. */
  initialPageIndex?: number;
  onPageIndexChange?: (
    pageIndex: number,
    reason: "user" | "normalization",
  ) => void;
  /** Starting minimum card width in px for the size slider; defaults to 200. */
  defaultCardSize?: number;
  /** Invoked whenever the card-size slider moves; useful for persistence. */
  onCardSizeChange?: (size: number) => void;
  /** Starts with movie details (title, meta, showtimes) hidden; defaults to shown. */
  defaultHideDetails?: boolean;
  /** Invoked whenever the details visibility toggle changes. */
  onHideDetailsChange?: (hide: boolean) => void;
  className?: string;
  /** Classes for the filter panel wrapper. */
  panelClassName?: string;
  /** Classes for the movie grid. */
  gridClassName?: string;
  /** Extra classes applied to every card. */
  cardClassName?: string;
}

/**
 * A vertical filter panel wired to a {@link MovieCardGrid}. The client is
 * consulted once for the selected date and again only when the date changes;
 * cinema, genre, language and time filters run locally on the fetched data.
 */
export function MovieGridController({
  client,
  initialDate,
  initialFilters,
  onSelectedDateChange,
  onFiltersChange,
  side = "left",
  currentTime,
  hoverOpenDelay,
  maxShowtimes,
  backgroundColor,
  renderShowtime,
  onShowtimeClick,
  onMovieClick,
  pageSize,
  initialPageIndex,
  onPageIndexChange,
  defaultCardSize = 200,
  onCardSizeChange,
  defaultHideDetails = false,
  onHideDetailsChange,
  className,
  panelClassName,
  gridClassName,
  cardClassName,
}: MovieGridControllerProps) {
  const [cardSize, setCardSize] = useState(defaultCardSize);
  const [hideDetails, setHideDetails] = useState(defaultHideDetails);
  const {
    dates,
    selectedDate,
    datesLoading,
    isLoading,
    error,
    retry,
    filters,
    updateFilters,
    selectDate,
    options,
    items,
  } = useMovieFilters(client, initialDate, initialFilters);
  const reportedDateRef = useRef<string | null>(null);

  useEffect(() => {
    if (selectedDate !== null && reportedDateRef.current !== selectedDate) {
      reportedDateRef.current = selectedDate;
      onSelectedDateChange?.(selectedDate, "normalization");
    }
  }, [onSelectedDateChange, selectedDate]);

  useEffect(() => {
    onFiltersChange?.(filters);
  }, [filters, onFiltersChange]);

  const loading = datesLoading || isLoading;

  const handleCardSizeChange = (next: number) => {
    setCardSize(next);
    onCardSizeChange?.(next);
  };

  const handleHideDetailsChange = (next: boolean) => {
    setHideDetails(next);
    onHideDetailsChange?.(next);
  };

  const handleDateChange = (date: string) => {
    reportedDateRef.current = date;
    onSelectedDateChange?.(date, "user");
    selectDate(date);
  };

  return (
    <div
      className={cn(
        "flex flex-col gap-6 md:flex-row",
        side === "right" && "md:flex-row-reverse",
        className,
      )}
    >
      <MovieFilterPanel
        query={filters.query}
        onQueryChange={(query) => updateFilters({ query })}
        dates={dates}
        selectedDate={selectedDate ?? ""}
        onDateChange={handleDateChange}
        cinemas={options.cinemas}
        selectedCinemas={filters.cinemas}
        onCinemasChange={(cinemas) => updateFilters({ cinemas })}
        genres={options.genres}
        selectedGenres={filters.genres}
        onGenresChange={(genres) => updateFilters({ genres })}
        languages={options.languages}
        selectedLanguages={filters.languages}
        onLanguagesChange={(languages) => updateFilters({ languages })}
        timeRange={filters.timeRange}
        onTimeRangeChange={(timeRange) => updateFilters({ timeRange })}
        className={cn("w-full shrink-0 md:w-72", panelClassName)}
      />

      <div className="flex min-w-0 flex-1 flex-col gap-4">
        {error !== null ? (
          <div
            className="flex min-h-48 flex-col items-center justify-center gap-3"
            role="alert"
          >
            <span className="text-sm text-muted-foreground">{error}</span>
            <Button variant="outline" size="sm" onClick={retry}>
              Retry
            </Button>
          </div>
        ) : loading ? (
          <div className="min-h-48 flex flex-col items-center justify-center gap-4" role="status">
            <div className="h-1 w-full max-w-xs overflow-hidden rounded-full bg-muted">
              <div className="animate-loading-bar h-full w-1/3 rounded-full bg-foreground" />
            </div>
            <span aria-live="polite" className="text-sm text-muted-foreground">
              Loading showtimes…
            </span>
          </div>
        ) : items.length === 0 ? (
          <div className="min-h-48 flex items-center justify-center" role="status">
            <span className="text-sm text-muted-foreground">
              No screenings match these filters.
            </span>
          </div>
        ) : (
          <MovieCardGrid
            items={items}
            currentTime={currentTime}
            hoverOpenDelay={hoverOpenDelay}
            maxShowtimes={maxShowtimes}
            backgroundColor={backgroundColor}
            renderShowtime={renderShowtime}
            onShowtimeClick={onShowtimeClick}
            onMovieClick={onMovieClick}
            pageSize={pageSize}
            initialPageIndex={initialPageIndex}
            onPageIndexChange={onPageIndexChange}
            cardSize={pageSize === "auto" ? cardSize : undefined}
            onCardSizeChange={
              pageSize === "auto" ? handleCardSizeChange : undefined
            }
            hideDetails={hideDetails}
            onHideDetailsChange={handleHideDetailsChange}
            cardClassName={cardClassName}
            className={gridClassName}
          />
        )}
      </div>
    </div>
  );
}
