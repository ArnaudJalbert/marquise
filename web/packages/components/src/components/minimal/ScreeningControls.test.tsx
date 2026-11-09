import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ActiveCatalogueSelection } from "./catalogue-types";
import { ScreeningControls } from "./ScreeningControls";

let reportHeader: IntersectionObserverCallback = () => {};

class HeaderObserver {
  constructor(callback: IntersectionObserverCallback) {
    reportHeader = callback;
  }
  observe() {}
  disconnect() {}
}

beforeEach(() => vi.stubGlobal("IntersectionObserver", HeaderObserver));
afterEach(() => vi.unstubAllGlobals());

/** Reports the expanded header as scrolled above the viewport, or back in view. */
function scrollHeader(position: "past" | "visible") {
  const entry = {
    isIntersecting: position === "visible",
    boundingClientRect: { top: position === "past" ? -300 : 0 },
  } as IntersectionObserverEntry;
  act(() => reportHeader([entry], {} as IntersectionObserver));
}

const cinemas = [
  { id: "a", name: "Cinema A" },
  { id: "b", name: "Cinema B" },
];

function Controls({ initial }: { initial?: Partial<ActiveCatalogueSelection> }) {
  const [selection, setSelection] = useState<ActiveCatalogueSelection>({
    start: "2026-10-30",
    end: "2026-10-30",
    title: "",
    filters: [],
    ...initial,
  });
  return (
    <ScreeningControls
      selection={selection}
      onSelection={setSelection}
      cinemas={cinemas}
      today="2026-10-30"
    />
  );
}

const bar = () => screen.getByRole("region", { name: "Screening controls" });
const expandedHeader = () => document.querySelector<HTMLElement>(".minimal-screening-header")!;

it("collapses into a one-row bar once the header scrolls past, and back", () => {
  /** Scenario: scrolling past the large header shows the compact bar; scrolling up hides it. */
  render(<Controls />);
  expect(screen.queryByRole("region", { name: "Screening controls" })).toBeNull();

  scrollHeader("past");
  const row = within(bar());
  expect(row.getByRole("button", { name: "Previous period" })).toBeInTheDocument();
  expect(row.getByText("Today", { selector: "strong" })).toBeInTheDocument();
  expect(row.getByRole("button", { name: "Next period" })).toBeInTheDocument();
  expect(row.getByRole("group", { name: "Choose dates" })).toBeInTheDocument();
  expect(row.getByRole("searchbox", { name: "Search movies" })).toBeInTheDocument();
  expect(row.getByRole("button", { name: "Filters" })).toHaveAttribute("aria-expanded", "false");
  expect(expandedHeader()).toHaveAttribute("inert");

  scrollHeader("visible");
  expect(screen.queryByRole("region", { name: "Screening controls" })).toBeNull();
  expect(expandedHeader()).not.toHaveAttribute("inert");
});

it("ignores the header while it is still below the viewport top", () => {
  /** Scenario: a header not yet reached (below the fold) never shows the bar. */
  render(<Controls />);
  const entry = {
    isIntersecting: false,
    boundingClientRect: { top: 900 },
  } as IntersectionObserverEntry;
  act(() => reportHeader([entry], {} as IntersectionObserver));
  expect(screen.queryByRole("region", { name: "Screening controls" })).toBeNull();
});

it("steps the period and picks a day from the bar", () => {
  /** Scenario: the bar's stepper and mini strip change the same period as the header. */
  render(<Controls />);
  scrollHeader("past");
  fireEvent.click(within(bar()).getByRole("button", { name: "Next period" }));
  expect(within(bar()).getByText("Tomorrow", { selector: "strong" })).toBeInTheDocument();
  expect(within(expandedHeader()).getByRole("heading", { name: "Tomorrow" })).toBeInTheDocument();

  fireEvent.click(within(bar()).getByRole("button", { name: "Today, Friday October 30th" }), { detail: 0 });
  expect(within(bar()).getByText("Today", { selector: "strong" })).toBeInTheDocument();
});

