/** Flat, denormalised movie data — safe to pass straight from an API response. */
export interface MovieCardData {
  title: string;
  posterUrl?: string | null;
  releaseYear?: number | null;
  durationMinutes?: number | null;
  directors?: readonly string[] | null;
}
