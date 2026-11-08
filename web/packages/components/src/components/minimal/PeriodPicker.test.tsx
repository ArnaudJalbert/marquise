import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, expect, it, vi } from "vitest";
import type { CatalogueDayCount } from "./catalogue-types";
import { PeriodPicker } from "./PeriodPicker";

// Tuesday November 3, 2026.
const today = "2026-11-03";
const CELL = 100;

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/** Stubs the viewport so `(max-width: 639px)` matches on a phone; returns a resize. */
function stubViewport(phone: boolean) {
  const listeners = new Set<() => void>();
  let matches = phone;
  vi.stubGlobal("matchMedia", (query: string) => ({
    get matches() {
      return matches && query === "(max-width: 639px)";
    },
    addEventListener: (_: string, listener: () => void) => listeners.add(listener),
    removeEventListener: (_: string, listener: () => void) => listeners.delete(listener),
  }));
  return (nextPhone: boolean) =>
    act(() => {
      matches = nextPhone;
      listeners.forEach((listener) => listener());
    });
}

type LoadDayCounts = (
  start: string,
  end: string,
  signal: AbortSignal,
) => Promise<readonly CatalogueDayCount[]>;

function Harness({
  today: todayDate = today,
  start = todayDate,
  end = start,
  onChange,
  onLoadDayCounts,
}: {
  start?: string;
  end?: string;
  today?: string;
  onChange: (start: string, end: string) => void;
  onLoadDayCounts?: LoadDayCounts;
}) {
  const [period, setPeriod] = useState([start, end] as const);
  return (
    <PeriodPicker
      start={period[0]}
      end={period[1]}
      today={todayDate}
      onLoadDayCounts={onLoadDayCounts}
      onChange={(nextStart, nextEnd) => {
        onChange(nextStart, nextEnd);
        setPeriod([nextStart, nextEnd]);
      }}
    />
  );
}

function setup(start?: string, end?: string, todayDate = today) {
  const onChange = vi.fn<(start: string, end: string) => void>();
  render(
    <Harness start={start ?? todayDate} end={end} today={todayDate} onChange={onChange} />,
  );
  return onChange;
}

/** Lays the strip out as equal cells of CELL pixels so pointer math is real. */
function strip(cellWidth = CELL) {
  const element = screen.getByRole("group", { name: "Choose dates" });
  const cells = element.querySelectorAll("button").length;
  element.getBoundingClientRect = () =>
    ({ left: 0, width: cells * cellWidth, top: 0, height: 60 }) as DOMRect;
  return element;
}

const at = (cell: number, cellWidth = CELL) => ({
  clientX: cell * cellWidth + cellWidth / 2,
  button: 0,
  pointerId: 1,
});

function dragOn(target: Element, from: number, to: number) {
  const element = strip();
  fireEvent.pointerDown(target, at(from));
  fireEvent.pointerMove(element, at(to));
  fireEvent.pointerUp(element, at(to));
}

const slider = () => screen.getByRole("slider", { name: "Zoom" });
const zoomTo = (weeks: number) =>
  fireEvent.change(slider(), { target: { value: String(weeks) } });
const visibleDays = () =>
  Array.from(strip().querySelectorAll(".minimal-strip-day"), (cell) =>
    cell.getAttribute("aria-label"),
  );

const blockCells = () =>
  Array.from(strip().querySelectorAll("button")).filter((cell) =>
    / to /.test(cell.getAttribute("aria-label") ?? ""),
  );
const visibleBlocks = () => blockCells().map((cell) => cell.getAttribute("aria-label"));
const block = (name: string) => screen.getByRole("button", { name });
const zoomChip = () => screen.getByRole("button", { name: /, zoom / });
const dayCell = (name: string) => screen.getByRole("button", { name });
/** The weekday label in a day cell, matched as the whole text so "Wednesday" fails. */
const weekdayIn = (name: string, label: string) => within(dayCell(name)).getByText(label);

const title = () => screen.getByRole("heading", { level: 1 }).textContent;
const selectedDays = () =>
  screen
    .getAllByRole("button", { pressed: true })
    .filter((button) => button.classList.contains("minimal-strip-day"))
    .map((button) => button.getAttribute("aria-label"));

it("opens on Today in the one-week view with today marked", () => {
  /** Scenario: the default period is Today and the strip shows today and the next six days. */
  setup();
  expect(title()).toBe("Today");
  expect(screen.getByText("Tue Nov 3")).toBeInTheDocument();
  const days = visibleDays();
  expect(days).toHaveLength(7);
  expect([days[0], days[6]]).toEqual([
    "Today, Tuesday November 3rd",
    "Monday November 9th",
  ]);
  expect(screen.getByRole("button", { name: "Today, Tuesday November 3rd" })).toHaveClass(
    "is-today",
  );
  expect(
    screen.getByRole("button", { name: "Saturday November 7th" }),
  ).toHaveClass("is-weekend");
  expect(slider()).toHaveValue("1");
  expect(slider()).toHaveAttribute("aria-valuetext", "1 week");
  expect(screen.getByText("1 week")).toBeVisible();
});

