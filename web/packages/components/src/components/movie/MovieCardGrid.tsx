import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "../../lib/utils";
import { MovieCard } from "./MovieCard";
import type { MovieCardGridItem, MovieCardGridProps } from "./movie-card-grid";

const GRID_GAP = 16;
const MIN_CARD_WIDTH = 200;
const CARD_SIZE_MIN = 150;
const CARD_SIZE_MAX = 320;

/** Layout effects measure the DOM; on the server `useLayoutEffect` warns, so fall back to `useEffect`. */
const useIsomorphicLayoutEffect =
  typeof window === "undefined" ? useEffect : useLayoutEffect;

/** Column count for auto-fit: between 2 and 8, based on container width and the grid gap. */
function columnsForWidth(width: number, cardSize: number, maxColumns: number): number {
  const columnWidth = cardSize + GRID_GAP;
  return Math.min(maxColumns, Math.max(2, Math.floor((width + GRID_GAP) / columnWidth)));
}

/**
 * A responsive grid of movie cards. Each item carries its own movie and
 * showtimes; shared interaction props are forwarded to every card. Cards fill
 * their row height so rows stay aligned.
 *
 * With a numeric `pageSize` the grid slices items into pages; with
 * `pageSize="auto"` it measures its container and pages so the grid always fits
 * inside a bounded-height parent.
 */