it("edits the same chips from the Filters panel as the expanded header", () => {
  /** Scenario: the Filters (N) panel and the header chip row share one filter state. */
  render(<Controls initial={{ filters: [{ type: "cinema", value: "a", operator: "is" }] }} />);
  scrollHeader("past");
  const filtersButton = within(bar()).getByRole("button", { name: "Filters (1 active)" });

  fireEvent.click(filtersButton);
  expect(filtersButton).toHaveAttribute("aria-expanded", "true");
  const panel = screen.getByRole("dialog", { name: "Filters" });
  expect(within(panel).getByRole("group", { name: "cinema filter" })).toHaveTextContent("Cinema is Cinema A");

  fireEvent.click(within(panel).getByRole("button", { name: "Change cinema operator from is" }));
  expect(within(expandedHeader()).getByRole("group", { name: "cinema filter" })).toHaveTextContent(
    "Cinema is not Cinema A",
  );

  fireEvent.click(within(panel).getByText("+ Filter"));
  fireEvent.click(within(panel).getByRole("button", { name: "Time" }));
  expect(within(bar()).getByRole("button", { name: "Filters (2 active)" })).toBeInTheDocument();
  expect(within(expandedHeader()).getByRole("group", { name: "time filter" })).toBeInTheDocument();

  fireEvent.click(within(panel).getByRole("button", { name: "Clear all" }));
  expect(within(bar()).getByRole("button", { name: "Filters" })).toBeInTheDocument();
  expect(within(expandedHeader()).queryByRole("group", { name: "cinema filter" })).toBeNull();
});

it("closes the Filters panel with Escape, returning focus, after closing an open menu first", () => {
  /** Scenario: keyboard users close an open chip menu, then the panel, without losing focus. */
  render(<Controls initial={{ filters: [{ type: "cinema", value: "a", operator: "is" }] }} />);
  scrollHeader("past");
  const filtersButton = within(bar()).getByRole("button", { name: "Filters (1 active)" });
  fireEvent.click(filtersButton);
  const panel = screen.getByRole("dialog", { name: "Filters" });
  const menu = within(panel).getByText("Cinema A", { selector: "summary" });
  fireEvent.click(menu);
  const details = menu.closest("details");
  if (details) details.open = true;

  fireEvent.keyDown(menu, { key: "Escape" });
  expect(details).not.toHaveAttribute("open");
  expect(screen.getByRole("dialog", { name: "Filters" })).toBeInTheDocument();

  fireEvent.keyDown(within(panel).getByRole("button", { name: "Remove cinema filter" }), { key: "Escape" });
  expect(screen.queryByRole("dialog", { name: "Filters" })).toBeNull();
  expect(filtersButton).toHaveFocus();
  expect(filtersButton).toHaveAttribute("aria-expanded", "false");
});

it("closes the Filters panel when the visitor presses outside the bar", () => {
  /** Scenario: a tap outside dismisses the panel; taps inside keep it open. */
  render(<Controls />);
  scrollHeader("past");
  fireEvent.click(within(bar()).getByRole("button", { name: "Filters" }));
  fireEvent.pointerDown(screen.getByRole("dialog", { name: "Filters" }));
  expect(screen.getByRole("dialog", { name: "Filters" })).toBeInTheDocument();

  fireEvent.pointerDown(document.body);
  expect(screen.queryByRole("dialog", { name: "Filters" })).toBeNull();
});

it("focuses the bar's search field with slash while the bar is shown", () => {
  /** Scenario: `/` reaches the visible search field, not the scrolled-away one. */
  render(<Controls />);
  scrollHeader("past");
  fireEvent.keyDown(document.body, { key: "/" });
  expect(within(bar()).getByRole("searchbox", { name: "Search movies" })).toHaveFocus();
});

