import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { describe, expect, it, vi } from "vitest";
import type { Cinema, CinemaShowtime, MovieGridClient } from "marquise-client";

import { fixedResizeObserver } from "../../../test/resize-observer";
import { MovieGridController } from "./MovieGridController";
import type { MovieCardGridItem } from "./movie-card-grid";

const cinemaA: Cinema = {
  id: "cinema-a",
  name: "Cinéma A",
  link: "https://example.com/cinemas/cinema-a",
};
const cinemaB: Cinema = {
  id: "cinema-b",
  name: "Cinéma B",
  link: "https://example.com/cinemas/cinema-b",
};

function showtime(time: string, cinema: Cinema, language: string): CinemaShowtime {
  return {
    startsAt: `2026-08-03T${time}:00-04:00`,
    ticketUrl: "https://tickets.example.com/t",
    cinema,
    language,
  };
}

function item(
  key: string,
  genres: string[],
  showtimes: CinemaShowtime[],
): MovieCardGridItem {
  return {
    key,
    movie: { title: key, genres },
    showtimesUrl: `https://example.com/movies/${key}`,
    showtimes,
  };
}

const dayOne = [
  item("dune", ["Sci-Fi"], [showtime("18:00", cinemaA, "VOSTF")]),
  item("anora", ["Comedy"], [showtime("20:00", cinemaB, "VF")]),
];

const dayTwo = [
  item("dune", ["Sci-Fi"], [showtime("18:00", cinemaA, "VOSTF")]),
];

