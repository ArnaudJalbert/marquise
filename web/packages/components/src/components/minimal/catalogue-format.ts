export function addDays(date: string, days: number): string {
  const value = new Date(`${date}T12:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}
export function formatDate(date: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "UTC",
    weekday: "short",
    day: "numeric",
  }).format(new Date(`${date}T12:00:00Z`));
}
export function formatRangeDate(date: string): string {
  const value = new Date(`${date}T12:00:00Z`);
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "UTC",
    weekday: "long",
    month: "long",
    day: "numeric",
  }).formatToParts(value);
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((item) => item.type === type)?.value ?? "";
  const day = Number(part("day"));
  const suffix =
    day % 100 >= 11 && day % 100 <= 13
      ? "th"
      : ({ 1: "st", 2: "nd", 3: "rd" }[day % 10] ?? "th");
  return `${part("weekday")} ${part("month")} ${day}${suffix}`;
}
export function timeToHour(time: string, fallback: number): number {
  const match = /^(\d{2}):(\d{2})$/.exec(time);
  if (!match) return fallback;
  return Math.min(
    24,
    Math.max(0, Number(match[1]) + Math.floor(Number(match[2]) / 60)),
  );
}
export function formatHour(hour: number): string {
  if (hour === 0 || hour === 24) return "midnight";
  return `${hour % 12 || 12}:00 ${hour < 12 ? "AM" : "PM"}`;
}

/** Malformed URL escapes remain opaque IDs so the API can report not found. */
export function decodePathId(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export function formatScore(score: number | null | undefined): string {
  return score == null ? "" : `${score.toFixed(1)}/10`;
}

/** Dates are Montréal calendar dates, so DST does not change the day count. */
export function relativeDay(date: string, today: string): string {
  const days = Math.round((Date.parse(date) - Date.parse(today)) / 86400000);
  if (days === 0) return "";
  if (days === 1) return "Tomorrow";
  if (days < 7) return `In ${days} days`;
  const weeks = Math.floor(days / 7);
  return `In ${weeks} ${weeks === 1 ? "week" : "weeks"}`;
}

/** Floored minutes until a showtime, shown only when it starts under two hours from now. */
export function startsIn(showtime: string, currentTimeInMilliseconds: number): string {
  const minutes = Math.floor((Date.parse(showtime) - currentTimeInMilliseconds) / 60000);
  if (minutes < 0 || minutes >= 120) return "";
  if (minutes < 60) return `in ${minutes} min`;
  return minutes === 60 ? "in 1 h" : `in 1 h ${minutes - 60} min`;
}