describe("on phones", () => {
  beforeEach(() =>
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: query === "(max-width: 639px)",
      media: query,
      addEventListener() {},
      removeEventListener() {},
    })),
  );

  const sheet = () => screen.getByRole("dialog", { name: "Dates and filters" });

  it("keeps ‹ period › in the bar and shows Filters (N) there once search scrolls away", () => {
    /** Scenario: the phone bar holds the period; the search row and its Filters button scroll away. */
    render(<Controls initial={{ filters: [{ type: "cinema", value: "a", operator: "is" }] }} />);
    const row = within(bar());
    expect(row.getByRole("button", { name: "Previous period" })).toBeInTheDocument();
    expect(row.getByRole("button", { name: "Today" })).toHaveAttribute("aria-haspopup", "dialog");
    expect(row.getByRole("button", { name: "Next period" })).toBeInTheDocument();
    expect(row.queryByRole("button", { name: "Filters (1 active)" })).toBeNull();
    expect(row.queryByRole("searchbox", { name: "Search movies" })).toBeNull();
    expect(screen.getByRole("searchbox", { name: "Search movies" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Filters (1 active)" })).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Choose dates" })).toBeNull();
    expect(screen.queryByRole("group", { name: "cinema filter" })).toBeNull();

    scrollHeader("past");
    expect(row.getByRole("button", { name: "Filters (1 active)" })).toBeInTheDocument();

    fireEvent.click(row.getByRole("button", { name: "Next period" }));
    expect(row.getByRole("button", { name: "Tomorrow" })).toBeInTheDocument();
  });

  it("edits a draft in the sheet and applies it with Show N movies", async () => {
    /** Scenario: date and chip changes stay a draft until the visitor taps Show N movies. */
    const onSelection = vi.fn();
    const onCountMovies = vi.fn(async (draft: ActiveCatalogueSelection) =>
      draft.filters.length ? 1 : 4,
    );
    render(
      <ScreeningControls
        selection={{ start: "2026-10-30", end: "2026-10-30", title: "", filters: [] }}
        onSelection={onSelection}
        onCountMovies={onCountMovies}
        cinemas={cinemas}
        today="2026-10-30"
      />,
    );
    const title = within(bar()).getByRole("button", { name: "Today" });
    fireEvent.click(title);
    expect(title).toHaveAttribute("aria-expanded", "true");
    expect(await within(sheet()).findByRole("button", { name: "Show 4 movies" })).toBeInTheDocument();

    fireEvent.click(within(sheet()).getByRole("button", { name: "Saturday October 31st" }), { detail: 0 });
    fireEvent.click(within(sheet()).getByText("+ Filter"));
    fireEvent.click(within(sheet()).getByRole("button", { name: "Time" }));
    expect(within(sheet()).getByRole("heading", { name: "Tomorrow" })).toBeInTheDocument();
    expect(within(bar()).getByRole("button", { name: "Today" })).toBeInTheDocument();
    expect(onSelection).not.toHaveBeenCalled();
    expect(onCountMovies).toHaveBeenLastCalledWith(
      expect.objectContaining({ start: "2026-10-31", end: "2026-10-31" }),
      expect.any(AbortSignal),
    );

    fireEvent.click(await within(sheet()).findByRole("button", { name: "Show 1 movie" }));
    expect(onSelection).toHaveBeenCalledOnce();
    expect(onSelection).toHaveBeenCalledWith({
      start: "2026-10-31",
      end: "2026-10-31",
      title: "",
      filters: [{ type: "time", value: "matinee", operator: "is" }],
    });
    expect(screen.queryByRole("dialog", { name: "Dates and filters" })).toBeNull();
    expect(title).toHaveFocus();
    expect(title).toHaveAttribute("aria-expanded", "false");
  });

  it("cancels the draft when the visitor taps outside the sheet", () => {
    /** Scenario: a tap on the backdrop discards the draft; reopening starts from the applied selection. */
    const onSelection = vi.fn();
    render(
      <ScreeningControls
        selection={{ start: "2026-10-30", end: "2026-10-30", title: "", filters: [] }}
        onSelection={onSelection}
        cinemas={cinemas}
        today="2026-10-30"
      />,
    );
    const filtersButton = screen.getByRole("button", { name: "Filters" });
    fireEvent.click(filtersButton);
    fireEvent.click(within(sheet()).getByText("+ Filter"));
    fireEvent.click(within(sheet()).getByRole("button", { name: "Cinema" }));
    expect(within(sheet()).getByRole("group", { name: "cinema filter" })).toBeInTheDocument();
    expect(within(sheet()).getByRole("button", { name: "Show movies" })).toBeInTheDocument();

    fireEvent.click(within(sheet()).getByRole("group", { name: "cinema filter" }));
    expect(sheet()).toBeInTheDocument();
    // A tap on the backdrop lands on the dialog element itself.
    fireEvent.click(sheet());
    expect(screen.queryByRole("dialog", { name: "Dates and filters" })).toBeNull();
    expect(onSelection).not.toHaveBeenCalled();
    expect(filtersButton).toHaveFocus();

    fireEvent.click(filtersButton);
    expect(within(sheet()).queryByRole("group", { name: "cinema filter" })).toBeNull();
  });
});
