import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { PeriodPicker } from "./PeriodPicker";

// Tuesday November 3, 2026.
const today = "2026-11-03";
const CELL = 100;

afterEach(cleanup);

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

const title = () => screen.getByRole("heading", { level: 1 }).textContent;
const selectedDays = () =>
  screen
    .getAllByRole("button", { pressed: true })
    .filter((button) => button.classList.contains("minimal-strip-day"))
    .map((button) => button.getAttribute("aria-label"));

it("opens on Today in the two-week view with today marked", () => {
  /** Scenario: the default period is Today and the strip shows fourteen equal days. */
  setup();
  expect(title()).toBe("Today");
  expect(screen.getByText("Tue Nov 3")).toBeInTheDocument();
  expect(strip().querySelectorAll(".minimal-strip-day")).toHaveLength(14);
  expect(screen.getByRole("button", { name: "Today, Tuesday November 3rd" })).toHaveClass(
    "is-today",
  );
  expect(
    screen.getByRole("button", { name: "Saturday November 7th" }),
  ).toHaveClass("is-weekend");
  expect(screen.getByRole("button", { name: "2 weeks" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
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
  /** Scenario: the day strip keeps a move area between its narrow resize handles. */
  const onChange = setup();
  fireEvent.click(screen.getByRole("button", { name: "6 weeks" }));
  const element = strip(8);
  fireEvent.pointerDown(element, at(0, 8));
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

it("auto zooms to six weeks for long periods and back to two weeks for short ones", () => {
  /** Scenario: the strip widens for ranges over a week and returns to days after. */
  const onChange = setup();
  dragOn(screen.getByRole("button", { name: "Wednesday November 4th" }), 1, 12);
  expect(onChange).toHaveBeenLastCalledWith("2026-11-04", "2026-11-15");
  expect(strip().querySelectorAll(".minimal-strip-day")).toHaveLength(42);
  expect(screen.getByRole("button", { name: "6 weeks" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  fireEvent.click(screen.getByRole("button", { name: "Next period" }));
  expect(title()).toBe("Nov 16 → Nov 27");
  // Tap a day three weeks out: a single day returns to its fortnight.
  fireEvent.pointerDown(screen.getByRole("button", { name: "Tuesday November 24th" }), at(21));
  fireEvent.pointerUp(strip(), at(21));
  expect(onChange).toHaveBeenLastCalledWith("2026-11-24", "2026-11-24");
  const days = strip().querySelectorAll(".minimal-strip-day");
  expect(days).toHaveLength(14);
  expect(days[0]).toHaveAccessibleName("Tuesday November 24th");
});

it("lets the zoom buttons override auto zoom", () => {
  /** Scenario: choosing a zoom changes only the view, not the period. */
  const onChange = setup();
  fireEvent.click(screen.getByRole("button", { name: "6 weeks" }));
  expect(strip().querySelectorAll(".minimal-strip-day")).toHaveLength(42);
  fireEvent.click(screen.getByRole("button", { name: "2 weeks" }));
  expect(strip().querySelectorAll(".minimal-strip-day")).toHaveLength(14);
  expect(onChange).not.toHaveBeenCalled();
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
