import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  MovieFilterPanel,
  formatDateLabel,
  type MovieFilterPanelProps,
} from "./MovieFilterPanel";

function sectionFor(label: string): HTMLElement {
  const heading = screen.getByText(new RegExp(`^${label}`));
  const section = heading.closest("section");
  if (section === null) {
    throw new Error(`Section for ${label} not found`);
  }
  return section;
}

function renderPanel(overrides?: Partial<MovieFilterPanelProps>) {
  const props: MovieFilterPanelProps = {
    query: "",
    onQueryChange: vi.fn(),
    dates: ["2026-08-03", "2026-08-04"],
    selectedDate: "2026-08-03",
    onDateChange: vi.fn(),
    cinemas: ["Cinéma A", "Cinéma B"],
    selectedCinemas: [],
    onCinemasChange: vi.fn(),
    genres: ["Drama", "Comedy"],
    selectedGenres: [],
    onGenresChange: vi.fn(),
    languages: ["VOSTF", "VF"],
    selectedLanguages: [],
    onLanguagesChange: vi.fn(),
    timeRange: [0, 24],
    onTimeRangeChange: vi.fn(),
    ...overrides,
  };
  const { rerender } = render(<MovieFilterPanel {...props} />);
  return { props, rerender };
}

describe("MovieFilterPanel", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-01T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });
  it("updates movie search", () => {
    const { props } = renderPanel();

    fireEvent.change(screen.getByRole("searchbox", { name: "Search movies" }), {
      target: { value: "anora" },
    });

    expect(props.onQueryChange).toHaveBeenCalledWith("anora");
  });

  it("shows the selected date in the calendar trigger", () => {
    renderPanel();

    expect(
      screen.getByRole("button", {
        name: `Open calendar, selected ${formatDateLabel("2026-08-03")}`,
      }),
    ).toBeInTheDocument();
  });

  it("shows a placeholder when no date is selected", () => {
    renderPanel({ selectedDate: "" });

    expect(screen.getByText("Select a date")).toBeInTheDocument();
  });

  it("steps to the next available date with the arrows", () => {
    const { props } = renderPanel();

    const next = screen.getByRole("button", { name: "Next date" });
    const previous = screen.getByRole("button", { name: "Previous date" });

    expect(previous).not.toBeDisabled();
    expect(next).not.toBeDisabled();

    fireEvent.click(next);

    expect(props.onDateChange).toHaveBeenCalledWith("2026-08-04");
  });

  it("steps past the initial date range", () => {
    const { props } = renderPanel({ selectedDate: "2026-08-04" });

    fireEvent.click(screen.getByRole("button", { name: "Next date" }));

    expect(props.onDateChange).toHaveBeenCalledWith("2026-08-05");
  });

  it("picks a date from the calendar", () => {
    const { props } = renderPanel();

    fireEvent.click(
      screen.getByRole("button", {
        name: `Open calendar, selected ${formatDateLabel("2026-08-03")}`,
      }),
    );
    fireEvent.click(screen.getByRole("button", { name: formatDateLabel("2026-08-04") }));

    expect(props.onDateChange).toHaveBeenCalledWith("2026-08-04");
  });

  it("allows any calendar date", () => {
    const { props } = renderPanel({ dates: ["2026-08-03", "2026-08-05"] });

    fireEvent.click(
      screen.getByRole("button", {
        name: `Open calendar, selected ${formatDateLabel("2026-08-03")}`,
      }),
    );
    fireEvent.click(screen.getByRole("button", { name: formatDateLabel("2026-08-04") }));

    expect(props.onDateChange).toHaveBeenCalledWith("2026-08-04");
  });

  it("greys out past calendar dates", () => {
    vi.setSystemTime(new Date("2026-08-04T12:00:00Z"));
    renderPanel({ selectedDate: "2026-08-05" });

    fireEvent.click(
      screen.getByRole("button", {
        name: `Open calendar, selected ${formatDateLabel("2026-08-05")}`,
      }),
    );

    expect(screen.getByRole("button", { name: formatDateLabel("2026-08-03") })).toBeDisabled();
    expect(screen.getByRole("button", { name: formatDateLabel("2026-08-04") })).not.toBeDisabled();
  });

  it("uses Montréal's date when deciding whether a day is past", () => {
    vi.setSystemTime(new Date("2026-08-05T01:00:00Z"));
    renderPanel({ selectedDate: "2026-08-04" });

    fireEvent.click(
      screen.getByRole("button", {
        name: `Open calendar, selected ${formatDateLabel("2026-08-04")}`,
      }),
    );

    expect(screen.getByRole("button", { name: formatDateLabel("2026-08-04") })).not.toBeDisabled();
  });

  it("skips disabled dates during calendar keyboard navigation", () => {
    vi.setSystemTime(new Date("2026-08-04T12:00:00Z"));
    renderPanel({ selectedDate: "2026-08-05" });

    fireEvent.click(
      screen.getByRole("button", {
        name: `Open calendar, selected ${formatDateLabel("2026-08-05")}`,
      }),
    );
    const calendar = screen.getByRole("grid", { name: "Calendar" });
    fireEvent.keyDown(calendar, { key: "ArrowLeft" });
    fireEvent.keyDown(calendar, { key: "ArrowLeft" });

    expect(screen.getByRole("button", { name: formatDateLabel("2026-08-04") })).toHaveAttribute(
      "tabindex",
      "0",
    );
  });

  it("adds a cinema chip when it is toggled on", () => {
    const { props } = renderPanel();

    fireEvent.click(screen.getByRole("button", { name: "Cinéma A" }));

    expect(props.onCinemasChange).toHaveBeenCalledWith(["Cinéma A"]);
  });

  it("removes a cinema chip when it is toggled off", () => {
    const { props } = renderPanel({ selectedCinemas: ["Cinéma A"] });

    fireEvent.click(screen.getByRole("button", { name: "Cinéma A" }));

    expect(props.onCinemasChange).toHaveBeenCalledWith([]);
  });

  it("toggles genre and language chips through their own callbacks", () => {
    const { props } = renderPanel();

    fireEvent.click(screen.getByRole("button", { name: "Drama" }));
    expect(props.onGenresChange).toHaveBeenCalledWith(["Drama"]);

    fireEvent.click(screen.getByRole("button", { name: "VOSTF" }));
    expect(props.onLanguagesChange).toHaveBeenCalledWith(["VOSTF"]);
  });

  it("shows the selected count next to a multi-select label", () => {
    renderPanel({ selectedCinemas: ["Cinéma A"] });

    expect(screen.getByText("Cinemas · 1/2")).toBeInTheDocument();
  });

  it("renders the time range label from the current hours", () => {
    renderPanel();

    expect(screen.getByText("00:00 – 24:00")).toBeInTheDocument();
  });

  it("reports slider changes as clamped time ranges", () => {
    const { props } = renderPanel();

    fireEvent.change(screen.getByLabelText("Start time"), {
      target: { value: "10" },
    });
    expect(props.onTimeRangeChange).toHaveBeenCalledWith([10, 24]);

    fireEvent.change(screen.getByLabelText("End time"), {
      target: { value: "22" },
    });
    expect(props.onTimeRangeChange).toHaveBeenCalledWith([0, 22]);
  });

  it("expands a collapsed time range by dragging the start thumb right", () => {
    const { props } = renderPanel({ timeRange: [14, 14] });

    fireEvent.change(screen.getByLabelText("Start time"), {
      target: { value: "16" },
    });

    expect(props.onTimeRangeChange).toHaveBeenCalledWith([14, 16]);
  });

  it("shows a placeholder when a multi-select has no options", () => {
    renderPanel({ cinemas: [] });

    expect(screen.getByText("No options on this date.")).toBeInTheDocument();
  });

  it("selects every option in a group with the Select all button", () => {
    const { props } = renderPanel();
    const section = sectionFor("Cinemas");

    fireEvent.click(
      within(section).getByRole("button", { name: "Select all" }),
    );

    expect(props.onCinemasChange).toHaveBeenCalledWith(["Cinéma A", "Cinéma B"]);
  });

  it("clears every option in a group with the Clear button", () => {
    const { props } = renderPanel({ selectedCinemas: ["Cinéma A"] });
    const section = sectionFor("Cinemas");

    fireEvent.click(within(section).getByRole("button", { name: "Clear" }));

    expect(props.onCinemasChange).toHaveBeenCalledWith([]);
  });

  it("disables Select all once every option is already selected", () => {
    renderPanel({ selectedCinemas: ["Cinéma A", "Cinéma B"] });
    const section = sectionFor("Cinemas");

    expect(
      within(section).getByRole("button", { name: "Select all" }),
    ).toBeDisabled();
  });

  it("disables Clear while no option is selected", () => {
    renderPanel();
    const section = sectionFor("Genres");

    expect(within(section).getByRole("button", { name: "Clear" })).toBeDisabled();
  });

  it("hides the Select all/Clear buttons when a group has no options", () => {
    renderPanel({ cinemas: [] });
    const section = sectionFor("Cinemas");

    expect(
      within(section).queryByRole("button", { name: "Select all" }),
    ).not.toBeInTheDocument();
    expect(
      within(section).queryByRole("button", { name: "Clear" }),
    ).not.toBeInTheDocument();
  });

  it("does not render display controls", () => {
    renderPanel();

    expect(
      screen.queryByRole("checkbox", { name: "Show details" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("slider", { name: "Card size" })).not.toBeInTheDocument();
  });
});
