import type { ReactNode } from "react";

import type { CinemaShowtime } from "./cinema";
import type { MovieCardData } from "./movie";

export interface MovieCardProps {
  movie: MovieCardData;
  /** Single source of showtimes; populates the card chips, the hover popover and the inline widget. */
  showtimes?: readonly CinemaShowtime[];
  /** Link to the "all showtimes" page; the movie title always links to it. */
  showtimesUrl: string;
  /** Maximum number of upcoming showtime chips to show before the all-showtimes widget. */
  maxShowtimes?: number;
  /** Delay in ms before the hover popover opens. */
  hoverOpenDelay?: number;
  /** Render-prop override for a single showtime chip; replaces the default time link. */
  renderShowtime?: (showtime: CinemaShowtime) => ReactNode;
  /** Invoked when a showtime chip is clicked. */
  onShowtimeClick?: (showtime: CinemaShowtime) => void;
  /** ISO-8601 timestamp treated as "now"; showtimes that already started are crossed out. */
  currentTime?: string;
  /** Background color (any CSS color) that fills the card behind poster and text. */
  backgroundColor?: string;
  /** Extra classes for the outer card. */
  className?: string;
}
