import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "../../lib/utils";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { getCurrentMontrealDate } from "./format";

const dateLabelFormatter = new Intl.DateTimeFormat("en-CA", {
  weekday: "short",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

const monthLabelFormatter = new Intl.DateTimeFormat("en-CA", {
  year: "numeric",
  month: "long",
  timeZone: "UTC",
});

const WEEKDAY_LABELS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

/** Build a Date from a "YYYY-MM-DD" day, anchored at UTC noon so day labels never shift. */
function dateFromIsoDay(isoDay: string): Date {
  const [year, month, day] = isoDay.split("-").map(Number);
  if (year === undefined || month === undefined || day === undefined) {
    return new Date(NaN);
  }
  return new Date(Date.UTC(year, month - 1, day, 12));
}

function isoDayKey(date: Date): string {
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/** First day (UTC) of month containing given "YYYY-MM-DD" day. */
function monthStart(isoDay: string): Date {
  const [year, month] = isoDay.split("-").map(Number);
  return new Date(Date.UTC(year ?? 2000, (month ?? 1) - 1, 1));
}

function shiftMonth(date: Date, delta: number): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + delta, 1));
}

export function addIsoDays(isoDay: string, days: number): string {
  const date = dateFromIsoDay(isoDay);
  date.setUTCDate(date.getUTCDate() + days);
  return isoDayKey(date);
}

export function formatDateLabel(isoDay: string): string {
  const date = dateFromIsoDay(isoDay);
  if (Number.isNaN(date.getTime())) {
    return isoDay;
  }
  return dateLabelFormatter.format(date);
}

