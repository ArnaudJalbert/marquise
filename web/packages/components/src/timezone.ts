const MONTREAL_TZ = 'America/Toronto';

const MONTREAL_TODAY_FORMATTER = new Intl.DateTimeFormat('en-CA', { timeZone: MONTREAL_TZ });

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

function montrealLocalToUtc(dateKey: string, time: string): Date {
  const [year, month, day] = dateKey.split('-').map(Number);
  const [hour, minute] = time.split(':').map(Number);
  const guess = new Date(Date.UTC(year, month - 1, day, hour, minute));
  const offsetMinutes = montrealOffsetMinutesAt(guess);
  return new Date(guess.getTime() - offsetMinutes * 60_000);
}

export function montrealDateKeyToUtcRange(dateKey: string): { from: Date; to: Date } {
  return {
    from: montrealLocalToUtc(dateKey, '00:00'),
    to: montrealLocalToUtc(dateKey, '23:59'),
  };
}
