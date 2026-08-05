import type { ReactNode } from "react";

import type { CinemaShowtime } from "./cinema";
import type { MovieCardData } from "./movie";

/** One cell in a movie card grid: the movie plus its own screenings. */
export interface MovieCardGridItem {
  /** Stable key for React reconciliation; falls back to title + index. */
  key?: string;
  movie: MovieCardData;
  showtimes?: readonly CinemaShowtime[];
  /** Link to the "all showtimes" page; the movie title always links to it. */
  showtimesUrl: string;
}

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
  /**
   * Minimum card width in px for `pageSize="auto"`. Larger values produce
   * wider cards and fewer columns; smaller values more columns. Ignored with
   * a numeric `pageSize`. Defaults to 200.
   */
  cardSize?: number;
  /** When true, every card shows only its poster and hides title, meta and showtimes. */
  hideDetails?: boolean;
  /** Classes for the grid container; overrides the default responsive columns. */
  className?: string;
  /** Extra classes applied to every card. */
  cardClassName?: string;
}
