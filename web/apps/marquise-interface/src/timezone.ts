/**
 * Marquise is Montreal-only — "today" for the wall should mean Montreal's
 * calendar date, not whatever timezone the visitor's device happens to be
 * in (a visitor checking Montreal showtimes from Tokyo should still land on
 * Montreal's "today", not their own).
 */
const MONTREAL_TZ = 'America/Toronto';

const MONTREAL_TODAY_FORMATTER = new Intl.DateTimeFormat('en-CA', { timeZone: MONTREAL_TZ });

/** Today's date in Montreal, as "YYYY-MM-DD" (en-CA formats numeric dates in that order). */
export function montrealTodayKey(): string {
  return MONTREAL_TODAY_FORMATTER.format(new Date());
}

const MONTREAL_OFFSET_PROBE_FORMATTER = new Intl.DateTimeFormat('en-US', {
  timeZone: MONTREAL_TZ,
  hourCycle: 'h23',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});

/**
 * Montreal's UTC offset (in minutes, negative for behind UTC e.g. -240 for
 * EDT) at the instant `date` represents. DST means this varies by date, so
 * it can't be a constant.
 */
function montrealOffsetMinutesAt(date: Date): number {
  const parts = Object.fromEntries(
    MONTREAL_OFFSET_PROBE_FORMATTER.formatToParts(date).map((p) => [p.type, p.value])
  );
  const asUtc = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
    Number(parts.hour),
    Number(parts.minute),
    Number(parts.second)
  );
  return (asUtc - date.getTime()) / 60_000;
}

/** Convert a Montreal wall-clock date key + "HH:MM" time into a real UTC instant. */
function montrealLocalToUtc(dateKey: string, time: string): Date {
  const [year, month, day] = dateKey.split('-').map(Number);
  const [hour, minute] = time.split(':').map(Number);
  const guess = new Date(Date.UTC(year, month - 1, day, hour, minute));
  const offsetMinutes = montrealOffsetMinutesAt(guess);
  return new Date(guess.getTime() - offsetMinutes * 60_000);
}

/** The real UTC instants for the start and end of a Montreal calendar day. */
export function montrealDateKeyToUtcRange(dateKey: string): { from: Date; to: Date } {
  return {
    from: montrealLocalToUtc(dateKey, '00:00'),
    to: montrealLocalToUtc(dateKey, '23:59'),
  };
}