it("draws a new period by dragging across days", () => {
  /** Scenario: dragging outside the selection draws a range from the first day touched. */
  const onChange = setup();
  dragOn(screen.getByRole("button", { name: "Friday November 6th" }), 3, 5);
  expect(onChange).toHaveBeenCalledExactlyOnceWith("2026-11-06", "2026-11-08");
  expect(title()).toBe("This weekend");
  expect(screen.getByText("Nov 6 → Nov 8")).toBeInTheDocument();
});

it("draws backwards when the drag goes left", () => {
  /** Scenario: a right-to-left drag still produces an ordered range. */
  const onChange = setup();
  dragOn(screen.getByRole("button", { name: "Sunday November 8th" }), 5, 2);
  expect(onChange).toHaveBeenCalledExactlyOnceWith("2026-11-05", "2026-11-08");
});

it("shows the live range while dragging and commits only on release", () => {
  /** Scenario: the URL is not touched until the pointer is released. */
  const onChange = setup();
  const element = strip();
  fireEvent.pointerDown(screen.getByRole("button", { name: "Thursday November 5th" }), at(2));
  fireEvent.pointerMove(element, at(4));
  expect(onChange).not.toHaveBeenCalled();
  expect(selectedDays()).toEqual([
    "Thursday November 5th",
    "Friday November 6th",
    "Saturday November 7th",
  ]);
  fireEvent.pointerUp(element, at(4));
  expect(onChange).toHaveBeenCalledOnce();
});

it("moves the selected window by dragging inside it", () => {
  /** Scenario: dragging the window keeps its length and shifts its dates. */
  const onChange = setup("2026-11-04", "2026-11-05");
  dragOn(screen.getByRole("button", { name: "Wednesday November 4th" }), 1, 4);
  expect(onChange).toHaveBeenCalledExactlyOnceWith("2026-11-07", "2026-11-08");
});

it("moves a one-day selection in a narrow three-week view", () => {
  /** Scenario: narrow resize grips leave the selected range's center interactive. */
  const onChange = setup();
  zoomTo(3);
  const element = strip(8);
  const window = element.querySelector(".minimal-strip-window") as HTMLElement;
  window.getBoundingClientRect = () =>
    ({ left: 0, right: 8, width: 8, top: 0, bottom: 60, height: 60 }) as DOMRect;
  const startHandle = element.querySelector('[data-handle="start"]') as Element;
  fireEvent.pointerDown(startHandle, at(0, 8));
  fireEvent.pointerMove(element, at(1, 8));
  fireEvent.pointerUp(element, at(1, 8));
  expect(onChange).toHaveBeenCalledExactlyOnceWith("2026-11-04", "2026-11-04");
});

it("resizes the window from either edge", () => {
  /** Scenario: dragging a handle moves only that edge, never past the other. */
  const onChange = setup("2026-11-04", "2026-11-05");
  const handle = (edge: string) =>
    strip().querySelector(`[data-handle="${edge}"]`) as Element;
  dragOn(handle("end"), 2, 6);
  expect(onChange).toHaveBeenLastCalledWith("2026-11-04", "2026-11-09");
  dragOn(handle("start"), 1, 3);
  expect(onChange).toHaveBeenLastCalledWith("2026-11-06", "2026-11-09");
  dragOn(handle("start"), 3, 9);
  expect(onChange).toHaveBeenLastCalledWith("2026-11-09", "2026-11-09");
});

it("picks a single day on tap, inside or outside the window", () => {
  /** Scenario: tapping a day without dragging selects just that day. */
  const onChange = setup("2026-11-04", "2026-11-07");
  zoomTo(2);
  const element = strip();
  fireEvent.pointerDown(screen.getByRole("button", { name: "Thursday November 5th" }), at(2));
  fireEvent.pointerUp(element, at(2));
  expect(onChange).toHaveBeenLastCalledWith("2026-11-05", "2026-11-05");
  fireEvent.pointerDown(screen.getByRole("button", { name: "Wednesday November 11th" }), at(8));
  fireEvent.pointerUp(element, at(8));
  expect(onChange).toHaveBeenLastCalledWith("2026-11-11", "2026-11-11");
  expect(title()).toBe("Wed Nov 11");
});

