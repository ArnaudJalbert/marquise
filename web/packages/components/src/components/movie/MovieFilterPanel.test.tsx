import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

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
  it("shows the selected date on the calendar trigger", () => {
    renderPanel();

    const trigger = screen.getByRole("button", { name: /open calendar/i });
    expect(trigger).toHaveTextContent(formatDateLabel("2026-08-03"));
  });

  it("shows a placeholder when no date is selected", () => {
    renderPanel({ selectedDate: "" });

    expect(screen.getByText("Select a date")).toBeInTheDocument();
  });

  it("steps to the next available date with the arrows", () => {
    const { props } = renderPanel();

    const next = screen.getByRole("button", { name: "Next date" });
    const previous = screen.getByRole("button", { name: "Previous date" });

    expect(previous).toBeDisabled();
    expect(next).not.toBeDisabled();

    fireEvent.click(next);

    expect(props.onDateChange).toHaveBeenCalledWith("2026-08-04");
  });

  it("disables the next arrow on the last available date", () => {
    renderPanel({ selectedDate: "2026-08-04" });

    expect(
      screen.getByRole("button", { name: "Next date" }),
    ).toBeDisabled();
  });

  it("picks a date from the calendar popover", () => {
    const { props } = renderPanel();

    fireEvent.click(screen.getByRole("button", { name: /open calendar/i }));
    fireEvent.click(
      screen.getByRole("button", { name: formatDateLabel("2026-08-04") }),
    );

    expect(props.onDateChange).toHaveBeenCalledWith("2026-08-04");
  });

  it("disables calendar days that are not available", () => {
    renderPanel({ dates: ["2026-08-03", "2026-08-05"] });

    fireEvent.click(screen.getByRole("button", { name: /open calendar/i }));

    expect(
      screen.getByRole("button", { name: formatDateLabel("2026-08-04") }),
    ).toBeDisabled();
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

  it("shows a card-size slider under Languages when cardSize props are given", () => {
    renderPanel({ cardSize: 200, onCardSizeChange: vi.fn() });

    const section = sectionFor("Card size");
    expect(within(section).getByRole("slider", { name: "Card size" })).toHaveValue(
      "200",
    );
  });

  it("reports card-size changes through onCardSizeChange", () => {
    const onCardSizeChange = vi.fn();
    renderPanel({ cardSize: 200, onCardSizeChange });

    fireEvent.change(screen.getByRole("slider", { name: "Card size" }), {
      target: { value: "320" },
    });

    expect(onCardSizeChange).toHaveBeenCalledWith(320);
  });

  it("omits the card-size slider when cardSize props are absent", () => {
    renderPanel();

    expect(
      screen.queryByRole("slider", { name: "Card size" }),
    ).not.toBeInTheDocument();
  });

  it("shows a details toggle that reports changes through onHideDetailsChange", () => {
    const onHideDetailsChange = vi.fn();
    renderPanel({ hideDetails: false, onHideDetailsChange });

    const toggle = screen.getByRole("checkbox", { name: "Show details" });
    expect(toggle).toBeChecked();

    fireEvent.click(toggle);

    expect(onHideDetailsChange).toHaveBeenCalledWith(true);
  });

  it("reflects hidden details in the details toggle", () => {
    renderPanel({ hideDetails: true, onHideDetailsChange: vi.fn() });

    expect(
      screen.getByRole("checkbox", { name: "Show details" }),
    ).not.toBeChecked();
  });

  it("omits the details toggle when its props are absent", () => {
    renderPanel();

    expect(
      screen.queryByRole("checkbox", { name: "Show details" }),
    ).not.toBeInTheDocument();
  });
});
