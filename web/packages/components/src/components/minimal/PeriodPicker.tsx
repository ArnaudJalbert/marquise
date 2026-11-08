import { ChevronLeft, ChevronRight } from "lucide-react";
import {
  useEffect,
  useId,
  useRef,
  useState,
  useSyncExternalStore,
  type CSSProperties,
  type KeyboardEvent,
  type PointerEvent,
  type Ref,
} from "react";
import { addDays, formatRangeDate } from "./catalogue-format";
import {
  anchorView,
  dayOfMonth,
  daysBetween,
  describePeriod,
  fitView,
  HORIZON_DAYS,
  monthName,
  stepPeriod,
  weekday,
  weekdayName,
  type StripView,
  type WeekCount,
} from "./period";

const weeksLabel = (weeks: WeekCount) => `${weeks} ${weeks === 1 ? "week" : "weeks"}`;

/** Same breakpoint as the phone rules in minimal.css. */
const PHONE_QUERY = "(max-width: 639px)";

function subscribeToPhoneLayout(onChange: () => void) {
  const query = window.matchMedia?.(PHONE_QUERY);
  query?.addEventListener("change", onChange);
  return () => query?.removeEventListener("change", onChange);
}

const isPhoneLayout = () => window.matchMedia?.(PHONE_QUERY).matches ?? false;

/** Whether the phone breakpoint matches, kept live as the viewport changes. */
function usePhoneLayout(): boolean {
  return useSyncExternalStore(subscribeToPhoneLayout, isPhoneLayout, () => false);
}

function ZoomSlider({
  weeks,
  onZoom,
  inputRef,
}: {
  weeks: WeekCount;
  onZoom: (weeks: WeekCount) => void;
  inputRef?: Ref<HTMLInputElement>;
}) {
  return (
    <>
      <input
        ref={inputRef}
        type="range"
        min={1}
        max={6}
        step={1}
        value={weeks}
        aria-label="Zoom"
        aria-valuetext={weeksLabel(weeks)}
        onChange={(event) => onZoom(Number(event.target.value) as WeekCount)}
      />
      <span aria-hidden>{weeksLabel(weeks)}</span>
    </>
  );
}

/** Phone zoom: a "N wk" chip that opens the slider in a popover below it. */
function ZoomChip({
  weeks,
  onZoom,
}: {
  weeks: WeekCount;
  onZoom: (weeks: WeekCount) => void;
}) {
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLDivElement>(null);
  const chip = useRef<HTMLButtonElement>(null);
  const slider = useRef<HTMLInputElement>(null);
  const popoverId = useId();

  useEffect(() => {
    if (!open) return;
    slider.current?.focus();
    const close = () => {
      setOpen(false);
      chip.current?.focus();
    };
    const closeOutside = (event: globalThis.PointerEvent) => {
      if (!menu.current?.contains(event.target as Node)) close();
    };
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <div className="minimal-zoom-menu" ref={menu}>
      <button
        ref={chip}
        type="button"
        className="minimal-zoom-chip"
        aria-label={`Zoom, ${weeksLabel(weeks)}`}
        aria-expanded={open}
        aria-controls={popoverId}
        onClick={() => setOpen(!open)}
      >
        {weeks} wk <span aria-hidden>▾</span>
      </button>
      {open && (
        <div id={popoverId} className="minimal-zoom minimal-zoom-popover">
          <ZoomSlider weeks={weeks} onZoom={onZoom} inputRef={slider} />
        </div>
      )}
    </div>
  );
}

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
  todayAsWeekday,
  onChange,
}: {
  today: string;
  range: [number, number];
  view: StripView;
  /** Label today with its weekday, highlighted, where "Today" would not fit. */
  todayAsWeekday: boolean;
  onChange: (start: number, end: number) => void;
}) {
  const drag = useRef<Drag | null>(null);
  const keyboardAnchor = useRef<number | null>(null);
  const keyboardRange = useRef<string | null>(null);
  if (keyboardRange.current && keyboardRange.current !== range.join("/")) {
    keyboardAnchor.current = null;
    keyboardRange.current = null;
  }
  const [draft, setDraft] = useState<[number, number] | null>(null);
  const [start, end] = draft ?? range;
  const dayCount = view.weeks * 7;
  const days = Array.from({ length: dayCount }, (_, i) => view.first + i);
  const last = view.first + dayCount - 1;
  const focusDay = Math.max(view.first, Math.min(last, start));
  const dayAt = (event: PointerEvent<HTMLDivElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(0.999, (event.clientX - box.left) / box.width));
    return view.first + Math.floor(ratio * dayCount);
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
      data-days={dayCount}
      style={{ "--strip-days": dayCount } as CSSProperties}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          keyboardAnchor.current = null;
          keyboardRange.current = null;
        }
      }}
      onPointerDown={(event) => {
        if (event.button !== 0) return;
        keyboardAnchor.current = null;
        keyboardRange.current = null;
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
              if (event.detail === 0) {
                keyboardAnchor.current = null;
                keyboardRange.current = null;
                onChange(day, day);
              }
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
                if (event.shiftKey) {
                  const anchor = keyboardAnchor.current ?? day;
                  keyboardAnchor.current = anchor;
                  const nextDay = day + (event.key === "ArrowRight" ? 1 : -1);
                  const nextRange: [number, number] = [
                    Math.min(anchor, nextDay),
                    Math.max(anchor, nextDay),
                  ];
                  keyboardRange.current = nextRange.join("/");
                  onChange(...nextRange);
                } else {
                  keyboardAnchor.current = null;
                  keyboardRange.current = null;
                }
                sibling.focus();
              }
            }}
          >
            <span className="minimal-strip-month" aria-hidden>
              {day === view.first || dayOfMonth(date) === 1 ? monthName(date) : ""}
            </span>
            <span
              className={
                day === 0 && todayAsWeekday
                  ? "minimal-strip-weekday is-highlighted"
                  : "minimal-strip-weekday"
              }
              aria-hidden
            >
              {day === 0 && !todayAsWeekday ? "Today" : weekdayName(date)}
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
            left: `${((shownStart - view.first) / dayCount) * 100}%`,
            width: `${((shownEnd - shownStart + 1) / dayCount) * 100}%`,
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
  // A fresh picker opens on one week from today.
  const [view, setView] = useState(() => fitView({ weeks: 1, first: 0 }, ...range));
  const [fitted, setFitted] = useState(`${today}/${start}/${end}`);
  // Refit the view whenever the committed period changes, wherever it came from.
  if (fitted !== `${today}/${start}/${end}`) {
    setFitted(`${today}/${start}/${end}`);
    setView(fitView(view, ...range));
  }
  const { title, detail } = describePeriod(start, end, today);
  const previous = stepPeriod(start, end, today, -1);
  const next = stepPeriod(start, end, today, 1);
  const phone = usePhoneLayout();
  const zoom = (weeks: WeekCount) => setView(anchorView(weeks, range[0]));

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
        {phone ? (
          <ZoomChip weeks={view.weeks} onZoom={zoom} />
        ) : (
          <div className="minimal-zoom">
            <ZoomSlider weeks={view.weeks} onZoom={zoom} />
          </div>
        )}
      </div>
      {detail && <p className="minimal-period-detail">{detail}</p>}
      <DayStrip
        today={today}
        range={range}
        view={view}
        todayAsWeekday={phone && view.weeks === 2}
        onChange={(from, to) => onChange(addDays(today, from), addDays(today, to))}
      />
    </section>
  );
}