it("picks a single day from the keyboard and moves focus with arrows", () => {
  /** Scenario: keyboard users reach and choose days without a pointer. */
  const onChange = setup();
  const todayCell = screen.getByRole("button", { name: "Today, Tuesday November 3rd" });
  expect(todayCell).toHaveAttribute("tabindex", "0");
  todayCell.focus();
  fireEvent.keyDown(todayCell, { key: "ArrowRight" });
  const tomorrow = screen.getByRole("button", { name: "Wednesday November 4th" });
  expect(tomorrow).toHaveFocus();
  fireEvent.click(tomorrow);
  expect(onChange).toHaveBeenCalledExactlyOnceWith("2026-11-04", "2026-11-04");
  expect(title()).toBe("Tomorrow");
});

it("extends a period with Shift and arrow keys", () => {
  /** Scenario: keyboard users select a multi-day period without a pointer. */
  const onChange = setup();
  const todayCell = screen.getByRole("button", { name: "Today, Tuesday November 3rd" });
  todayCell.focus();
  fireEvent.keyDown(todayCell, { key: "ArrowRight", shiftKey: true });
  const tomorrow = screen.getByRole("button", { name: "Wednesday November 4th" });
  expect(tomorrow).toHaveFocus();
  expect(onChange).toHaveBeenLastCalledWith("2026-11-03", "2026-11-04");
  fireEvent.keyDown(tomorrow, { key: "ArrowRight", shiftKey: true });
  expect(screen.getByRole("button", { name: "Thursday November 5th" })).toHaveFocus();
  expect(onChange).toHaveBeenLastCalledWith("2026-11-03", "2026-11-05");
  expect(title()).toBe("Nov 3 → Nov 5");
});

it("resets the keyboard anchor when stepping changes the period", () => {
  /** Scenario: a new range starts from the newly focused day after stepping. */
  const onChange = setup();
  const todayCell = screen.getByRole("button", { name: "Today, Tuesday November 3rd" });
  todayCell.focus();
  fireEvent.keyDown(todayCell, { key: "ArrowRight", shiftKey: true });
  fireEvent.click(screen.getByRole("button", { name: "Next period" }));
  const nov5 = screen.getByRole("button", { name: "Thursday November 5th" });
  nov5.focus();
  fireEvent.keyDown(nov5, { key: "ArrowRight", shiftKey: true });
  expect(onChange).toHaveBeenLastCalledWith("2026-11-05", "2026-11-06");
  expect(title()).toBe("Nov 5 → Nov 6");
});

it("resets the keyboard anchor after focus leaves the strip", () => {
  /** Scenario: a fresh keyboard range starts after using an external control. */
  const onChange = setup();
  const todayCell = screen.getByRole("button", { name: "Today, Tuesday November 3rd" });
  todayCell.focus();
  fireEvent.keyDown(todayCell, { key: "ArrowRight", shiftKey: true });
  slider().focus();
  const nov5 = screen.getByRole("button", { name: "Thursday November 5th" });
  nov5.focus();
  fireEvent.keyDown(nov5, { key: "ArrowRight", shiftKey: true });
  expect(onChange).toHaveBeenLastCalledWith("2026-11-05", "2026-11-06");
});

it("steps the period by its own length and disables stepping before today", () => {
  /** Scenario: ‹ › move a day by a day and a weekend to the next weekend. */
  const onChange = setup();
  const previous = screen.getByRole("button", { name: "Previous period" });
  const next = screen.getByRole("button", { name: "Next period" });
  expect(previous).toBeDisabled();
  fireEvent.click(next);
  expect(onChange).toHaveBeenLastCalledWith("2026-11-04", "2026-11-04");
  expect(title()).toBe("Tomorrow");
  dragOn(screen.getByRole("button", { name: "Friday November 6th" }), 3, 5);
  fireEvent.click(next);
  expect(onChange).toHaveBeenLastCalledWith("2026-11-13", "2026-11-15");
  expect(title()).toBe("Next weekend");
  fireEvent.click(previous);
  expect(title()).toBe("This weekend");
});

it("pans to a stepped period outside the view at the same zoom", () => {
  /** Scenario: stepping past the visible week shows the next week, still one week wide. */
  setup("2026-11-09");
  fireEvent.click(screen.getByRole("button", { name: "Next period" }));
  expect(title()).toBe("Tue Nov 10");
  const days = visibleDays();
  expect(days).toHaveLength(7);
  expect(days[0]).toBe("Tuesday November 10th");
  expect(selectedDays()).toEqual(["Tuesday November 10th"]);
});

it("widens to fit a long period and never narrows on its own", () => {
  /** Scenario: the view grows to the weeks a period spans and keeps that zoom after. */
  setup("2026-11-04", "2026-11-15");
  expect(visibleDays()).toHaveLength(14);
  expect(slider()).toHaveAttribute("aria-valuetext", "2 weeks");
  fireEvent.click(screen.getByRole("button", { name: "Next period" }));
  expect(title()).toBe("Nov 16 → Nov 27");
  expect(visibleDays()).toHaveLength(21);
  expect(visibleDays()[0]).toBe("Tuesday November 10th");
  expect(screen.getByText("3 weeks")).toBeVisible();
  // Tap a single day: the view stays three weeks wide.
  fireEvent.pointerDown(screen.getByRole("button", { name: "Tuesday November 24th" }), at(14));
  fireEvent.pointerUp(strip(), at(14));
  expect(title()).toBe("Tue Nov 24");
  expect(visibleDays()).toHaveLength(21);
  expect(visibleDays()[0]).toBe("Tuesday November 10th");
  expect(slider()).toHaveValue("3");
});

