import type { ReactNode } from "react";

import type {
  CinemaShowtime,
  MovieCardData,
  MovieCardGridItem,
} from "marquise-client";

export type { MovieCardGridItem } from "marquise-client";

export interface MovieCardGridProps {
  items: readonly MovieCardGridItem[];
  /** Shared props forwarded to every card. */
  currentTime?: string;
  hoverOpenDelay?: number;
  maxShowtimes?: number;
  backgroundColor?: string;
  renderShowtime?: (showtime: CinemaShowtime) => ReactNode;
  onShowtimeClick?: (showtime: CinemaShowtime) => void;
  /** Invoked when a card's poster or title is clicked. */
  onMovieClick?: (movie: MovieCardData) => void;
  /**
   * Number of movies per page, or "auto" to fit the grid to its container.
   * "auto" measures a bounded-height parent and pages so nothing overflows;
   * omit to render every movie in a single grid.
   */
  pageSize?: number | "auto";
  /** Zero-based page selected on first render; defaults to the first page. */
  initialPageIndex?: number;
  /** Invoked for user navigation or when an unavailable page is normalized. */
  onPageIndexChange?: (
    pageIndex: number,
    reason: "user" | "normalization",
  ) => void;
  /**
   * Minimum card width in px for `pageSize="auto"`. Larger values produce
   * wider cards and fewer columns; smaller values more columns. Ignored with
   * a numeric `pageSize`. Defaults to 200.
   */
  cardSize?: number;
  /** Invoked whenever the controlled card-size slider moves. */
  onCardSizeChange?: (size: number) => void;
  /** When true, every card hides metadata and showtimes while retaining its title. */
  hideDetails?: boolean;
  /** Invoked whenever the controlled details visibility toggle changes. */
  onHideDetailsChange?: (hide: boolean) => void;
  /** Classes for the grid container; overrides the default responsive columns. */
  className?: string;
  /** Extra classes applied to every card. */
  cardClassName?: string;
}
