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
  /**
   * Number of movies per page, or "auto" to fit the grid to its container.
   * "auto" measures a bounded-height parent and pages so nothing overflows;
   * omit to render every movie in a single grid.
   */
  pageSize?: number | "auto";
  /** Classes for the grid container; overrides the default responsive columns. */
  className?: string;
  /** Extra classes applied to every card. */
  cardClassName?: string;
}