it("zooms by whole weeks from the selection start without changing the selection", () => {
  /** Scenario: the slider re-anchors the view on the selected week and leaves the period alone. */
  const onChange = setup("2026-11-20");
  expect(visibleDays()[0]).toBe("Tuesday November 17th");
  zoomTo(2);
  expect(visibleDays()).toHaveLength(14);
  expect(visibleDays()[0]).toBe("Tuesday November 17th");
  expect(slider()).toHaveAttribute("aria-valuetext", "2 weeks");
  zoomTo(6);
  expect(visibleBlocks()).toHaveLength(6);
  expect(visibleBlocks()[0]).toBe("November 3 to November 9");
  zoomTo(1);
  expect(visibleDays()).toEqual([
    "Tuesday November 17th",
    "Wednesday November 18th",
    "Thursday November 19th",
    "Friday November 20th",
    "Saturday November 21st",
    "Sunday November 22nd",
    "Monday November 23rd",
  ]);
  expect(onChange).not.toHaveBeenCalled();
  expect(title()).toBe("Fri Nov 20");
});

it("keeps a zoomed view inside the six-week horizon", () => {
  /** Scenario: zooming near the end of the strip never shows dates past the horizon. */
  setup("2026-12-10");
  expect(visibleDays()[0]).toBe("Tuesday December 8th");
  zoomTo(3);
  const days = visibleDays();
  expect(days).toHaveLength(21);
  expect([days[0], days[20]]).toEqual([
    "Tuesday November 24th",
    "Monday December 14th",
  ]);
  expect(slider()).toHaveAttribute("min", "1");
  expect(slider()).toHaveAttribute("max", "6");
  expect(slider()).toHaveAttribute("step", "1");
});

it("drops a cancelled drag", () => {
  /** Scenario: a cancelled pointer leaves the period unchanged. */
  const onChange = setup();
  const element = strip();
  fireEvent.pointerDown(screen.getByRole("button", { name: "Friday November 6th" }), at(3));
  fireEvent.pointerMove(element, at(5));
  fireEvent.pointerCancel(element);
  expect(onChange).not.toHaveBeenCalled();
  expect(title()).toBe("Today");
  expect(selectedDays()).toEqual(["Today, Tuesday November 3rd"]);
});

/** Daily totals for consecutive dates from today. */
const buildTotals = (...screenings: number[]): CatalogueDayCount[] =>
  screenings.map((count, offset) => ({
    date: `2026-11-${String(3 + offset).padStart(2, "0")}`,
    screenings: count,
  }));
const readVolume = (name: string) =>
  dayCell(name).querySelector("[data-volume]")?.getAttribute("data-volume");
const loadCounts = (counts: CatalogueDayCount[]) =>
  vi.fn<LoadDayCounts>(async () => counts);

it("requests the visible week's totals once and draws bars on one scale", async () => {
  /** Scenario: equal totals match, the busiest day is full height, and zero has no bar. */
  const onLoadDayCounts = loadCounts(buildTotals(12, 6, 0, 6, 3, 0, 1));
  render(<Harness onChange={vi.fn()} onLoadDayCounts={onLoadDayCounts} />);

  expect(await screen.findByRole("button", { description: "12 screenings" })).toBe(
    dayCell("Today, Tuesday November 3rd"),
  );
  expect(onLoadDayCounts).toHaveBeenCalledOnce();
  expect(onLoadDayCounts.mock.calls[0]?.slice(0, 2)).toEqual(["2026-11-03", "2026-11-09"]);
  expect(readVolume("Today, Tuesday November 3rd")).toBe("1");
  expect(readVolume("Wednesday November 4th")).toBe("0.5");
  expect(readVolume("Friday November 6th")).toBe("0.5");
  expect(readVolume("Thursday November 5th")).toBeUndefined();
  expect(dayCell("Thursday November 5th")).toHaveAccessibleDescription("No screenings");
  expect(dayCell("Monday November 9th")).toHaveAccessibleDescription("1 screening");
});

it("renders an all-zero horizon without bars and keeps every day selectable", async () => {
  /** Scenario: a horizon with nothing scheduled has no division error and still selects. */
  const onChange = vi.fn();
  render(<Harness onChange={onChange} onLoadDayCounts={loadCounts(buildTotals(0, 0, 0, 0, 0, 0, 0))} />);
  const days = await screen.findAllByRole("button", { description: "No screenings" });
  expect(days).toHaveLength(7);
  expect(strip().querySelectorAll("[data-volume]")).toHaveLength(0);
  fireEvent.click(dayCell("Friday November 6th"), { detail: 0 });
  expect(onChange).toHaveBeenCalledExactlyOnceWith("2026-11-06", "2026-11-06");
});

