import { ChevronLeft, ChevronRight } from "lucide-react";
import {
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
  type PointerEvent,
} from "react";
import { addDays, formatRangeDate } from "./catalogue-format";
import {
  dayOfMonth,
  daysBetween,
  describePeriod,
  fitView,
  fortnightView,
  HORIZON_DAYS,
  monthName,
  stepPeriod,
  weekday,
  weekdayName,
  type StripView,
} from "./period";

type DragMode = "draw" | "move" | "start" | "end";
interface Drag {
  mode: DragMode;
  anchor: number;
  moved: boolean;
  range: [number, number];
}

function dragRange(
  { mode, anchor }: Drag,
  day: number,
  [start, end]: [number, number],
): [number, number] {
  if (mode === "move") {
    const shift = Math.max(-start, Math.min(HORIZON_DAYS - 1 - end, day - anchor));
    return [start + shift, end + shift];
  }
  if (mode === "start") return [Math.min(day, end), end];
  if (mode === "end") return [start, Math.max(day, start)];
  return day < anchor ? [day, anchor] : [anchor, day];
}

function DayStrip({
  today,
  range,
  view,
  onChange,
}: {
  today: string;
  range: [number, number];
  view: StripView;
  onChange: (start: number, end: number) => void;
}) {
  const drag = useRef<Drag | null>(null);
  const [draft, setDraft] = useState<[number, number] | null>(null);
  const [start, end] = draft ?? range;
  const days = Array.from({ length: view.days }, (_, i) => view.first + i);
  const last = view.first + view.days - 1;
  const focusDay = Math.max(view.first, Math.min(last, start));
  const dayAt = (event: PointerEvent<HTMLDivElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(0.999, (event.clientX - box.left) / box.width));
    return view.first + Math.floor(ratio * view.days);
  };
  const update = (next: Drag) => {
    drag.current = next;
    setDraft(next.range);
  };
  const shownStart = Math.max(start, view.first);
  const shownEnd = Math.min(end, last);

  return (
    <div
      className="minimal-strip"
      role="group"
      aria-label="Choose dates"
      data-days={view.days}
      style={{ "--strip-days": view.days } as CSSProperties}
      onPointerDown={(event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        const day = dayAt(event);
        const handle = (event.target as Element)
          .closest("[data-handle]")
          ?.getAttribute("data-handle");
        const windowRect = event.currentTarget
          .querySelector(".minimal-strip-window")
          ?.getBoundingClientRect();
        const inMoveArea =
          windowRect &&
          windowRect.width > 0 &&
          event.clientX > windowRect.left + windowRect.width * 0.25 &&
          event.clientX < windowRect.right - windowRect.width * 0.25;
        const mode: DragMode =
          inMoveArea && day >= range[0] && day <= range[1]
            ? "move"
            : handle === "start" || handle === "end"
            ? handle
            : day >= range[0] && day <= range[1]
              ? "move"
              : "draw";
        // jsdom has no pointer capture; browsers keep the drag on the strip.
        event.currentTarget.setPointerCapture?.(event.pointerId);
        update({
          mode,
          anchor: day,
          moved: false,
          range: mode === "draw" ? [day, day] : range,
        });
      }}
      onPointerMove={(event) => {
        const current = drag.current;
        if (!current) return;
        const day = dayAt(event);
        update({
          ...current,
          moved: current.moved || day !== current.anchor,
          range: dragRange(current, day, range),
        });
      }}
      onPointerUp={() => {
        const current = drag.current;
        if (!current) return;
        drag.current = null;
        setDraft(null);
        // A tap anywhere picks that single day.
        const [nextStart, nextEnd] = current.moved
          ? current.range
          : [current.anchor, current.anchor];
        onChange(nextStart, nextEnd);
      }}
      onPointerCancel={() => {
        drag.current = null;
        setDraft(null);
      }}
    >
      {days.map((day) => {
        const date = addDays(today, day);
        const weekend = weekday(date) === 0 || weekday(date) === 6;
        const selected = day >= start && day <= end;
        return (
          <button
            key={date}
            type="button"
            className={[
              "minimal-strip-day",
              weekend && "is-weekend",
              day === 0 && "is-today",
              selected && "is-selected",
            ]
              .filter(Boolean)
              .join(" ")}
            aria-label={`${day === 0 ? "Today, " : ""}${formatRangeDate(date)}`}
            aria-pressed={selected}
            tabIndex={day === focusDay ? 0 : -1}
            // Pointer taps commit on pointer up; this handles keyboard activation.
            onClick={(event) => {
              if (event.detail === 0) onChange(day, day);
            }}
            onKeyDown={(event: KeyboardEvent<HTMLButtonElement>) => {
              const sibling =
                event.key === "ArrowLeft"
                  ? event.currentTarget.previousElementSibling
                  : event.key === "ArrowRight"
                    ? event.currentTarget.nextElementSibling
                    : null;
              if (sibling instanceof HTMLButtonElement) {
                event.preventDefault();
                sibling.focus();
              }
            }}
          >
            <span className="minimal-strip-month" aria-hidden>
              {day === view.first || dayOfMonth(date) === 1 ? monthName(date) : ""}
            </span>
            <span className="minimal-strip-weekday" aria-hidden>
              {view.days === 42
                ? weekdayName(date).charAt(0)
                : day === 0
                  ? "Today"
                  : weekdayName(date)}
            </span>
            <span className="minimal-strip-date" aria-hidden>
              {dayOfMonth(date)}
            </span>
          </button>
        );
      })}
      {shownStart <= shownEnd && (
        <div
          className="minimal-strip-window"
          aria-hidden
          style={{
            left: `${((shownStart - view.first) / view.days) * 100}%`,
            width: `${((shownEnd - shownStart + 1) / view.days) * 100}%`,
          }}
        >
          {start >= view.first && <span data-handle="start" />}
          {end <= last && <span data-handle="end" />}
        </div>
      )}
    </div>
  );
}