export function MovieCardGrid({
  items,
  currentTime,
  hoverOpenDelay,
  maxShowtimes,
  backgroundColor,
  renderShowtime,
  onShowtimeClick,
  onMovieClick,
  pageSize,
  initialPageIndex = 0,
  onPageIndexChange,
  cardSize,
  onCardSizeChange,
  hideDetails,
  onHideDetailsChange,
  className,
  cardClassName,
}: MovieCardGridProps) {
  const autoFit = pageSize === "auto";
  const gridAreaRef = useRef<HTMLDivElement>(null);
  const gridRef = useRef<HTMLUListElement>(null);
  const [dims, setDims] = useState<{ width: number; height: number } | null>(null);
  const [rowHeight, setRowHeight] = useState<number | null>(null);
  const [pageIndex, setPageIndex] = useState(() =>
    Math.max(0, Math.floor(initialPageIndex)),
  );

  useIsomorphicLayoutEffect(() => {
    if (!autoFit) return;
    const gridArea = gridAreaRef.current;
    if (gridArea === null) return;
    const observer = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect === undefined) return;
      setDims({ width: rect.width, height: rect.height });
    });
    observer.observe(gridArea);
    return () => observer.disconnect();
  }, [autoFit]);

  const cardWidth = cardSize ?? MIN_CARD_WIDTH;
  const widthColumns =
    autoFit && dims !== null
      ? columnsForWidth(dims.width, cardWidth, cardSize === undefined ? 6 : 8)
      : null;
  const availableRows =
    autoFit && dims !== null && rowHeight !== null
      ? Math.max(1, Math.floor((dims.height + GRID_GAP) / (rowHeight + GRID_GAP)))
      : null;
  const columns =
    widthColumns !== null && availableRows !== null
      ? Math.min(
          widthColumns,
          Math.max(2, Math.ceil(items.length / availableRows)),
        )
      : widthColumns;
  const effectivePageSize =
    autoFit && columns !== null && availableRows !== null
      ? columns * availableRows
      : autoFit
        ? null
        : pageSize !== undefined
          ? Math.max(1, pageSize)
          : null;
  const hasPagination = effectivePageSize !== null;
  const pageCount = hasPagination
    ? Math.max(1, Math.ceil(items.length / (effectivePageSize as number)))
    : 1;
  const measuring = autoFit && effectivePageSize === null;

  useIsomorphicLayoutEffect(() => {
    if (hasPagination && pageIndex >= pageCount) {
      const normalizedPage = Math.max(0, pageCount - 1);
      setPageIndex(normalizedPage);
      onPageIndexChange?.(normalizedPage, "normalization");
    }
  }, [hasPagination, onPageIndexChange, pageCount, pageIndex]);

  let renderItems: readonly MovieCardGridItem[] = items;
  if (hasPagination) {
    const startIndex = pageIndex * (effectivePageSize as number);
    renderItems = items.slice(startIndex, startIndex + (effectivePageSize as number));
  } else if (measuring) {
    renderItems = items.slice(0, widthColumns ?? 2);
  }

  useIsomorphicLayoutEffect(() => {
    if (!autoFit || dims === null || columns === null) return;
    const grid = gridRef.current;
    if (grid === null) return;
    const heights: number[] = [];
    const rowItems = Math.min(columns, grid.children.length);
    for (let i = 0; i < rowItems; i++) {
      const child = grid.children[i];
      if (child instanceof HTMLElement && child.offsetHeight > 0) {
        heights.push(child.offsetHeight);
      }
    }
    if (heights.length > 0) {
      const measuredHeight = Math.max(...heights);
      setRowHeight((current) =>
        current === measuredHeight ? current : measuredHeight,
      );
    }
  }, [autoFit, columns, dims, hideDetails]);

  const showPagination = hasPagination && pageCount > 1;
  const showCardSizeControl = autoFit && cardSize !== undefined && onCardSizeChange !== undefined;
  const showDetailsControl = hideDetails !== undefined && onHideDetailsChange !== undefined;
  const showControls = showPagination || showCardSizeControl || showDetailsControl;
  const cardSizePct =
    cardSize !== undefined
      ? ((cardSize - CARD_SIZE_MIN) / (CARD_SIZE_MAX - CARD_SIZE_MIN)) * 100
      : 0;

  const grid = (
    <ul
      ref={gridRef}
      aria-label="Movie grid"
      style={
        autoFit
          ? { gridTemplateColumns: `repeat(${columns ?? 2}, minmax(0, 1fr))` }
          : undefined
      }
      className={cn(
        "grid gap-4",
        autoFit ? undefined : "grid-cols-2 md:grid-cols-3 xl:grid-cols-4",
        autoFit ? undefined : className,
      )}
    >
      {renderItems.map((item, index) => {
        const card = (
          <MovieCard
            movie={item.movie}
            showtimes={item.showtimes}
            showtimesUrl={item.showtimesUrl}
            currentTime={currentTime}
            hoverOpenDelay={hoverOpenDelay}
            maxShowtimes={maxShowtimes}
            backgroundColor={backgroundColor}
            renderShowtime={renderShowtime}
            onShowtimeClick={onShowtimeClick}
            onMovieClick={onMovieClick}
            hideDetails={hideDetails}
            className={cn("h-full", cardClassName)}
          />
        );
        return (
          <li
            key={item.key ?? `${item.movie.title}-${index}`}
            className={autoFit ? "flex justify-center" : undefined}
          >
            {autoFit ? (
              <div className="w-full" style={{ maxWidth: `${cardWidth}px` }}>
                {card}
              </div>
            ) : (
              card
            )}
          </li>
        );
      })}
    </ul>
  );

  const controls = showControls ? (
    <div className="movie-grid-controls flex flex-col gap-3 md:grid md:grid-cols-3 md:items-center">
      {showDetailsControl ? (
        <label className="flex w-fit cursor-pointer items-center gap-2 text-sm md:col-start-1 md:justify-self-start">
          <input
            type="checkbox"
            checked={!hideDetails}
            onChange={(event) => onHideDetailsChange?.(!event.target.checked)}
            className="size-4 accent-[var(--foreground)]"
          />
          Show details
        </label>
      ) : null}
      {showPagination ? (
        <div className="flex items-center justify-center gap-2 md:col-start-2">
          <button
            type="button"
            onClick={() => {
              const nextPage = Math.max(0, pageIndex - 1);
              setPageIndex(nextPage);
              onPageIndexChange?.(nextPage, "user");
            }}
            disabled={pageIndex === 0}
            aria-label="Previous page"
            className="flex cursor-pointer items-center justify-center p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-40"
          >
            <ChevronLeft aria-hidden className="size-4" />
          </button>
          <span
            aria-live="polite"
            className="font-mono text-xs text-muted-foreground tabular-nums"
          >
            {pageIndex + 1} / {pageCount}
          </span>
          <button
            type="button"
            onClick={() => {
              const nextPage = Math.min(pageCount - 1, pageIndex + 1);
              setPageIndex(nextPage);
              onPageIndexChange?.(nextPage, "user");
            }}
            disabled={pageIndex >= pageCount - 1}
            aria-label="Next page"
            className="flex cursor-pointer items-center justify-center p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-40"
          >
            <ChevronRight aria-hidden className="size-4" />
          </button>
        </div>
      ) : null}
      {showCardSizeControl ? (
        <div className="flex w-full items-center justify-between gap-3 md:col-start-3 md:w-auto md:justify-self-end">
          <span className="text-sm">Card size</span>
          <div className="card-size-slider relative h-8 w-40 select-none">
            <div className="absolute top-1/2 h-1.5 w-full -translate-y-1/2 rounded-full bg-muted" />
            <div
              className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-foreground"
              style={{ left: 0, width: `${cardSizePct}%` }}
            />
            <input
              type="range"
              min={CARD_SIZE_MIN}
              max={CARD_SIZE_MAX}
              step={10}
              value={cardSize}
              onChange={(event) => onCardSizeChange?.(Number(event.target.value))}
              aria-label="Card size"
              aria-valuetext={`${cardSize} pixels`}
            />
          </div>
        </div>
      ) : null}
    </div>
  ) : null;

  if (autoFit) {
    return (
      <div className={cn("flex h-full w-full flex-col", className)}>
        <div ref={gridAreaRef} className="min-h-0 flex-1">
          {grid}
        </div>
        {controls}
      </div>
    );
  }

  return (
    <>
      {grid}
      {controls}
    </>
  );
}