it("reloads for a new visible horizon but not for a selection inside it", async () => {
  /** Scenario: zooming changes the counted dates; moving the period within the view does not. */
  const onLoadDayCounts = loadCounts(buildTotals(1));
  render(<Harness onChange={vi.fn()} onLoadDayCounts={onLoadDayCounts} />);
  await screen.findByRole("button", { description: "1 screening" });
  dragOn(dayCell("Thursday November 5th"), 2, 4);
  fireEvent.click(dayCell("Monday November 9th"), { detail: 0 });
  await act(async () => {});
  expect(onLoadDayCounts).toHaveBeenCalledOnce();
  zoomTo(2);
  await act(async () => {});
  expect(onLoadDayCounts).toHaveBeenCalledTimes(2);
  expect(onLoadDayCounts.mock.calls[1]?.slice(0, 2)).toEqual(["2026-11-03", "2026-11-16"]);
});

it("shows no counts while loading or after a failure, and the strip stays usable", async () => {
  /** Scenario: pending and failed requests never look like zero screenings. */
  const onChange = vi.fn();
  const { rerender } = render(
    <Harness onChange={onChange} onLoadDayCounts={() => new Promise(() => {})} />,
  );
  expect(strip()).toHaveAttribute("aria-busy", "true");
  expect(dayCell("Friday November 6th")).not.toHaveAccessibleDescription();
  fireEvent.click(dayCell("Friday November 6th"), { detail: 0 });
  expect(onChange).toHaveBeenCalledExactlyOnceWith("2026-11-06", "2026-11-06");
  rerender(
    <Harness onChange={onChange} onLoadDayCounts={async () => Promise.reject(new Error("offline"))} />,
  );
  await act(async () => {});
  expect(strip()).not.toHaveAttribute("aria-busy", "true");
  expect(strip().querySelectorAll("[data-volume]")).toHaveLength(0);
  expect(dayCell("Friday November 6th")).not.toHaveAccessibleDescription();
});

it("never shows counts from an older filter state or a superseded response", async () => {
  /** Scenario: a slow response for old filters arrives after the new ones were requested. */
  let resolveOld: (counts: CatalogueDayCount[]) => void = () => {};
  const old = vi.fn<LoadDayCounts>(
    (_start, _end, _signal) => new Promise((resolve) => (resolveOld = resolve)),
  );
  const current = loadCounts(buildTotals(4));
  const { rerender } = render(<Harness onChange={vi.fn()} onLoadDayCounts={old} />);
  rerender(<Harness onChange={vi.fn()} onLoadDayCounts={current} />);
  expect(old.mock.calls[0]?.[2].aborted).toBe(true);
  await screen.findByRole("button", { description: "4 screenings" });
  await act(async () => resolveOld(buildTotals(99)));
  expect(screen.queryByRole("button", { description: "99 screenings" })).toBeNull();
  expect(dayCell("Today, Tuesday November 3rd")).toHaveAccessibleDescription("4 screenings");
});

it("sums each week block's visible days and scales bars across the drawn blocks", async () => {
  /** Scenario: a block counts its seven days, a zero week has no bar, the busiest block is full height, and days outside the horizon never count. */
  stubViewport(false);
  const onLoadDayCounts = loadCounts([
    { date: "2026-11-02", screenings: 50 },
    ...buildTotals(1, 1, 1, 1, 1, 1, 1, ...Array(7).fill(0), 14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7),
    { date: "2026-12-01", screenings: 50 },
  ]);
  render(<Harness onChange={vi.fn()} onLoadDayCounts={onLoadDayCounts} />);
  zoomTo(4);
  await screen.findByRole("button", { description: "14 screenings" });
  expect(onLoadDayCounts).toHaveBeenLastCalledWith("2026-11-03", "2026-11-30", expect.anything());
  expect(blockCells()).toHaveLength(4);
  expect(block("November 3 to November 9")).toHaveAccessibleDescription("7 screenings");
  expect(readVolume("November 3 to November 9")).toBe("0.5");
  expect(block("November 10 to November 16")).toHaveAccessibleDescription("No screenings");
  expect(readVolume("November 10 to November 16")).toBeUndefined();
  expect(readVolume("November 17 to November 23")).toBe("1");
  expect(block("November 24 to November 30")).toHaveAccessibleDescription("7 screenings");
  expect(readVolume("November 24 to November 30")).toBe("0.5");
  expect(strip().querySelectorAll("[data-volume]")).toHaveLength(3);
});

