import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, expect, it, vi } from "vitest";
import type { CatalogueDayCount } from "./catalogue-types";
import { PeriodPicker } from "./PeriodPicker";

// Tuesday November 3, 2026.
const today = "2026-11-03";
const CELL = 100;

afterEach(cleanup);

type LoadDayCounts = (
  start: string,
  end: string,
  signal: AbortSignal,
) => Promise<readonly CatalogueDayCount[]>;

function Harness({
  start = today,
  end = start,
  onChange,
  onLoadDayCounts,
}: {
  start?: string;
  end?: string;
  onChange: (start: string, end: string) => void;
  onLoadDayCounts?: LoadDayCounts;
}) {
  const [period, setPeriod] = useState([start, end] as const);
  return (
    <PeriodPicker
      start={period[0]}
      end={period[1]}
      today={today}
      onLoadDayCounts={onLoadDayCounts}
      onChange={(nextStart, nextEnd) => {
        onChange(nextStart, nextEnd);
        setPeriod([nextStart, nextEnd]);
      }}
    />
  );
}

function setup(start?: string, end?: string) {
  const onChange = vi.fn<(start: string, end: string) => void>();
  render(<Harness start={start} end={end} onChange={onChange} />);
  return onChange;
}

/** Lays the strip out as equal cells of CELL pixels so pointer math is real. */
function strip(cellWidth = CELL) {
  const element = screen.getByRole("group", { name: "Choose dates" });
  const days = element.querySelectorAll(".minimal-strip-day").length;
  element.getBoundingClientRect = () =>
    ({ left: 0, width: days * cellWidth, top: 0, height: 60 }) as DOMRect;
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

it("moves a one-day selection in a narrow six-week view", () => {
  /** Scenario: narrow resize grips leave the selected range's center interactive. */
  const onChange = setup();
  zoomTo(6);
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
  expect(visibleDays()).toHaveLength(42);
  expect(visibleDays()[0]).toBe("Today, Tuesday November 3rd");
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
const totals = (...screenings: number[]): CatalogueDayCount[] =>
  screenings.map((count, offset) => ({
    date: `2026-11-${String(3 + offset).padStart(2, "0")}`,
    screenings: count,
  }));
const dayButton = (name: string) => screen.getByRole("button", { name });
const volume = (name: string) =>
  dayButton(name).querySelector<HTMLElement>(".minimal-strip-volume");
const loadCounts = (counts: CatalogueDayCount[]) =>
  vi.fn<LoadDayCounts>(async () => counts);

it("requests the visible week's totals once and draws bars on one scale", async () => {
  /** Scenario: equal totals match, the busiest day is full height, and zero has no bar. */
  const onLoadDayCounts = loadCounts(totals(12, 6, 0, 6, 3, 0, 1));
  render(<Harness onChange={vi.fn()} onLoadDayCounts={onLoadDayCounts} />);

  expect(await screen.findByRole("button", { description: "12 screenings" })).toBe(
    dayButton("Today, Tuesday November 3rd"),
  );
  expect(onLoadDayCounts).toHaveBeenCalledOnce();
  expect(onLoadDayCounts.mock.calls[0]?.slice(0, 2)).toEqual(["2026-11-03", "2026-11-09"]);
  expect(volume("Today, Tuesday November 3rd")?.style.getPropertyValue("--volume")).toBe("1");
  expect(volume("Wednesday November 4th")?.style.getPropertyValue("--volume")).toBe("0.5");
  expect(volume("Friday November 6th")?.style.getPropertyValue("--volume")).toBe("0.5");
  expect(volume("Thursday November 5th")).toBeNull();
  expect(dayButton("Thursday November 5th")).toHaveAccessibleDescription("No screenings");
  expect(dayButton("Monday November 9th")).toHaveAccessibleDescription("1 screening");
});

it("renders an all-zero horizon without bars and keeps every day selectable", async () => {
  /** Scenario: a horizon with nothing scheduled has no division error and still selects. */
  const onChange = vi.fn();
  render(<Harness onChange={onChange} onLoadDayCounts={loadCounts(totals(0, 0, 0, 0, 0, 0, 0))} />);
  await screen.findAllByRole("button", { description: "No screenings" });
  expect(strip().querySelectorAll(".minimal-strip-volume")).toHaveLength(0);
  expect(strip().querySelectorAll(".minimal-strip-day")).toHaveLength(7);
  fireEvent.click(dayButton("Friday November 6th"), { detail: 0 });
  expect(onChange).toHaveBeenCalledExactlyOnceWith("2026-11-06", "2026-11-06");
});

it("reloads for a new visible horizon but not for a selection inside it", async () => {
  /** Scenario: zooming changes the counted dates; moving the period within the view does not. */
  const onLoadDayCounts = loadCounts(totals(1));
  render(<Harness onChange={vi.fn()} onLoadDayCounts={onLoadDayCounts} />);
  await screen.findByRole("button", { description: "1 screening" });
  dragOn(dayButton("Thursday November 5th"), 2, 4);
  fireEvent.click(dayButton("Monday November 9th"), { detail: 0 });
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
  expect(dayButton("Friday November 6th")).not.toHaveAccessibleDescription();
  fireEvent.click(dayButton("Friday November 6th"), { detail: 0 });
  expect(onChange).toHaveBeenCalledExactlyOnceWith("2026-11-06", "2026-11-06");
  rerender(
    <Harness onChange={onChange} onLoadDayCounts={async () => Promise.reject(new Error("offline"))} />,
  );
  await act(async () => {});
  expect(strip()).not.toHaveAttribute("aria-busy", "true");
  expect(strip().querySelectorAll(".minimal-strip-volume")).toHaveLength(0);
  expect(dayButton("Friday November 6th")).not.toHaveAccessibleDescription();
});

it("never shows counts from an older filter state or a superseded response", async () => {
  /** Scenario: a slow response for old filters arrives after the new ones were requested. */
  let resolveOld: (counts: CatalogueDayCount[]) => void = () => {};
  const old = vi.fn<LoadDayCounts>(
    (_start, _end, _signal) => new Promise((resolve) => (resolveOld = resolve)),
  );
  const current = loadCounts(totals(4));
  const { rerender } = render(<Harness onChange={vi.fn()} onLoadDayCounts={old} />);
  rerender(<Harness onChange={vi.fn()} onLoadDayCounts={current} />);
  expect(old.mock.calls[0]?.[2].aborted).toBe(true);
  await screen.findByRole("button", { description: "4 screenings" });
  await act(async () => resolveOld(totals(99)));
  expect(screen.queryByRole("button", { description: "99 screenings" })).toBeNull();
  expect(dayButton("Today, Tuesday November 3rd")).toHaveAccessibleDescription("4 screenings");
});