export function Calendar({
  selectedDate,
  initialMonth,
  onSelect,
}: {
  selectedDate: string;
  initialMonth: string;
  onSelect: (date: string) => void;
}) {
  const [visible, setVisible] = useState(() => monthStart(initialMonth));
  const [focusedDate, setFocusedDate] = useState<string | null>(
    selectedDate || null,
  );
  const focusableRef = useRef<HTMLButtonElement | null>(null);
  const today = getCurrentMontrealDate();
  const year = visible.getUTCFullYear();
  const month = visible.getUTCMonth();
  const firstWeekday = visible.getUTCDay();
  const daysInMonth = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();

  const cells: Array<string | null> = [];
  for (let index = 0; index < firstWeekday; index++) {
    cells.push(null);
  }
  for (let day = 1; day <= daysInMonth; day++) {
    cells.push(isoDayKey(new Date(Date.UTC(year, month, day))));
  }
  const rows: Array<Array<string | null>> = [];
  for (let index = 0; index < cells.length; index += 7) {
    const row = cells.slice(index, index + 7);
    while (row.length < 7) {
      row.push(null);
    }
    rows.push(row);
  }

  const focusableDate =
    focusedDate !== null && cells.includes(focusedDate)
      ? focusedDate
      : cells.find((iso): iso is string => iso !== null) ?? null;

  useEffect(() => {
    focusableRef.current?.focus();
  }, [focusedDate]);

  const moveFocus = (delta: number) => {
    if (focusableDate === null) {
      return;
    }
    for (
      let index = cells.indexOf(focusableDate) + delta;
      index >= 0 && index < cells.length;
      index += delta
    ) {
      const target = cells[index];
      if (typeof target === "string" && target >= today) {
        setFocusedDate(target);
        return;
      }
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      moveFocus(-1);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      moveFocus(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveFocus(-7);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      moveFocus(7);
    } else if (event.key === "Home") {
      event.preventDefault();
      setFocusedDate(cells.find((iso): iso is string => iso !== null && iso >= today) ?? null);
    } else if (event.key === "End") {
      event.preventDefault();
      setFocusedDate(
        [...cells].reverse().find((iso): iso is string => iso !== null && iso >= today) ?? null,
      );
    }
  };

  const goToMonth = (delta: number) => {
    setVisible((current) => shiftMonth(current, delta));
    setFocusedDate(null);
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <button
          type="button"
          aria-label="Previous month"
          onClick={() => goToMonth(-1)}
          className="flex cursor-pointer items-center justify-center p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronLeft aria-hidden className="size-4" />
        </button>
        <p className="text-sm font-medium" aria-live="polite">
          {monthLabelFormatter.format(visible)}
        </p>
        <button
          type="button"
          aria-label="Next month"
          onClick={() => goToMonth(1)}
          className="flex cursor-pointer items-center justify-center p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronRight aria-hidden className="size-4" />
        </button>
      </div>
      <div role="grid" aria-label="Calendar" onKeyDown={handleKeyDown}>
        <div role="row" className="grid grid-cols-7 text-center">
          {WEEKDAY_LABELS.map((weekday) => (
            <span
              key={weekday}
              role="columnheader"
              className="py-1 text-xs font-medium text-muted-foreground"
            >
              {weekday}
            </span>
          ))}
        </div>
        <div className="flex flex-col gap-1">
          {rows.map((row, rowIndex) => (
            <div key={rowIndex} role="row" className="grid grid-cols-7 gap-1">
              {row.map((iso, index) =>
                iso === null ? (
                  <span key={`empty-${rowIndex}-${index}`} role="gridcell" />
                ) : (
                  <span key={iso} role="gridcell">
                    <button
                      ref={focusableDate === iso ? focusableRef : undefined}
                      type="button"
                      tabIndex={focusableDate === iso ? 0 : -1}
                      aria-label={formatDateLabel(iso)}
                      aria-pressed={iso === selectedDate}
                      disabled={iso < today}
                      onClick={() => onSelect(iso)}
                      className={cn(
                        "size-8 cursor-pointer rounded-md text-sm tabular-nums transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                        iso < today
                          ? "cursor-default text-muted-foreground/40 hover:bg-transparent"
                          : iso === selectedDate && "bg-primary font-semibold text-primary-foreground",
                      )}
                    >
                      {Number(iso.slice(-2))}
                    </button>
                  </span>
                ),
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** Compact date picker with adjacent-date shortcuts and calendar popover. */
export function DateSelector({
  dates,
  selectedDate,
  onDateChange,
}: {
  dates: readonly string[];
  selectedDate: string;
  onDateChange: (date: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const today = getCurrentMontrealDate();
  const canStepBack = selectedDate > today;
  const canStepForward = selectedDate !== "";
  const anchorDate = selectedDate || dates[0] || today;

  const step = (delta: -1 | 1) => {
    if (selectedDate !== "") onDateChange(addIsoDays(selectedDate, delta));
  };

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        aria-label="Previous date"
        disabled={!canStepBack}
        onClick={() => step(-1)}
        className="flex cursor-pointer items-center justify-center p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-40"
      >
        <ChevronLeft aria-hidden className="size-4" />
      </button>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            aria-label={
              selectedDate === ""
                ? "Open calendar"
                : `Open calendar, selected ${formatDateLabel(selectedDate)}`
            }
            className="flex flex-1 cursor-pointer items-center justify-between gap-2 rounded-md border px-3 py-2 text-left text-sm transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {selectedDate === "" ? (
              <span className="text-muted-foreground">Select a date</span>
            ) : (
              formatDateLabel(selectedDate)
            )}
            <CalendarDays aria-hidden className="size-4 shrink-0 text-muted-foreground" />
          </button>
        </PopoverTrigger>
        <PopoverContent align="start" className="w-72">
          <Calendar
            selectedDate={selectedDate}
            initialMonth={anchorDate}
            onSelect={(date) => {
              onDateChange(date);
              setOpen(false);
            }}
          />
        </PopoverContent>
      </Popover>
      <button
        type="button"
        aria-label="Next date"
        disabled={!canStepForward}
        onClick={() => step(1)}
        className="flex cursor-pointer items-center justify-center p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-40"
      >
        <ChevronRight aria-hidden className="size-4" />
      </button>
    </div>
  );
}