it("shows days up to three weeks and week blocks from four on desktop", () => {
  /** Scenario: the desktop strip collapses into blocks only at 4 to 6 weeks. */
  stubViewport(false);
  setup();
  zoomTo(3);
  expect(visibleDays()).toHaveLength(21);
  expect(visibleBlocks()).toHaveLength(0);
  for (const weeks of [4, 5, 6]) {
    zoomTo(weeks);
    expect(visibleDays()).toHaveLength(0);
    expect(visibleBlocks()).toHaveLength(weeks);
  }
});

it("shows week blocks from three weeks at the phone breakpoint, switching live", () => {
  /** Scenario: phones collapse at 3 weeks, and crossing the breakpoint switches modes. */
  const setPhone = stubViewport(true);
  setup();
  fireEvent.click(zoomChip());
  zoomTo(2);
  expect(visibleDays()).toHaveLength(14);
  zoomTo(3);
  expect(visibleDays()).toHaveLength(0);
  expect(visibleBlocks()).toHaveLength(3);
  setPhone(false);
  expect(visibleDays()).toHaveLength(21);
  expect(visibleBlocks()).toHaveLength(0);
  setPhone(true);
  expect(visibleBlocks()).toHaveLength(3);
  fireEvent.click(zoomChip());
  for (const weeks of [4, 5, 6]) {
    zoomTo(weeks);
    expect(visibleDays()).toHaveLength(0);
    expect(visibleBlocks()).toHaveLength(weeks);
  }
});

it("keeps the drag anchor when the phone breakpoint flips mid-drag", () => {
  /** Scenario: a drag started on a week block finishes on days from that week's first day. */
  const setPhone = stubViewport(true);
  const onChange = setup();
  fireEvent.click(zoomChip());
  zoomTo(3);
  strip();
  fireEvent.pointerDown(block("November 10 to November 16"), at(1));
  setPhone(false);
  const element = strip();
  fireEvent.pointerMove(element, at(16));
  fireEvent.pointerUp(element, at(16));
  expect(onChange).toHaveBeenLastCalledWith("2026-11-10", "2026-11-19");
});

it("labels each block with its month change, day span and full range", () => {
  /** Scenario: blocks run in 7-day steps from today and name a month only when it changes. */
  stubViewport(false);
  setup("2026-11-07", "2026-11-07", "2026-11-07");
  zoomTo(6);
  expect(visibleBlocks()).toEqual([
    "November 7 to November 13",
    "November 14 to November 20",
    "November 21 to November 27",
    "November 28 to December 4",
    "December 5 to December 11",
    "December 12 to December 18",
  ]);
  expect(blockCells().map((cell) => cell.textContent)).toEqual([
    "Nov7-13",
    "14-20",
    "21-27",
    "28-4",
    "Dec5-11",
    "12-18",
  ]);
});

it("names each block by the month of its first day, always on the first block", () => {
  /** Scenario: a block crossing into a new month keeps its start month; the next one names the new month. */
  stubViewport(false);
  setup("2026-11-28", "2026-11-28", "2026-11-28");
  zoomTo(6);
  expect(blockCells().map((cell) => cell.textContent)).toEqual([
    "Nov28-4",
    "Dec5-11",
    "12-18",
    "19-25",
    "26-1",
    "Jan2-8",
  ]);
  cleanup();
  setup("2026-12-08");
  zoomTo(4);
  expect(blockCells().map((cell) => cell.textContent)).toEqual([
    "Nov17-23",
    "24-30",
    "Dec1-7",
    "8-14",
  ]);
});

it("names the month on the first cell and where the month changes, in both modes", () => {
  /** Scenario: days label their month at the view start and on the 1st; blocks label it on the first block and when their first day's month differs from the block before. */
  stubViewport(false);
  setup("2026-11-24");
  zoomTo(2);
  const cellText = (name: string) => block(name).textContent;
  expect(cellText("Tuesday November 24th")).toBe("NovTue24");
  expect(cellText("Wednesday November 25th")).toBe("Wed25");
  expect(cellText("Tuesday December 1st")).toBe("DecTue1");
  zoomTo(6);
  expect(blockCells().map((cell) => cell.textContent)).toEqual([
    "Nov3-9",
    "10-16",
    "17-23",
    "24-30",
    "Dec1-7",
    "8-14",
  ]);
  expect(block("November 3 to November 9")).not.toHaveClass("is-today");
});

it("picks a whole block on tap and draws across blocks", () => {
  /** Scenario: block taps and draws commit whole weeks. */
  stubViewport(false);
  const onChange = setup();
  zoomTo(4);
  const element = strip();
  fireEvent.pointerDown(block("November 17 to November 23"), at(2));
  fireEvent.pointerUp(element, at(2));
  expect(onChange).toHaveBeenLastCalledWith("2026-11-17", "2026-11-23");
  expect(block("November 17 to November 23")).toHaveAttribute("aria-pressed", "true");
  dragOn(block("November 10 to November 16"), 1, 0);
  expect(onChange).toHaveBeenLastCalledWith("2026-11-03", "2026-11-16");
  expect(title()).toBe("Nov 3 → Nov 16");
});

