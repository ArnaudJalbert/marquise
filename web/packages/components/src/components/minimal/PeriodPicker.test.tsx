import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { act, useState } from "react";
import { afterEach, expect, it, vi } from "vitest";
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

function Harness({
  start = today,
  end = start,
  onChange,
}: {
  start?: string;
  end?: string;
  onChange: (start: string, end: string) => void;
}) {
  const [period, setPeriod] = useState([start, end] as const);
  return (
    <PeriodPicker
      start={period[0]}
      end={period[1]}
      today={today}
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

const zoomChip = () => screen.getByRole("button", { name: /^Zoom/ });
const weekdayLabel = (name: string) =>
  screen.getByRole("button", { name }).querySelector(".minimal-strip-weekday")
    ?.textContent;

it("opens the phone zoom chip popover and closes it with Escape", () => {
  /** Scenario: on a phone the chip opens the slider; Escape closes it and refocuses the chip. */
  stubViewport(true);
  const onChange = setup();
  expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  const chip = zoomChip();
  expect(chip).toHaveAccessibleName("Zoom, 1 week");
  expect(chip).toHaveAttribute("aria-expanded", "false");
  expect(chip).toHaveTextContent("1 wk");
  fireEvent.click(chip);
  expect(chip).toHaveAttribute("aria-expanded", "true");
  expect(slider()).toHaveFocus();
  zoomTo(3);
  expect(visibleDays()).toHaveLength(21);
  expect(chip).toHaveTextContent("3 wk");
  expect(chip).toHaveAccessibleName("Zoom, 3 weeks");
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
  expect(screen.queryByRole("button", { name: /^Zoom/ })).not.toBeInTheDocument();
  resize(true);
  expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  expect(zoomChip()).toBeVisible();
  resize(false);
  expect(slider()).toBeVisible();
});

it("labels every day with a three-letter weekday at six weeks", () => {
  /** Scenario: the widest view still reads Tue, Wed, never single letters. */
  stubViewport(false);
  setup();
  zoomTo(6);
  expect(weekdayLabel("Wednesday November 4th")).toBe("Wed");
  expect(weekdayLabel("Today, Tuesday November 3rd")).toBe("Today");
});

it("shows today's weekday instead of Today on the phone two-week view", () => {
  /** Scenario: the narrow phone fortnight marks today with its short weekday. */
  stubViewport(true);
  setup();
  expect(weekdayLabel("Today, Tuesday November 3rd")).toBe("Today");
  fireEvent.click(zoomChip());
  zoomTo(2);
  expect(weekdayLabel("Today, Tuesday November 3rd")).toBe("Tue");
  expect(weekdayLabel("Wednesday November 4th")).toBe("Wed");
});

it("keeps Today on the desktop two-week view", () => {
  /** Scenario: only the phone fortnight swaps the Today label. */
  stubViewport(false);
  setup();
  zoomTo(2);
  expect(weekdayLabel("Today, Tuesday November 3rd")).toBe("Today");
});
