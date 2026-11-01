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
