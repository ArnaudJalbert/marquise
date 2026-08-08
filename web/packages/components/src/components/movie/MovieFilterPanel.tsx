import { type ChangeEvent, type ReactNode } from "react";

import { cn } from "../../lib/utils";
import { DateSelector } from "./date-selector";
import { TIME_MAX_HOUR, TIME_MIN_HOUR } from "./movie-grid-filter";

export { formatDateLabel } from "./date-selector";

export function formatHourLabel(hour: number): string {
  return `${String(hour).padStart(2, "0")}:00`;
}

function SectionHeading({ children }: { children: ReactNode }) {
  return (
    <h2 className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
      {children}
    </h2>
  );
}

function Chip({
  selected,
  label,
  onClick,
}: {
  selected: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={cn(
        "cursor-pointer rounded-full border px-3 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        selected
          ? "border-transparent bg-primary text-primary-foreground"
          : "border-border bg-background text-foreground hover:bg-accent",
      )}
    >
      {label}
    </button>
  );
}

function MultiSelectGroup({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: readonly string[];
  selected: readonly string[];
  onChange: (next: readonly string[]) => void;
}) {
  const toggle = (option: string) => {
    if (selected.includes(option)) {
      onChange(selected.filter((value) => value !== option));
    } else {
      onChange([...selected, option]);
    }
  };
  const allSelected =
    options.length > 0 &&
    options.every((option) => selected.includes(option));
  const noneSelected = selected.length === 0;

  const selectionButtonClasses =
    "cursor-pointer text-xs text-muted-foreground hover:text-foreground hover:underline underline-offset-4 disabled:pointer-events-none disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <SectionHeading>
          {label}
          {selected.length > 0 ? ` · ${selected.length}/${options.length}` : ""}
        </SectionHeading>
        {options.length > 0 ? (
          <div className="flex shrink-0 gap-3">
            <button
              type="button"
              onClick={() => onChange([...options])}
              disabled={allSelected}
              className={selectionButtonClasses}
            >
              Select all
            </button>
            <button
              type="button"
              onClick={() => onChange([])}
              disabled={noneSelected}
              className={selectionButtonClasses}
            >
              Clear
            </button>
          </div>
        ) : null}
      </div>
      {options.length === 0 ? (
        <p className="text-xs text-muted-foreground">No options on this date.</p>
      ) : (
        <div className="flex flex-wrap gap-2" role="group" aria-label={label}>
          {options.map((option) => (
            <Chip
              key={option}
              label={option}
              selected={selected.includes(option)}
              onClick={() => toggle(option)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

export interface MovieFilterPanelProps {
  /** Selectable dates as "YYYY-MM-DD" strings. */
  dates: readonly string[];
  selectedDate: string;
  onDateChange: (date: string) => void;
  /** Cinemas available on the selected date, by name. */
  cinemas: readonly string[];
  selectedCinemas: readonly string[];
  onCinemasChange: (next: readonly string[]) => void;
  /** Genres available on the selected date. */
  genres: readonly string[];
  selectedGenres: readonly string[];
  onGenresChange: (next: readonly string[]) => void;
  /** Language tags available on the selected date. */
  languages: readonly string[];
  selectedLanguages: readonly string[];
  onLanguagesChange: (next: readonly string[]) => void;
  /** Start–end hours, both inclusive. */
  timeRange: readonly [number, number];
  onTimeRangeChange: (next: readonly [number, number]) => void;
  minHour?: number;
  maxHour?: number;
  className?: string;
}

/**
 * Vertical, controlled filter panel for a movie grid. The date is picked from a
 * calendar popover (with arrows to step to the previous/next available date),
 * the time range from a slider, and cinema/genre/language from chip groups;
 * every value is lifted up so callers decide when to fetch and how to filter.
 */
export function MovieFilterPanel({
  dates,
  selectedDate,
  onDateChange,
  cinemas,
  selectedCinemas,
  onCinemasChange,
  genres,
  selectedGenres,
  onGenresChange,
  languages,
  selectedLanguages,
  onLanguagesChange,
  timeRange,
  onTimeRangeChange,
  minHour = TIME_MIN_HOUR,
  maxHour = TIME_MAX_HOUR,
  className,
}: MovieFilterPanelProps) {
  const span = maxHour - minHour;
  const startPct = span > 0 ? ((timeRange[0] - minHour) / span) * 100 : 0;
  const endPct = span > 0 ? ((timeRange[1] - minHour) / span) * 100 : 100;

  const handleStartChange = (event: ChangeEvent<HTMLInputElement>) => {
    const value = Math.max(minHour, Number(event.target.value));
    onTimeRangeChange([Math.min(value, timeRange[1]), Math.max(value, timeRange[1])]);
  };

  const handleEndChange = (event: ChangeEvent<HTMLInputElement>) => {
    const value = Math.min(maxHour, Number(event.target.value));
    onTimeRangeChange([timeRange[0], Math.max(value, timeRange[0])]);
  };

  return (
    <div className={cn("flex min-h-0 flex-col gap-6 overflow-y-auto", className)}>
      <section className="flex flex-col gap-2">
        <SectionHeading>Date</SectionHeading>
        <DateSelector
          dates={dates}
          selectedDate={selectedDate}
          onDateChange={onDateChange}
        />
      </section>

      <section className="flex flex-col gap-2">
        <SectionHeading>Time</SectionHeading>
        <p
          aria-live="polite"
          className="font-mono text-sm text-muted-foreground tabular-nums"
        >
          {formatHourLabel(timeRange[0])} – {formatHourLabel(timeRange[1])}
        </p>
        <div className="time-range-slider relative h-8 select-none">
          <div className="absolute top-1/2 h-1.5 w-full -translate-y-1/2 rounded-full bg-muted" />
          <div
            className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-foreground"
            style={{ left: `${startPct}%`, width: `${Math.max(0, endPct - startPct)}%` }}
          />
          <input
            type="range"
            min={minHour}
            max={maxHour}
            step={1}
            value={timeRange[0]}
            onChange={handleStartChange}
            aria-label="Start time"
            aria-valuetext={formatHourLabel(timeRange[0])}
            className={timeRange[0] === timeRange[1] ? "z-10" : undefined}
          />
          <input
            type="range"
            min={minHour}
            max={maxHour}
            step={1}
            value={timeRange[1]}
            onChange={handleEndChange}
            aria-label="End time"
            aria-valuetext={formatHourLabel(timeRange[1])}
          />
        </div>
      </section>

      <MultiSelectGroup
        label="Cinemas"
        options={cinemas}
        selected={selectedCinemas}
        onChange={onCinemasChange}
      />
      <MultiSelectGroup
        label="Genres"
        options={genres}
        selected={selectedGenres}
        onChange={onGenresChange}
      />
      <MultiSelectGroup
        label="Languages"
        options={languages}
        selected={selectedLanguages}
        onChange={onLanguagesChange}
      />
    </div>
  );
}
