import { ChevronLeft, ChevronRight } from "lucide-react";

const dateLabelFormatter = new Intl.DateTimeFormat("en-CA", {
  weekday: "short",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

export function formatDateLabel(isoDay: string): string {
  const date = new Date(`${isoDay}T12:00:00Z`);
  return Number.isNaN(date.getTime()) ? isoDay : dateLabelFormatter.format(date);
}

/** Native available-date selector with adjacent-date shortcuts. */
export function DateSelector({
  dates,
  selectedDate,
  onDateChange,
}: {
  dates: readonly string[];
  selectedDate: string;
  onDateChange: (date: string) => void;
}) {
  const sortedDates = [...dates].sort();
  const selectedIndex = sortedDates.indexOf(selectedDate);
  const step = (delta: -1 | 1) => {
    const target = sortedDates[selectedIndex + delta];
    if (target !== undefined) onDateChange(target);
  };

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        aria-label="Previous date"
        disabled={selectedIndex <= 0}
        onClick={() => step(-1)}
        className="flex cursor-pointer items-center justify-center p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-40"
      >
        <ChevronLeft aria-hidden className="size-4" />
      </button>
      <select
        aria-label="Screening date"
        value={selectedDate}
        onChange={(event) => onDateChange(event.target.value)}
        className="min-w-0 flex-1 cursor-pointer rounded-md border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {selectedDate === "" ? <option value="">Select a date</option> : null}
        {sortedDates.map((date) => (
          <option key={date} value={date}>
            {formatDateLabel(date)}
          </option>
        ))}
      </select>
      <button
        type="button"
        aria-label="Next date"
        disabled={selectedIndex === -1 || selectedIndex >= sortedDates.length - 1}
        onClick={() => step(1)}
        className="flex cursor-pointer items-center justify-center p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-40"
      >
        <ChevronRight aria-hidden className="size-4" />
      </button>
    </div>
  );
}
