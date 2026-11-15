export const MONTREAL_TIME_ZONE = "America/Montreal";

const montrealDateFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: MONTREAL_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

const montrealDateTimeFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: MONTREAL_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

/** Inclusive ISO-8601 bounds for one calendar day in Montréal. */
export interface MontrealDayRange {
  from: string;
  to: string;
}

/** Return a date as a calendar-day key in the Montréal timezone. */
export function toMontrealIsoDate(date: Date): string {
  if (Number.isNaN(date.getTime())) {
    throw new RangeError("date must be valid");
  }
  return formatDateParts(montrealDateFormatter.formatToParts(date));
}

/** Return inclusive API bounds for a Montréal calendar day. */
export function montrealDayRange(isoDay: string): MontrealDayRange {
  const start = montrealMidnight(isoDay);
  const end = new Date(montrealMidnight(addDays(isoDay, 1)).getTime() - 1);
  return { from: start.toISOString(), to: end.toISOString() };
}

/** Add whole calendar days to a YYYY-MM-DD key. */
export function addDays(isoDay: string, days: number): string {
  const { year, month, day } = parseIsoDay(isoDay);
  return new Date(Date.UTC(year, month - 1, day + days))
    .toISOString()
    .slice(0, 10);
}

/** Convert a Montréal local date and 24-hour time to an ISO-8601 instant. */
export function montrealDateTime(isoDay: string, time: string): string {
  const { year, month, day } = parseIsoDay(isoDay);
  const match = /^(\d{2}):(\d{2})$/.exec(time);
  if (match === null) {
    throw new RangeError("time must use HH:MM format");
  }
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  if (hour > 23 || minute > 59) {
    throw new RangeError("time must be valid");
  }
  const localTimeAsUtc = Date.UTC(year, month - 1, day, hour, minute);
  let instant = localTimeAsUtc;
  // Recheck the offset at the candidate instant across a DST transition.
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const local = partsToNumbers(
      montrealDateTimeFormatter.formatToParts(new Date(instant)),
    );
    const actualLocalAsUtc = Date.UTC(
      local.year,
      local.month - 1,
      local.day,
      local.hour,
      local.minute,
      local.second,
    );
    const difference = localTimeAsUtc - actualLocalAsUtc;
    if (difference === 0) return new Date(instant).toISOString();
    instant += difference;
  }
  throw new RangeError(
    "This time does not exist in Montréal on this date because the clocks change.",
  );
}

function montrealMidnight(isoDay: string): Date {
  const { year, month, day } = parseIsoDay(isoDay);
  const utcMidnight = new Date(Date.UTC(year, month - 1, day));
  const localParts = partsToNumbers(
    montrealDateTimeFormatter.formatToParts(utcMidnight),
  );
  const localTimeAsUtc = Date.UTC(
    localParts.year,
    localParts.month - 1,
    localParts.day,
    localParts.hour,
    localParts.minute,
    localParts.second,
  );
  return new Date(
    utcMidnight.getTime() - (localTimeAsUtc - utcMidnight.getTime()),
  );
}

function formatDateParts(parts: Intl.DateTimeFormatPart[]): string {
  const { year, month, day } = partsToNumbers(parts);
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function partsToNumbers(parts: Intl.DateTimeFormatPart[]): {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  second: number;
} {
  const values = Object.fromEntries(
    parts
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, Number(part.value)]),
  );
  return {
    year: values.year ?? 0,
    month: values.month ?? 0,
    day: values.day ?? 0,
    hour: values.hour ?? 0,
    minute: values.minute ?? 0,
    second: values.second ?? 0,
  };
}

function parseIsoDay(isoDay: string): {
  year: number;
  month: number;
  day: number;
} {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDay);
  if (match === null) {
    throw new RangeError("date must use YYYY-MM-DD format");
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const candidate = new Date(Date.UTC(year, month - 1, day));
  if (candidate.toISOString().slice(0, 10) !== isoDay) {
    throw new RangeError("date must be a valid calendar day");
  }
  return { year, month, day };
}
