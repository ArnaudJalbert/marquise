import type { ReactNode } from "react";
import type { CinemaShowtime, MovieCardData } from "marquise-client";

export interface MovieCardProps {
  movie: MovieCardData;
  /** Single source of showtimes; populates the card chips, the hover popover and the inline widget. */
  showtimes?: readonly CinemaShowtime[];
  /** Link to the "all showtimes" page; the movie title always links to it. */
  showtimesUrl: string;
  /** Optional maximum number of upcoming showtime chips to show. */
  maxShowtimes?: number;
  /** Delay in ms before the hover popover opens. */
  hoverOpenDelay?: number;
  /** Render-prop override for a single showtime chip; replaces the default time link. */
  renderShowtime?: (showtime: CinemaShowtime) => ReactNode;
  /** Invoked when a showtime chip is clicked. */
  onShowtimeClick?: (showtime: CinemaShowtime) => void;
  /** Invoked when the poster or title is clicked, replacing the showtimesUrl link. */
  onMovieClick?: (movie: MovieCardData) => void;
  /** ISO-8601 timestamp treated as "now"; showtimes that already started are crossed out. */
  currentTime?: string;
  /** Background color (any CSS color) that fills the card behind poster and text. */
  backgroundColor?: string;
  /** When true, hides metadata and showtimes while retaining the title. */
  hideDetails?: boolean;
  /** Extra classes for the outer card. */
  className?: string;
}
