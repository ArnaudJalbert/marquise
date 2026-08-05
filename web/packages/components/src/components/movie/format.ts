const timeFormatter = new Intl.DateTimeFormat("en-CA", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  hourCycle: "h23",
  timeZone: "America/Toronto",
});

export function formatTime(startsAt: string): string {
  const date = new Date(startsAt);
  if (Number.isNaN(date.getTime())) {
    return startsAt;
  }
  return timeFormatter.format(date);
}

const hourFormatter = new Intl.DateTimeFormat("en-CA", {
  hour: "2-digit",
  hour12: false,
  hourCycle: "h23",
  timeZone: "America/Toronto",
});

/** Hour (0–23) of a showtime in the Montreal timezone, used for time-range filtering. */
export function getHour(startsAt: string): number {
  const date = new Date(startsAt);
  if (Number.isNaN(date.getTime())) {
    return 0;
  }
  return Number(hourFormatter.format(date));
}

export function formatDuration(durationMinutes: number): string {
  const hours = Math.floor(durationMinutes / 60);
  const minutes = durationMinutes % 60;
  if (hours === 0) {
    return `${minutes} min`;
  }
  if (minutes === 0) {
    return `${hours} h`;
  }
  return `${hours} h ${minutes} min`;
}

export function isPassed(
  startsAt: string,
  currentTime: string | undefined,
): boolean {
  if (currentTime === undefined) {
    return false;
  }
  const start = new Date(startsAt).getTime();
  const now = new Date(currentTime).getTime();
  if (Number.isNaN(start) || Number.isNaN(now)) {
    return false;
  }
  return start <= now;
}

export function compareByStart(a: string, b: string): number {
  const at = new Date(a).getTime();
  const bt = new Date(b).getTime();
  if (Number.isNaN(at)) {
    return Number.isNaN(bt) ? 0 : 1;
  }
  if (Number.isNaN(bt)) {
    return -1;
  }
  return at - bt;
}
