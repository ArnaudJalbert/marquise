import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react';
import { Popover } from './Popover';
import { Calendar } from './Calendar';
import { parseDateKey, addDaysToDateKey, toDateKey } from './dateKey';
import './DatePickerPopover.css';

export interface DatePickerPopoverProps {
  mode: 'single' | 'range';
  onModeChange: (mode: 'single' | 'range') => void;
  /** "YYYY-MM-DD" date strings. */
  selected: string[];
  onChange: (dates: string[]) => void;
}

const DAY_LABEL = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' });

/** Formats the date-picker summary label shown next to the trigger. */
export function formatDateSummary(dates: string[]): string {
  if (dates.length === 0) return 'No dates selected';
  if (dates.length === 1) return DAY_LABEL.format(parseDateKey(dates[0]));
  return `${dates.length} dates selected`;
}

function shiftDates(dates: string[], delta: number): string[] {
  if (dates.length === 0) {
    const d = new Date();
    d.setDate(d.getDate() + delta);
    return [toDateKey(d)];
  }
  return dates.map((key) => addDaysToDateKey(key, delta));
}

/** Calendar-icon trigger + summary label, composing Popover + Calendar. */
export function DatePickerPopover({ mode, onModeChange, selected, onChange }: DatePickerPopoverProps) {
  return (
    <div className="date-picker-popover">
      <button
        type="button"
        className="date-picker-popover__arrow"
        onClick={() => onChange(shiftDates(selected, -1))}
        aria-label="Previous day"
      >
        <ChevronLeft className="date-picker-popover__arrow-icon" aria-hidden="true" />
      </button>
      <Popover
        trigger={(open, toggle) => (
          <button
            type="button"
            className={`date-picker-popover__trigger ${open ? 'date-picker-popover__trigger--open' : ''}`}
            onClick={toggle}
            aria-label="Choose dates"
          >
            <CalendarDays className="date-picker-popover__icon" aria-hidden="true" />
          </button>
        )}
      >
        <Calendar mode={mode} onModeChange={onModeChange} selected={selected} onChange={onChange} />
      </Popover>
      <button
        type="button"
        className="date-picker-popover__arrow"
        onClick={() => onChange(shiftDates(selected, 1))}
        aria-label="Next day"
      >
        <ChevronRight className="date-picker-popover__arrow-icon" aria-hidden="true" />
      </button>
      <span className="date-picker-popover__summary">{formatDateSummary(selected)}</span>
    </div>
  );
}
