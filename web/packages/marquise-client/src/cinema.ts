/** A cinema hosting one or more screenings. */
export interface Cinema {
  /** Cinema id — the app's identifier for the cinema's page. */
  id: string;
  /** Cinema name — always shown. */
  name: string;
  /** Link to the cinema's own page, opened in a new tab when available. */
  link: string | null;
}

/** A cinema with its screenings, as used by the all-showtimes views. */
export interface CinemaShowtimeGroup {
  cinema: Cinema;
  showtimes: CinemaShowtime[];
}

/** A single screening in the all-showtimes view. */
export interface CinemaShowtime {
  /** ISO-8601 timestamp of the screening start. */
  startsAt: string;
  /** Link to the ticketing page for this screening, when available. */
  ticketUrl: string | null;
  /** Cinema where this screening happens — required. */
  cinema: Cinema;
  /** Language tag, e.g. "VF", "VOSTF", "EN". */
  language?: string | null;
  /** Format tag, e.g. "2D", "IMAX". */
  format?: string | null;
  /** Optional free-form note, e.g. "French subtitles". */
  note?: string | null;
}