/** Period title with stepping, zoom, and the draggable day strip. */
export function PeriodPicker({
  start,
  end,
  today,
  onChange,
  heading: Heading = "h1",
}: {
  start: string;
  end: string;
  today: string;
  onChange: (start: string, end: string) => void;
  heading?: "h1" | "h2";
}) {
  const range: [number, number] = [daysBetween(today, start), daysBetween(today, end)];
  const [view, setView] = useState(() => fitView(undefined, ...range));
  const [fitted, setFitted] = useState(`${today}/${start}/${end}`);
  // Auto zoom whenever the committed period changes, wherever it came from.
  if (fitted !== `${today}/${start}/${end}`) {
    setFitted(`${today}/${start}/${end}`);
    setView(fitView(view, ...range));
  }
  const { title, detail } = describePeriod(start, end, today);
  const previous = stepPeriod(start, end, today, -1);
  const next = stepPeriod(start, end, today, 1);
  const zoom = (days: 14 | 42) =>
    setView(days === 14 ? fortnightView(range[0]) : { days, first: 0 });

  return (
    <section className="minimal-period" aria-label="Dates">
      <div className="minimal-period-top">
        <div className="minimal-period-title">
          <button
            type="button"
            aria-label="Previous period"
            disabled={!previous}
            onClick={() => previous && onChange(...previous)}
          >
            <ChevronLeft aria-hidden size={18} />
          </button>
          <Heading>{title}</Heading>
          <button
            type="button"
            aria-label="Next period"
            disabled={!next}
            onClick={() => next && onChange(...next)}
          >
            <ChevronRight aria-hidden size={18} />
          </button>
        </div>
        <div className="minimal-zoom" role="group" aria-label="Zoom">
          {([14, 42] as const).map((days) => (
            <button
              key={days}
              type="button"
              aria-pressed={view.days === days}
              onClick={() => zoom(days)}
            >
              {days === 14 ? "2 weeks" : "6 weeks"}
            </button>
          ))}
        </div>
      </div>
      {detail && <p className="minimal-period-detail">{detail}</p>}
      <DayStrip
        today={today}
        range={range}
        view={view}
        onChange={(from, to) => onChange(addDays(today, from), addDays(today, to))}
      />
    </section>
  );
}
