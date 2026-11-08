import { ChevronLeft, ChevronRight } from "lucide-react";
import {
  useCallback,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
  type PointerEvent,
} from "react";
import { useResource } from "../discovery/use-resource";
import { addDays, formatRangeDate } from "./catalogue-format";
import type { CatalogueDayCount, MinimalCatalogueProps } from "./catalogue-types";
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

const formatWeeks = (weeks: WeekCount) => `${weeks} ${weeks === 1 ? "week" : "weeks"}`;

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

type LoadDayCounts = NonNullable<MinimalCatalogueProps["onLoadDayCounts"]>;

/** Screening totals by date, or undefined while unknown, plus whether a load is pending. */
interface DayVolume {
  totals?: ReadonlyMap<string, number>;
  loading: boolean;
}

const formatScreeningCount = (count: number) =>
  count === 0 ? "No screenings" : count === 1 ? "1 screening" : `${count} screenings`;

/** One request per visible horizon and loader; the loader's identity carries the filters. */
function useDayVolume(
  today: string,
  view: StripView,
  onLoadDayCounts: LoadDayCounts | undefined,
): DayVolume {
  const first = addDays(today, view.first);
  const last = addDays(today, view.first + view.weeks * 7 - 1);
  const counts = useResource(
    useCallback(
      async (signal: AbortSignal): Promise<readonly CatalogueDayCount[]> =>
        onLoadDayCounts ? onLoadDayCounts(first, last, signal) : [],
      [onLoadDayCounts, first, last],
    ),
    onLoadDayCounts !== undefined,
  );
  if (!onLoadDayCounts) return { loading: false };
  return {
    loading: counts.loading,
    totals: counts.data
      ? new Map(counts.data.map((day) => [day.date, day.screenings]))
      : undefined,
  };
}

function DayStrip({
  today,
  range,
  view,
  volume,
  onChange,
}: {
  today: string;
  range: [number, number];
  view: StripView;
  volume: DayVolume;
  onChange: (start: number, end: number) => void;
}) {
  const descriptionId = useId();
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
  // One scale for the whole visible horizon; an all-zero horizon draws no bars.
  const busiest = Math.max(0, ...(volume.totals?.values() ?? []));

  return (
    <div
      className="minimal-strip"
      role="group"
      aria-label="Choose dates"
      data-days={dayCount}
      aria-busy={volume.loading || undefined}
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
        const total = volume.totals ? (volume.totals.get(date) ?? 0) : undefined;
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
            aria-describedby={total === undefined ? undefined : `${descriptionId}-${day}`}
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
            <span className="minimal-strip-weekday" aria-hidden>
              {dayCount === 42
                ? weekdayName(date).charAt(0)
                : day === 0
                  ? "Today"
                  : weekdayName(date)}
            </span>
            <span className="minimal-strip-date" aria-hidden>
              {dayOfMonth(date)}
            </span>
            {total !== undefined && (
              <span id={`${descriptionId}-${day}`} className="minimal-visually-hidden">
                {formatScreeningCount(total)}
              </span>
            )}
            {total !== undefined && total > 0 && (
              <span
                className="minimal-strip-volume"
                aria-hidden
                style={{ "--volume": total / busiest } as CSSProperties}
              />
            )}
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
  onLoadDayCounts,
  heading: Heading = "h1",
}: {
  start: string;
  end: string;
  today: string;
  onChange: (start: string, end: string) => void;
  onLoadDayCounts?: LoadDayCounts;
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
  const volume = useDayVolume(today, view, onLoadDayCounts);
  const { title, detail } = describePeriod(start, end, today);
  const previous = stepPeriod(start, end, today, -1);
  const next = stepPeriod(start, end, today, 1);

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
        <div className="minimal-zoom">
          <input
            type="range"
            min={1}
            max={6}
            step={1}
            value={view.weeks}
            aria-label="Zoom"
            aria-valuetext={formatWeeks(view.weeks)}
            onChange={(event) =>
              setView(anchorView(Number(event.target.value) as WeekCount, range[0]))
            }
          />
          <span aria-hidden>{formatWeeks(view.weeks)}</span>
        </div>
      </div>
      {detail && <p className="minimal-period-detail">{detail}</p>}
      <DayStrip
        today={today}
        range={range}
        view={view}
        volume={volume}
        onChange={(from, to) => onChange(addDays(today, from), addDays(today, to))}
      />
    </section>
  );
}
