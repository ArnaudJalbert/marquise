import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { toDateKey, parseDateKey } from './dateKey';
import { montrealTodayKey } from './timezone';
import './Calendar.css';

export interface CalendarProps {
  mode: 'single' | 'range';
  onModeChange: (mode: 'single' | 'range') => void;
  /** "YYYY-MM-DD" date strings. */
  selected: string[];
  onChange: (dates: string[]) => void;
  initialMonth?: Date;
}

const WEEKDAY_LABELS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
const MONTH_LABELS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

/** Date-picker calendar with Single/Range selection modes and month navigation. */
export function Calendar({ mode, onModeChange, selected, onChange, initialMonth }: CalendarProps) {
  const [displayMonth, setDisplayMonth] = useState(() => initialMonth ?? new Date());
  const [rangeStart, setRangeStart] = useState<string | null>(null);

  const todayKey = montrealTodayKey();
  const year = displayMonth.getFullYear();
  const monthIndex = displayMonth.getMonth();
  const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
  const firstWeekday = new Date(year, monthIndex, 1).getDay();

  function goToMonth(delta: number) {
    setDisplayMonth(new Date(year, monthIndex + delta, 1));
    setRangeStart(null);
  }

  function toggleDay(day: number) {
    const key = toDateKey(new Date(year, monthIndex, day));
    if (key < todayKey) return;

    if (mode === 'single') {
      onChange([key]);
      return;
    }

    if (rangeStart == null) {
      setRangeStart(key);
      onChange([key]);
      return;
    }
    const startDate = parseDateKey(rangeStart);
    const endDate = new Date(year, monthIndex, day);
    const [lo, hi] = startDate <= endDate ? [startDate, endDate] : [endDate, startDate];
    const range: string[] = [];
    const cursor = new Date(lo);
    while (cursor <= hi) {
      range.push(toDateKey(cursor));
      cursor.setDate(cursor.getDate() + 1);
    }
    onChange(range);
    setRangeStart(null);
  }

  function handleModeChange(next: 'single' | 'range') {
    onModeChange(next);
    setRangeStart(null);
  }

  const cells: { key: string; day: number | null }[] = [];
  for (let i = 0; i < firstWeekday; i++) cells.push({ key: `blank-${i}`, day: null });
  for (let day = 1; day <= daysInMonth; day++) cells.push({ key: `day-${day}`, day });

  return (
    <div className="calendar">
      <div className="calendar__mode-toggle">
        <button
          type="button"
          className={`calendar__mode-btn ${mode === 'single' ? 'calendar__mode-btn--active' : ''}`}
          onClick={() => handleModeChange('single')}
        >
          Single
        </button>
        <button
          type="button"
          className={`calendar__mode-btn ${mode === 'range' ? 'calendar__mode-btn--active' : ''}`}
          onClick={() => handleModeChange('range')}
        >
          Range
        </button>
      </div>
      <div className="calendar__header">
        <button type="button" className="calendar__nav-btn" onClick={() => goToMonth(-1)} aria-label="Previous month">
          <ChevronLeft className="calendar__nav-icon" aria-hidden="true" />
        </button>
        <span className="calendar__month-label">
          {MONTH_LABELS[monthIndex]} {year}
        </span>
        <button type="button" className="calendar__nav-btn" onClick={() => goToMonth(1)} aria-label="Next month">
          <ChevronRight className="calendar__nav-icon" aria-hidden="true" />
        </button>
      </div>
      <div className="calendar__weekdays">
        {WEEKDAY_LABELS.map((label, i) => (
          <div key={i} className="calendar__weekday">
            {label}
          </div>
        ))}
      </div>
      <div className="calendar__days">
        {cells.map(({ key, day }) => {
          if (day == null) return <div key={key} className="calendar__day calendar__day--blank" />;
          const dateKey = toDateKey(new Date(year, monthIndex, day));
          const isSelected = selected.includes(dateKey);
          const isPast = dateKey < todayKey;
          return (
            <button
              key={key}
              type="button"
              disabled={isPast}
              className={`calendar__day ${isSelected ? 'calendar__day--selected' : ''} ${isPast ? 'calendar__day--disabled' : ''}`}
              onClick={() => toggleDay(day)}
            >
              {day}
            </button>
          );
        })}
      </div>
      <div className="calendar__footer">
        <button
          type="button"
          className="calendar__clear"
          onClick={() => {
            onChange([]);
            setRangeStart(null);
          }}
        >
          Clear
        </button>
      </div>
    </div>
  );
}