it("snaps resized edges to block edges and moves by whole blocks within the horizon", () => {
  /** Scenario: handles and moves in block mode keep the range block-aligned. */
  stubViewport(false);
  const onChange = setup("2026-11-07", "2026-11-08");
  zoomTo(6);
  const handle = (edge: string) =>
    strip().querySelector(`[data-handle="${edge}"]`) as Element;
  dragOn(handle("end"), 0, 1);
  expect(onChange).toHaveBeenLastCalledWith("2026-11-03", "2026-11-16");
  dragOn(handle("start"), 0, 1);
  expect(onChange).toHaveBeenLastCalledWith("2026-11-10", "2026-11-16");
  dragOn(handle("end"), 1, 2);
  expect(onChange).toHaveBeenLastCalledWith("2026-11-10", "2026-11-23");
  dragOn(block("November 10 to November 16"), 1, 3);
  expect(onChange).toHaveBeenLastCalledWith("2026-11-24", "2026-12-07");
  dragOn(block("November 24 to November 30"), 3, 5);
  expect(onChange).toHaveBeenLastCalledWith("2026-12-01", "2026-12-14");
});

it("draws from an unselected part of a partly selected block and moves only from selected days", () => {
  /** Scenario: with Nov 12 picked, pressing elsewhere in its block draws; pressing Nov 12 moves it. */
  stubViewport(false);
  const onChange = setup("2026-11-12");
  zoomTo(4);
  const dayWidth = CELL / 7;
  const atDay = (day: number) => ({ ...at(0), clientX: day * dayWidth + dayWidth / 2 });
  // The view opens on Nov 10, so day 3 is Nov 13 (unselected) and day 2 is Nov 12.
  let element = strip();
  fireEvent.pointerDown(block("November 10 to November 16"), atDay(3));
  fireEvent.pointerMove(element, at(1));
  fireEvent.pointerUp(element, at(1));
  expect(onChange).toHaveBeenLastCalledWith("2026-11-10", "2026-11-23");
  cleanup();
  const moved = setup("2026-11-12");
  zoomTo(4);
  element = strip();
  fireEvent.pointerDown(block("November 10 to November 16"), atDay(2));
  fireEvent.pointerMove(element, at(1));
  fireEvent.pointerUp(element, at(1));
  expect(moved).toHaveBeenLastCalledWith("2026-11-17", "2026-11-23");
});

it("moves, selects and extends blocks from the keyboard", () => {
  /** Scenario: arrows move between blocks, Enter selects one, Shift+arrows extend by blocks. */
  stubViewport(false);
  const onChange = setup();
  zoomTo(4);
  const first = block("November 3 to November 9");
  expect(first).toHaveAttribute("tabindex", "0");
  first.focus();
  fireEvent.keyDown(first, { key: "ArrowRight" });
  const second = block("November 10 to November 16");
  expect(second).toHaveFocus();
  fireEvent.click(second);
  expect(onChange).toHaveBeenLastCalledWith("2026-11-10", "2026-11-16");
  fireEvent.keyDown(second, { key: "ArrowRight", shiftKey: true });
  const third = block("November 17 to November 23");
  expect(third).toHaveFocus();
  expect(onChange).toHaveBeenLastCalledWith("2026-11-10", "2026-11-23");
  fireEvent.keyDown(third, { key: "ArrowLeft", shiftKey: true });
  fireEvent.keyDown(second, { key: "ArrowLeft", shiftKey: true });
  expect(first).toHaveFocus();
  expect(onChange).toHaveBeenLastCalledWith("2026-11-03", "2026-11-16");
});

it("draws a non-aligned selection as a partial fill and keeps it through zooming", () => {
  /** Scenario: a weekend or a single day stays as picked while the strip shows blocks. */
  stubViewport(false);
  const onChange = setup("2026-11-06", "2026-11-08");
  const window = () =>
    (strip().querySelector(".minimal-strip-window") as HTMLElement).style;
  zoomTo(5);
  expect(window().left).toBe(`${(3 / 35) * 100}%`);
  expect(window().width).toBe(`${(3 / 35) * 100}%`);
  expect(block("November 3 to November 9")).toHaveAttribute("aria-pressed", "mixed");
  expect(block("November 10 to November 16")).toHaveAttribute("aria-pressed", "false");
  zoomTo(1);
  zoomTo(6);
  expect(onChange).not.toHaveBeenCalled();
  expect(title()).toBe("This weekend");
  cleanup();
  setup("2026-11-12");
  zoomTo(4);
  expect(window().left).toBe(`${(2 / 28) * 100}%`);
  expect(window().width).toBe(`${(1 / 28) * 100}%`);
  expect(title()).toBe("Thu Nov 12");
});

