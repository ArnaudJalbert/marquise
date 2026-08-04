import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "../../lib/utils";
import { MovieCard } from "./MovieCard";
import type { MovieCardGridItem, MovieCardGridProps } from "./movie-card-grid";

const GRID_GAP = 16;
const MIN_CARD_WIDTH = 200;

/** Layout effects measure the DOM; on the server `useLayoutEffect` warns, so fall back to `useEffect`. */
const useIsomorphicLayoutEffect =
  typeof window === "undefined" ? useEffect : useLayoutEffect;

/** Column count for auto-fit: between 2 and 4, based on container width and the grid gap. */
function columnsForWidth(width: number): number {
  const columnWidth = MIN_CARD_WIDTH + GRID_GAP;
  return Math.min(4, Math.max(2, Math.floor((width + GRID_GAP) / columnWidth)));
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
  pageSize,
  className,
  cardClassName,
}: MovieCardGridProps) {
  const autoFit = pageSize === "auto";
  const gridAreaRef = useRef<HTMLDivElement>(null);
  const gridRef = useRef<HTMLUListElement>(null);
  const [dims, setDims] = useState<{ width: number; height: number } | null>(null);
  const [rowHeight, setRowHeight] = useState<number | null>(null);
  const [pageIndex, setPageIndex] = useState(0);

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

  const columns = autoFit && dims !== null ? columnsForWidth(dims.width) : null;

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
      setRowHeight(Math.max(...heights));
    }
  }, [autoFit, dims, columns]);

  const effectivePageSize =
    autoFit && dims !== null && rowHeight !== null && columns !== null
      ? columns *
        Math.max(1, Math.floor((dims.height + GRID_GAP) / (rowHeight + GRID_GAP)))
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
    setPageIndex((page) => (page >= pageCount ? Math.max(0, pageCount - 1) : page));
  }, [pageCount]);

  let renderItems: readonly MovieCardGridItem[] = items;
  if (hasPagination) {
    const startIndex = pageIndex * (effectivePageSize as number);
    renderItems = items.slice(startIndex, startIndex + (effectivePageSize as number));
  } else if (measuring) {
    renderItems = items.slice(0, columns ?? 2);
  }

  const showControls = hasPagination && pageCount > 1;

  const handleKeyDown = (event: KeyboardEvent<HTMLUListElement>) => {
    if (!showControls) return;
    if (event.target instanceof HTMLAnchorElement) return;
    if (event.key === "ArrowRight") {
      event.preventDefault();
      setPageIndex((page) => Math.min(pageCount - 1, page + 1));
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      setPageIndex((page) => Math.max(0, page - 1));
    }
  };

  const grid = (
    <ul
      ref={gridRef}
      onKeyDown={handleKeyDown}
      tabIndex={showControls ? 0 : undefined}
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
      {renderItems.map((item, index) => (
        <li key={item.key ?? `${item.movie.title}-${index}`}>
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
            className={cn("h-full", cardClassName)}
          />
        </li>
      ))}
    </ul>
  );

  const controls = showControls ? (
    <div className="flex items-center justify-center gap-2">
      <button
        type="button"
        onClick={() => setPageIndex((page) => Math.max(0, page - 1))}
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
        onClick={() => setPageIndex((page) => Math.min(pageCount - 1, page + 1))}
        disabled={pageIndex >= pageCount - 1}
        aria-label="Next page"
        className="flex cursor-pointer items-center justify-center p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-40"
      >
        <ChevronRight aria-hidden className="size-4" />
      </button>
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
