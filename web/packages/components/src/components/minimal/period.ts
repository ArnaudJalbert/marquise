import { addDays } from "./catalogue-format";

/** The day strip covers six weeks from today; offsets below count days from today. */
export const HORIZON_DAYS = 42;

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function utcNoon(date: string): Date {
  return new Date(`${date}T12:00:00Z`);
}
export function weekday(date: string): number {
  return utcNoon(date).getUTCDay();
}
export function dayOfMonth(date: string): number {
  return utcNoon(date).getUTCDate();
}
export function weekdayName(date: string): string {
  return WEEKDAYS[weekday(date)] ?? "";
}
export function monthName(date: string): string {
  return MONTHS[utcNoon(date).getUTCMonth()] ?? "";
}
/** Whole days from `from` to `to`. */
export function daysBetween(from: string, to: string): number {
  return Math.round((utcNoon(to).getTime() - utcNoon(from).getTime()) / 86_400_000);
}

const monthDay = (date: string) => `${monthName(date)} ${dayOfMonth(date)}`;
const shortDay = (date: string) => `${weekdayName(date)} ${monthDay(date)}`;

/** Friday of the weekend that contains today, or the next one. */
function currentFriday(today: string): string {
  const day = weekday(today);
  return addDays(today, day === 6 ? -1 : day === 0 ? -2 : 5 - day);
}

type PeriodKind = "day" | "weekend" | "week" | "range";

function kindOf(start: string, end: string, today: string): PeriodKind {
  if (start === end) return "day";
  // The current weekend may be cut short by today.
  const friday = addDays(end, -2);
  if (weekday(end) === 0 && start === (friday > today ? friday : today))
    return "weekend";
  if (weekday(start) === 1 && end === addDays(start, 6)) return "week";
  return "range";
}

export interface PeriodDescription {
  title: string;
  /** The dates behind a named title, when they are not obvious from it. */
  detail?: string;
}

export function describePeriod(
  start: string,
  end: string,
  today: string,
): PeriodDescription {
  const dates = start === end ? shortDay(start) : `${monthDay(start)} → ${monthDay(end)}`;
  const named = (title: string) => ({ title, detail: dates });
  switch (kindOf(start, end, today)) {
    case "day":
      if (start === today) return named("Today");
      if (start === addDays(today, 1)) return named("Tomorrow");
      return { title: dates };
    case "weekend": {
      const friday = currentFriday(today);
      if (end === addDays(friday, 2)) return named("This weekend");
      if (end === addDays(friday, 9)) return named("Next weekend");
      return named(`Weekend of ${monthDay(addDays(end, -2))}`);
    }
    case "week":
      return named(`Week of ${monthDay(start)}`);
    case "range":
      return { title: dates };
  }
}

/** The period one step before or after, or undefined when it would leave the strip. */
export function stepPeriod(
  start: string,
  end: string,
  today: string,
  direction: 1 | -1,
): [string, string] | undefined {
  const kind = kindOf(start, end, today);
  const length = kind === "day" || kind === "range" ? daysBetween(start, end) + 1 : 7;
  const nextEnd = addDays(end, direction * length);
  let nextStart = addDays(start, direction * length);
  if (kind === "weekend") {
    const friday = addDays(nextEnd, -2);
    nextStart = friday > today ? friday : today;
  }
  const last = addDays(today, HORIZON_DAYS - 1);
  return nextStart < today || nextStart > nextEnd || nextEnd > last
    ? undefined
    : [nextStart, nextEnd];
}

export type WeekCount = 1 | 2 | 3 | 4 | 5 | 6;

export interface StripView {
  weeks: WeekCount;
  /** Offset from today of the first visible day; always a multiple of 7. */
  first: number;
}

/** `weeks` whole weeks from the block holding `day`, clamped to the horizon. */
export function anchorView(weeks: WeekCount, day: number): StripView {
  const first = Math.floor(day / 7) * 7;
  return { weeks, first: Math.max(0, Math.min(HORIZON_DAYS - weeks * 7, first)) };
}

/** Keeps a visible period in view, else pans at the same zoom, widening only to fit. */
export function fitView(current: StripView, start: number, end: number): StripView {
  if (start >= current.first && end < current.first + current.weeks * 7) return current;
  const spannedWeeks = Math.floor(end / 7) - Math.floor(start / 7) + 1;
  return anchorView(Math.max(current.weeks, spannedWeeks) as WeekCount, start);
}