function createClient() {
  const byDate: Record<string, MovieCardGridItem[]> = {
    "2026-08-03": dayOne,
    "2026-08-04": dayTwo,
  };
  return {
    listDates: vi.fn(async (): Promise<string[]> => [
      "2026-08-03",
      "2026-08-04",
    ]),
    fetchForDate: vi.fn(
      async (date: string): Promise<MovieCardGridItem[]> => byDate[date] ?? [],
    ),
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

describe("MovieGridController", () => {
  it("renders the filter panel beside the grid once the date loads", async () => {
    const client = createClient();
    render(<MovieGridController client={client} />);

    expect(
      await screen.findByRole("heading", { name: "dune" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "anora" })).toBeInTheDocument();
    expect(
      screen.getByRole("combobox", { name: "Screening date" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cinéma A" })).toBeInTheDocument();
  });

  it("shows a loading indicator while a date is being fetched", async () => {
    const pending = deferred<MovieCardGridItem[]>();
    const client: MovieGridClient = {
      listDates: vi.fn(async () => ["2026-08-03"]),
      fetchForDate: vi.fn(() => pending.promise),
    };
    render(<MovieGridController client={client} />);

    expect(await screen.findByText("Loading showtimes…")).toBeInTheDocument();

    act(() => {
      pending.resolve(dayOne);
    });

    expect(
      await screen.findByRole("heading", { name: "dune" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Loading showtimes…")).not.toBeInTheDocument();
  });

  it("filters the grid locally without refetching", async () => {
    const client = createClient();
    render(<MovieGridController client={client} />);

    await screen.findByRole("heading", { name: "dune" });

    fireEvent.click(screen.getByRole("button", { name: "Cinéma B" }));

    await waitFor(() =>
      expect(
        screen.queryByRole("heading", { name: "dune" }),
      ).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("heading", { name: "anora" })).toBeInTheDocument();
    expect(client.fetchForDate).toHaveBeenCalledTimes(1);
  });

  it("restores local filters and reports their changes", async () => {
    const client = createClient();
    const onFiltersChange = vi.fn();
    render(
      <MovieGridController
        client={client}
        initialFilters={{ cinemas: ["Cinéma B"], timeRange: [0, 24] }}
        onFiltersChange={onFiltersChange}
      />,
    );

    expect(
      await screen.findByRole("heading", { name: "anora" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "dune" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cinéma B" }));
    await waitFor(() =>
      expect(onFiltersChange).toHaveBeenLastCalledWith(
        expect.objectContaining({ cinemas: [] }),
      ),
    );
  });

  it("reports resolved and user-selected dates with their reasons", async () => {
    const client = createClient();
    const onSelectedDateChange = vi.fn();
    render(
      <MovieGridController
        client={client}
        initialFilters={{ timeRange: [0, 24] }}
        onSelectedDateChange={onSelectedDateChange}
      />,
    );

    await screen.findByRole("heading", { name: "dune" });
    expect(onSelectedDateChange).toHaveBeenCalledWith(
      "2026-08-03",
      "normalization",
    );

    fireEvent.click(screen.getByRole("button", { name: "Next date" }));
    expect(onSelectedDateChange).toHaveBeenLastCalledWith("2026-08-04", "user");
  });

  it("shows an empty state when no screenings match", async () => {
    const client = createClient();
    render(<MovieGridController client={client} />);

    await screen.findByRole("heading", { name: "dune" });

    fireEvent.change(screen.getByLabelText("Start time"), {
      target: { value: "23" },
    });

    expect(
      await screen.findByText("No screenings match these filters."),
    ).toBeInTheDocument();
  });

  it("forwards onMovieClick to the movie cards", async () => {
    const client = createClient();
    const onMovieClick = vi.fn();
    render(<MovieGridController client={client} onMovieClick={onMovieClick} />);

    await screen.findByRole("heading", { name: "dune" });

    fireEvent.click(screen.getByRole("button", { name: "dune" }));

    expect(onMovieClick).toHaveBeenCalledTimes(1);
    expect(onMovieClick).toHaveBeenCalledWith({ title: "dune", genres: ["Sci-Fi"] });
  });

  it("shows an error and retries when the date fetch fails", async () => {
    let fail = true;
    const client: MovieGridClient = {
      listDates: vi.fn(async () => ["2026-08-03"]),
      fetchForDate: vi.fn(async () => {
        if (fail) {
          throw new Error("network");
        }
        return dayOne;
      }),
    };
    render(<MovieGridController client={client} />);

    expect(
      await screen.findByText("Could not load showtimes for this date."),
    ).toBeInTheDocument();

    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(
      await screen.findByRole("heading", { name: "dune" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Could not load showtimes for this date.")).not.toBeInTheDocument();
  });

  it("fetches only when the date changes, never for local filters", async () => {
    const client = createClient();
    render(<MovieGridController client={client} />);

    await waitFor(() => expect(client.fetchForDate).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Cinéma B" }));
    expect(client.fetchForDate).toHaveBeenCalledTimes(1);

    fireEvent.change(screen.getByRole("combobox", { name: "Screening date" }), {
      target: { value: "2026-08-04" },
    });

    await waitFor(() => expect(client.fetchForDate).toHaveBeenCalledTimes(2));
  });

  it("renders a card-size slider without widening a small result set", async () => {
    vi.restoreAllMocks();
    vi.stubGlobal("ResizeObserver", fixedResizeObserver(1430, 1200));
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(200);

    const client = createClient();
    const onCardSizeChange = vi.fn();
    const { container } = render(
      <MovieGridController
        client={client}
        pageSize="auto"
        onCardSizeChange={onCardSizeChange}
      />,
    );

    await screen.findByRole("heading", { name: "dune" });

    const slider = screen.getByRole("slider", { name: "Card size" });
    expect(slider).toHaveValue("200");

    const list = container.querySelector("ul");
    expect(list?.getAttribute("style")).toContain("repeat(2");

    fireEvent.change(slider, { target: { value: "320" } });

    expect(screen.getByRole("slider", { name: "Card size" })).toHaveValue("320");
    expect(list?.getAttribute("style")).toContain("repeat(2");
    expect(onCardSizeChange).toHaveBeenCalledWith(320);
  });

  it("changes auto-fit pages with the date selector mounted in Strict Mode", async () => {
    vi.restoreAllMocks();
    vi.stubGlobal("ResizeObserver", fixedResizeObserver(896, 600));
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(200);

    const movies = Array.from({ length: 10 }, (_, index) =>
      item(
        `Movie ${index + 1}`,
        ["Drama"],
        [showtime("18:00", cinemaA, "VOSTF")],
      ),
    );
    const client: MovieGridClient = {
      listDates: vi.fn(async () => ["2026-08-03"]),
      fetchForDate: vi.fn(async () => movies),
    };

    render(
      <StrictMode>
        <MovieGridController client={client} pageSize="auto" />
      </StrictMode>,
    );

    expect(
      await screen.findByRole("heading", { name: "Movie 1" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));

    expect(screen.getByText("2 / 2")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Movie 9" })).toBeInTheDocument();
  });

  it("omits the card-size slider when pageSize is not auto", async () => {
    const client = createClient();
    render(<MovieGridController client={client} />);

    await screen.findByRole("heading", { name: "dune" });

    expect(
      screen.queryByRole("slider", { name: "Card size" }),
    ).not.toBeInTheDocument();
  });

  it("toggles card details from the grid controls", async () => {
    const client = createClient();
    const onHideDetailsChange = vi.fn();
    render(
      <MovieGridController
        client={client}
        onHideDetailsChange={onHideDetailsChange}
      />,
    );

    await screen.findByRole("heading", { name: "dune" });

    fireEvent.click(screen.getByRole("checkbox", { name: "Show details" }));

    expect(screen.getByRole("heading", { name: "dune" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Poster for dune" }),
    ).toBeInTheDocument();
    expect(onHideDetailsChange).toHaveBeenCalledWith(true);
  });
});
