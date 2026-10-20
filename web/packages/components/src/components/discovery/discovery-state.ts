import type { ScreeningQuery } from "marquise-client";

export function validDate(value: string | null): string | undefined {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return undefined;
  const date = new Date(`${value}T12:00:00Z`);
  return !Number.isNaN(date.getTime()) &&
    date.toISOString().slice(0, 10) === value
    ? value
    : undefined;
}
function validTime(value: string | null): string | undefined {
  // Keep links from the former hour-slider interface useful.
  if (value && /^\d{1,2}$/.test(value) && Number(value) <= 24) {
    return Number(value) === 24 ? "23:59" : `${value.padStart(2, "0")}:00`;
  }
  return value && /^([01]\d|2[0-3]):[0-5]\d$/.test(value) ? value : undefined;
}
export function screeningValidation(query: ScreeningQuery): string | undefined {
  return query.fromTime && query.toTime && query.fromTime > query.toTime
    ? "Choose an Until time at or after the From time. For a screening after midnight, choose the next date."
    : undefined;
}
export function screeningQuery(url: URL, today: string): ScreeningQuery {
  const rawPage = Number(url.searchParams.get("page"));
  const fromTime = validTime(url.searchParams.get("from"));
  const toTime = validTime(url.searchParams.get("to"));
  return {
    date: validDate(url.searchParams.get("date")) ?? today,
    page: Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1,
    size: 48,
    movie: url.searchParams.get("movie") || undefined,
    cinemaId: url.searchParams.get("cinema") || undefined,
    language: url.searchParams.get("language") || undefined,
    fromTime,
    toTime,
  };
}
export function screeningsHref(query: ScreeningQuery): string {
  const params = new URLSearchParams({ date: query.date });
  if (query.page > 1) params.set("page", String(query.page));
  for (const [key, value] of [
    ["movie", query.movie],
    ["cinema", query.cinemaId],
    ["language", query.language],
    ["from", query.fromTime],
    ["to", query.toTime],
  ]) {
    if (key && value) params.set(key, value);
  }
  return `/screenings?${params}`;
}
