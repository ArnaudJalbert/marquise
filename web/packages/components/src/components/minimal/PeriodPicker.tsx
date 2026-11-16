import { ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import {
  useCallback,
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
import { useResource } from "./use-resource";
import { addDays, formatRangeDate } from "./catalogue-format";
import type { CatalogueDayCount, MinimalCatalogueProps } from "./catalogue-types";
import {
  anchorView,
  dayOfMonth,
  daysBetween,
  describePeriod,
  fitView,
  HORIZON_DAYS,
  longMonthDay,
  monthName,
  stepPeriod,
  weekday,
  weekdayName,
  type StripView,
  type WeekCount,
} from "./period";

const formatWeeks = (weeks: WeekCount) => `${weeks} ${weeks === 1 ? "week" : "weeks"}`;

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
        aria-valuetext={formatWeeks(weeks)}
        onChange={(event) => onZoom(Number(event.target.value) as WeekCount)}
      />
      <span aria-hidden>{formatWeeks(weeks)}</span>
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

  useEffect(() => {
    if (!open) return;
    slider.current?.focus();
    const closeOutside = (event: globalThis.PointerEvent) => {
      if (!menu.current?.contains(event.target as Node)) {
        setOpen(false);
        chip.current?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, [open]);

  return (
    <div
      className="minimal-zoom-menu"
      ref={menu}
      onKeyDown={(event) => {
        if (open && event.key === "Escape") {
          setOpen(false);
          chip.current?.focus();
        }
      }}
      // Tabbing away closes the popover; taps are handled by closeOutside, and a
      // tap on the popover's label drops focus to the page (no relatedTarget).
      onBlur={(event) => {
        const next = event.relatedTarget;
        if (next && !event.currentTarget.contains(next)) setOpen(false);
      }}
    >
      <button
        ref={chip}
        type="button"
        className="minimal-zoom-chip"
        aria-label={`${weeks} wk, zoom ${formatWeeks(weeks)}`}
        aria-expanded={open}
        // Safari does not focus a tapped button, so closing would drop focus to the page.
        onClick={() => {
          if (open) chip.current?.focus();
          setOpen(!open);
        }}
      >
        {weeks} wk <span aria-hidden>▾</span>
      </button>
      {open && (
        <div className="minimal-zoom minimal-zoom-popover">
          <ZoomSlider weeks={weeks} onZoom={onZoom} inputRef={slider} />
        </div>
      )}
    </div>
  );
}

type DragMode = "draw" | "move" | "start" | "end";
interface Drag {
  mode: DragMode;
  /** First day of the starting cell; days survive a switch to or from weeks. */
  anchor: number;
  moved: boolean;
  /** Draft range in days. */
  range: [number, number];
}

/** The cell range a drag reaches at `cell`, kept within cells 0 to `lastHorizonCell`. */
function dragRange(
  { mode, anchor }: Drag,
  cell: number,
  [start, end]: [number, number],
  lastHorizonCell: number,
): [number, number] {
  if (mode === "move") {
    const shift = Math.max(-start, Math.min(lastHorizonCell - end, cell - anchor));
    return [start + shift, end + shift];
  }
  if (mode === "start") return [Math.min(cell, end), end];
  if (mode === "end") return [start, Math.max(cell, start)];
  return cell < anchor ? [cell, anchor] : [anchor, cell];
}

type LoadDayCounts = NonNullable<MinimalCatalogueProps["onLoadDayCounts"]>;

/** Screening totals by date, or undefined while unknown, plus whether a load is pending. */
interface DayVolume {
  totals?: ReadonlyMap<string, number>;
  loading: boolean;
}

const formatScreeningCount = (count: number) =>
  count === 0 ? "No screenings" : count === 1 ? "1 screening" : `${count} screenings`;

const NO_VOLUME: DayVolume = { loading: false };

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
  if (!onLoadDayCounts) return NO_VOLUME;
  return {
    loading: counts.loading,
    totals: counts.data
      ? new Map(counts.data.map((day) => [day.date, day.screenings]))
      : undefined,
  };
}

/** The draggable day strip. Without `volume`, cells draw no screening counts. */
export function DayStrip({
  today,
  range,
  view,
  volume = NO_VOLUME,
  todayAsWeekday = false,
  onChange,
}: {
  today: string;
  range: [number, number];
  view: StripView;
  volume?: DayVolume;
  /** Label today with its weekday, highlighted, where "Today" would not fit. */
  todayAsWeekday?: boolean;
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
  const phoneLayout = usePhoneLayout();
  // Long views show one cell per rolling week; every edit then covers whole weeks.
  const weekLayout = view.weeks >= (phoneLayout ? 3 : 4);
  const cellDays = weekLayout ? 7 : 1;
  const toCell = (day: number) => Math.floor(day / cellDays);
  const toDays = ([from, to]: [number, number]): [number, number] => [
    from * cellDays,
    to * cellDays + cellDays - 1,
  ];
  const selectedCells: [number, number] = [toCell(range[0]), toCell(range[1])];
  const lastHorizonCell = HORIZON_DAYS / cellDays - 1;
  const dayCount = view.weeks * 7;
  const cellCount = dayCount / cellDays;
  const firstCell = view.first / cellDays;
  const cells = Array.from({ length: cellCount }, (_, index) => firstCell + index);
  const last = view.first + dayCount - 1;
  const focusCell = Math.max(firstCell, Math.min(firstCell + cellCount - 1, toCell(start)));
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
  const { totals } = volume;
  // A cell counts the screenings of its days; a week cell sums its seven.
  const sumCellScreenings = ([from, to]: [number, number]) => {
    if (!totals) return undefined;
    let sum = 0;
    for (let day = from; day <= to; day += 1) sum += totals.get(addDays(today, day)) ?? 0;
    return sum;
  };
  const cellTotals = cells.map((cell) => sumCellScreenings(toDays([cell, cell])));
  // One scale across the drawn cells; an all-zero horizon draws no bars.
  const busiest = Math.max(0, ...cellTotals.map((total) => total ?? 0));

  return (
    <div
      className="minimal-strip"
      role="group"
      aria-label="Choose dates"
      aria-busy={volume.loading || undefined}
      style={{ "--strip-cells": cellCount } as CSSProperties}
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
        const cell = toCell(day);
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
        // Only the selected days move the selection; the rest of a partly selected block draws.
        const inSelection = day >= range[0] && day <= range[1];
        const mode: DragMode =
          inMoveArea && inSelection
            ? "move"
            : handle === "start" || handle === "end"
              ? handle
              : inSelection
                ? "move"
                : "draw";
        // jsdom has no pointer capture; browsers keep the drag on the strip.
        event.currentTarget.setPointerCapture?.(event.pointerId);
        update({
          mode,
          anchor: cell * cellDays,
          moved: false,
          range: mode === "draw" ? toDays([cell, cell]) : range,
        });
      }}
      onPointerMove={(event) => {
        const current = drag.current;
        if (!current) return;
        const cell = toCell(dayAt(event));
        const anchor = toCell(current.anchor);
        update({
          ...current,
          moved: current.moved || cell !== anchor,
          range: toDays(
            dragRange({ ...current, anchor }, cell, selectedCells, lastHorizonCell),
          ),
        });
      }}
      onPointerUp={() => {
        const current = drag.current;
        if (!current) return;
        drag.current = null;
        setDraft(null);
        // A tap anywhere picks that single day or week.
        const [nextStart, nextEnd] = current.moved
          ? current.range
          : toDays([toCell(current.anchor), toCell(current.anchor)]);
        onChange(nextStart, nextEnd);
      }}
      onPointerCancel={() => {
        drag.current = null;
        setDraft(null);
      }}
    >
      {cells.map((cell, index) => {
        const [from, to] = toDays([cell, cell]);
        const total = cellTotals[index];
        const date = addDays(today, from);
        const endDate = addDays(today, to);
        const weekend = !weekLayout && (weekday(date) === 0 || weekday(date) === 6);
        const selected = from <= end && to >= start;
        const label =
          weekLayout
            ? `${longMonthDay(date)} to ${longMonthDay(endDate)}`
            : `${from === 0 ? "Today, " : ""}${formatRangeDate(date)}`;
        return (
          <button
            key={date}
            type="button"
            className={[
              weekLayout ? "minimal-strip-week" : "minimal-strip-day",
              weekend && "is-weekend",
              !weekLayout && from === 0 && "is-today",
              selected && "is-selected",
            ]
              .filter(Boolean)
              .join(" ")}
            aria-label={label}
            // A selection that covers part of a week shows as a partial fill.
            aria-pressed={from >= start && to <= end ? true : selected ? "mixed" : false}
            aria-describedby={total === undefined ? undefined : `${descriptionId}-${cell}`}
            tabIndex={cell === focusCell ? 0 : -1}
            // Pointer taps commit on pointer up; this handles keyboard activation.
            onClick={(event) => {
              if (event.detail === 0) {
                keyboardAnchor.current = null;
                keyboardRange.current = null;
                onChange(from, to);
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
                  // The anchor is kept in days so it survives a switch between days and weeks.
                  const anchor = toCell(keyboardAnchor.current ?? from);
                  keyboardAnchor.current = anchor * cellDays;
                  const nextCell = cell + (event.key === "ArrowRight" ? 1 : -1);
                  const nextRange = toDays([
                    Math.min(anchor, nextCell),
                    Math.max(anchor, nextCell),
                  ]);
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
              {/* Each cell is named by its first day's month, shown on the first cell and where it changes. */}
              {cell === firstCell || monthName(date) !== monthName(addDays(date, -cellDays))
                ? monthName(date)
                : ""}
            </span>
            {!weekLayout && (
              <span
                className={`minimal-strip-weekday${from === 0 && todayAsWeekday ? " is-highlighted" : ""}`}
                aria-hidden
              >
                {from === 0 && !todayAsWeekday ? "Today" : weekdayName(date)}
              </span>
            )}
            <span className="minimal-strip-date" aria-hidden>
              {weekLayout ? `${dayOfMonth(date)}-${dayOfMonth(endDate)}` : dayOfMonth(date)}
            </span>
            {total !== undefined && (
              <span id={`${descriptionId}-${cell}`} className="minimal-visually-hidden">
                {formatScreeningCount(total)}
              </span>
            )}
            {total !== undefined && total > 0 && (
              <span
                className="minimal-strip-volume"
                aria-hidden
                data-volume={total / busiest}
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

/** Strip view for a period, refitted whenever the committed period changes. */
export function usePeriodView(start: string, end: string, today: string) {
  const range: [number, number] = [daysBetween(today, start), daysBetween(today, end)];
  // A fresh strip opens on one week from today.
  const [view, setView] = useState(() => fitView({ weeks: 1, first: 0 }, ...range));
  const [fitted, setFitted] = useState(`${today}/${start}/${end}`);
  // Refit the view whenever the committed period changes, wherever it came from.
  if (fitted !== `${today}/${start}/${end}`) {
    setFitted(`${today}/${start}/${end}`);
    setView(fitView(view, ...range));
  }
  return { range, view, setView };
}

/**
 * ‹ period title › that moves the period by its own length.
 * With `onOpen`, the title is a button opening a dialog that `expanded` reports.
 */
export function PeriodStepper({
  start,
  end,
  today,
  onChange,
  heading: Heading = "h1",
  onOpen,
  expanded,
}: {
  start: string;
  end: string;
  today: string;
  onChange: (start: string, end: string) => void;
  heading?: "h1" | "h2" | "strong";
  onOpen?: (opener: HTMLButtonElement) => void;
  expanded?: boolean;
}) {
  const { title } = describePeriod(start, end, today);
  const previous = stepPeriod(start, end, today, -1);
  const next = stepPeriod(start, end, today, 1);
  return (
    <div className="minimal-period-title">
      <button
        type="button"
        aria-label="Previous period"
        disabled={!previous}
        onClick={() => previous && onChange(...previous)}
      >
        <ChevronLeft aria-hidden size={18} />
      </button>
      <Heading>
        {onOpen ? (
          <button
            type="button"
            className="minimal-period-open"
            aria-haspopup="dialog"
            aria-expanded={expanded}
            onClick={(event) => onOpen(event.currentTarget)}
          >
            <span>{title}</span>
            <ChevronDown aria-hidden size={16} />
          </button>
        ) : (
          title
        )}
      </Heading>
      <button
        type="button"
        aria-label="Next period"
        disabled={!next}
        onClick={() => next && onChange(...next)}
      >
        <ChevronRight aria-hidden size={18} />
      </button>
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
  heading = "h1",
}: {
  start: string;
  end: string;
  today: string;
  onChange: (start: string, end: string) => void;
  onLoadDayCounts?: LoadDayCounts;
  heading?: "h1" | "h2";
}) {
  const { range, view, setView } = usePeriodView(start, end, today);
  const volume = useDayVolume(today, view, onLoadDayCounts);
  const { detail } = describePeriod(start, end, today);
  const phone = usePhoneLayout();
  const zoom = (weeks: WeekCount) => setView(anchorView(weeks, range[0]));

  return (
    <section className="minimal-period" aria-label="Dates">
      <div className="minimal-period-top">
        <PeriodStepper
          start={start}
          end={end}
          today={today}
          heading={heading}
          onChange={onChange}
        />
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
        volume={volume}
        todayAsWeekday={phone && view.weeks === 2}
        onChange={(from, to) => onChange(addDays(today, from), addDays(today, to))}
      />
    </section>
  );
}