it("opens the phone zoom chip popover and closes it with Escape", () => {
  /** Scenario: on a phone the chip opens the slider; Escape closes it and refocuses the chip. */
  stubViewport(true);
  const onChange = setup();
  expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  const chip = zoomChip();
  expect(chip).toHaveAccessibleName("1 wk, zoom 1 week");
  expect(chip).toHaveAttribute("aria-expanded", "false");
  expect(chip).toHaveTextContent("1 wk");
  fireEvent.click(chip);
  expect(chip).toHaveAttribute("aria-expanded", "true");
  expect(slider()).toHaveFocus();
  zoomTo(3);
  expect(visibleBlocks()).toHaveLength(3);
  expect(chip).toHaveTextContent("3 wk");
  expect(chip).toHaveAccessibleName("3 wk, zoom 3 weeks");
  expect(screen.getByText("3 weeks")).toBeVisible();
  fireEvent.keyDown(slider(), { key: "Escape" });
  expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  expect(chip).toHaveAttribute("aria-expanded", "false");
  expect(chip).toHaveFocus();
  expect(onChange).not.toHaveBeenCalled();
});

it("closes the phone zoom popover on a tap outside it", () => {
  /** Scenario: tapping elsewhere closes the popover and returns focus to the chip. */
  stubViewport(true);
  setup();
  fireEvent.click(zoomChip());
  fireEvent.pointerDown(slider());
  expect(slider()).toBeInTheDocument();
  fireEvent.pointerDown(screen.getByRole("heading", { level: 1 }));
  expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  expect(zoomChip()).toHaveAttribute("aria-expanded", "false");
  expect(zoomChip()).toHaveFocus();
});

it("keeps focus on the chip when a tap on it closes the popover", () => {
  /** Scenario: Safari does not focus a tapped button, so closing from the chip refocuses it. */
  stubViewport(true);
  setup();
  fireEvent.click(zoomChip());
  expect(slider()).toHaveFocus();
  fireEvent.click(zoomChip());
  expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  expect(zoomChip()).toHaveAttribute("aria-expanded", "false");
  expect(zoomChip()).toHaveFocus();
});

it("closes the phone zoom popover when focus tabs away from it", () => {
  /** Scenario: keyboard focus leaving the chip and slider closes the popover. */
  stubViewport(true);
  setup();
  fireEvent.click(zoomChip());
  fireEvent.blur(slider(), { relatedTarget: zoomChip() });
  expect(slider()).toBeInTheDocument();
  // A tap on the popover's label or padding drops focus to the page.
  fireEvent.blur(slider(), { relatedTarget: null });
  expect(slider()).toBeInTheDocument();
  fireEvent.blur(slider(), {
    relatedTarget: screen.getByRole("button", { name: "Next period" }),
  });
  expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  expect(zoomChip()).toHaveAttribute("aria-expanded", "false");
});

it("swaps the chip and the inline slider when the viewport crosses the breakpoint", () => {
  /** Scenario: rotating or resizing keeps the header matched to the live breakpoint. */
  const resize = stubViewport(false);
  setup();
  expect(slider()).toBeVisible();
  expect(screen.queryByRole("button", { name: /, zoom / })).not.toBeInTheDocument();
  resize(true);
  expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  expect(zoomChip()).toBeVisible();
  resize(false);
  expect(slider()).toBeVisible();
});

it("labels every day with a three-letter weekday at three weeks", () => {
  /** Scenario: the widest day view still reads Tue, Wed, never single letters. */
  stubViewport(false);
  setup();
  zoomTo(3);
  expect(weekdayIn("Wednesday November 4th", "Wed")).toBeInTheDocument();
  expect(dayCell("Today, Tuesday November 3rd")).toHaveTextContent("Today");
});

it("shows today's weekday instead of Today on the phone two-week view", () => {
  /** Scenario: the narrow phone fortnight marks today with its short weekday. */
  stubViewport(true);
  setup();
  expect(dayCell("Today, Tuesday November 3rd")).toHaveTextContent("Today");
  fireEvent.click(zoomChip());
  zoomTo(2);
  expect(weekdayIn("Today, Tuesday November 3rd", "Tue")).toBeInTheDocument();
  expect(dayCell("Today, Tuesday November 3rd")).not.toHaveTextContent("Today");
  expect(weekdayIn("Wednesday November 4th", "Wed")).toBeInTheDocument();
});

it("keeps Today on the desktop two-week view", () => {
  /** Scenario: only the phone fortnight swaps the Today label. */
  stubViewport(false);
  setup();
  zoomTo(2);
  expect(dayCell("Today, Tuesday November 3rd")).toHaveTextContent("Today");
});
