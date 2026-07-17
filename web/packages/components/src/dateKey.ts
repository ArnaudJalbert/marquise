/**
 * Canonical date identity used across `PosterMovie.dates` / `PosterWallFilters.dates`:
 * a local "YYYY-MM-DD" string, not a bare day-of-month int. Bare day-of-month
 * ints have no way to disambiguate "the 15th of which month" — picking a date
 * in a different month than the data was anchored to silently matched
 * nothing. A real date string has no such ambiguity.
 */
export function toDateKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

/** Parses a "YYYY-MM-DD" key back into a local Date (midnight, local time). */
export function parseDateKey(key: string): Date {
  const [y, m, d] = key.split('-').map(Number);
  return new Date(y, m - 1, d);
}

export function addDaysToDateKey(dateKey: string, days: number): string {
  const [year, month, day] = dateKey.split('-').map(Number);
  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10);
}
