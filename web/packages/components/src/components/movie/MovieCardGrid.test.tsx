import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MovieCardGrid } from "./MovieCardGrid";

const cinema = {
  id: "cinema-moderne",
  name: "Cinéma Moderne",
  link: "https://example.com/cinemas/cinema-moderne",
};

const movieItems = (count: number) =>
  Array.from({ length: count }, (_, index) => ({
    movie: { title: `Movie ${index + 1}` },
    showtimesUrl: `https://example.com/movies/movie-${index + 1}`,
  }));

class ControllableResizeObserver implements ResizeObserver {
  private readonly callback: ResizeObserverCallback;
  static instances: ControllableResizeObserver[] = [];

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    ControllableResizeObserver.instances.push(this);
  }

  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}

  emit(width: number, height: number): void {
    this.callback([{ contentRect: { width, height } } as ResizeObserverEntry], this);
  }
}

function lastResizeObserver(): ControllableResizeObserver {
  const instance = ControllableResizeObserver.instances[0];
  if (instance === undefined) {
    throw new Error("ResizeObserver was not instantiated");
  }
  return instance;
}

describe("MovieCardGrid", () => {
  it("renders one card per item", () => {
    render(
      <MovieCardGrid
        items={[
          { movie: { title: "Anora" }, showtimesUrl: "https://example.com/movies/anora" },
          { movie: { title: "Dune: Part Two" }, showtimesUrl: "https://example.com/movies/dune" },
        ]}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Anora" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Dune: Part Two" }),
    ).toBeInTheDocument();
  });

  it("preserves card state across reordering when items carry stable keys", () => {
    const cinemaA = { id: "a", name: "Cinéma A", link: "https://example.com/cinemas/a" };
    const cinemaB = { id: "b", name: "Cinéma B", link: "https://example.com/cinemas/b" };
    const makeItem = (
      key: string,
      title: string,
      itemCinema: { id: string; name: string; link: string },
    ) => ({
      key,
      movie: { title },
      showtimesUrl: `https://example.com/movies/${title}`,
      showtimes: [
        {
          startsAt: "2026-08-03T18:30:00-04:00",
          ticketUrl: `https://tickets.example.com/${title}`,
          cinema: itemCinema,
        },
      ],
    });

    const { rerender } = render(
      <MovieCardGrid items={[makeItem("anora", "Anora", cinemaA), makeItem("dune", "Dune", cinemaB)]} />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "All showtimes for Anora" }),
    );
    expect(
      screen.getByRole("button", { name: "All showtimes for Anora" }),
    ).toHaveAttribute("aria-expanded", "true");

    rerender(
      <MovieCardGrid items={[makeItem("dune", "Dune", cinemaB), makeItem("anora", "Anora", cinemaA)]} />,
    );

    expect(
      screen.getByRole("button", { name: "All showtimes for Anora" }),
    ).toHaveAttribute("aria-expanded", "true");
  });

  it("resets card state when reordered items lack stable keys", () => {
    const cinemaA = { id: "a", name: "Cinéma A", link: "https://example.com/cinemas/a" };
    const cinemaB = { id: "b", name: "Cinéma B", link: "https://example.com/cinemas/b" };
    const makeItem = (title: string, itemCinema: { id: string; name: string; link: string }) => ({
      movie: { title },
      showtimesUrl: `https://example.com/movies/${title}`,
      showtimes: [
        {
          startsAt: "2026-08-03T18:30:00-04:00",
          ticketUrl: `https://tickets.example.com/${title}`,
          cinema: itemCinema,
        },
      ],
    });

    const { rerender } = render(
      <MovieCardGrid items={[makeItem("Anora", cinemaA), makeItem("Dune", cinemaB)]} />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "All showtimes for Anora" }),
    );
    expect(
      screen.getByRole("button", { name: "All showtimes for Anora" }),
    ).toHaveAttribute("aria-expanded", "true");

    rerender(
      <MovieCardGrid items={[makeItem("Dune", cinemaB), makeItem("Anora", cinemaA)]} />,
    );

    expect(
      screen.getByRole("button", { name: "All showtimes for Anora" }),
    ).toHaveAttribute("aria-expanded", "false");
  });

  it("applies the default responsive grid classes and merges className", () => {
    const { container } = render(
      <MovieCardGrid
        className="gap-8"
        items={[
          { movie: { title: "Anora" }, showtimesUrl: "https://example.com/movies/anora" },
        ]}
      />,
    );

    const list = container.querySelector("ul");
    expect(list).toHaveClass("grid");
    expect(list).toHaveClass("grid-cols-2");
    expect(list).toHaveClass("md:grid-cols-3");
    expect(list).toHaveClass("xl:grid-cols-4");
    expect(list).toHaveClass("gap-8");
  });

  it("fills the row height and merges cardClassName on every card", () => {
    const { container } = render(
      <MovieCardGrid
        cardClassName="max-w-xs"
        items={[
          { movie: { title: "Anora" }, showtimesUrl: "https://example.com/movies/anora" },
        ]}
      />,
    );

    const card = container.querySelector(".h-full");
    expect(card).not.toBeNull();
    expect(card).toHaveClass("max-w-xs");
  });

  it("renders each item's own showtimes", () => {
    render(
      <MovieCardGrid
        items={[
          {
            movie: { title: "Anora" },
            showtimesUrl: "https://example.com/movies/anora",
            showtimes: [
              {
                startsAt: "2026-08-03T18:30:00-04:00",
                ticketUrl: "https://tickets.example.com/anora",
                cinema,
              },
            ],
          },
        ]}
      />,
    );

    const link = screen.getByRole("link", { name: "18:30" });
    expect(link).toHaveAttribute("href", "https://tickets.example.com/anora");
  });

  it("forwards onMovieClick to every card", () => {
    const onMovieClick = vi.fn();
    const movie = { title: "Anora" };
    render(
      <MovieCardGrid
        onMovieClick={onMovieClick}
        items={[{ movie, showtimesUrl: "https://example.com/movies/anora" }]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Anora" }));

    expect(onMovieClick).toHaveBeenCalledWith(movie);
  });

  it("forwards currentTime so started showtimes are crossed out", () => {
    render(
      <MovieCardGrid
        currentTime="2026-08-03T19:00:00-04:00"
        items={[
          {
            movie: { title: "Anora" },
            showtimesUrl: "https://example.com/movies/anora",
            showtimes: [
              {
                startsAt: "2026-08-03T18:30:00-04:00",
                ticketUrl: "https://tickets.example.com/anora",
                cinema,
              },
            ],
          },
        ]}
      />,
    );

    expect(screen.getByText("18:30")).toHaveClass("line-through");
  });

  it("forwards onShowtimeClick to the card chips", () => {
    const onShowtimeClick = vi.fn();
    const showtime = {
      startsAt: "2026-08-03T18:30:00-04:00",
      ticketUrl: "https://tickets.example.com/anora",
      cinema,
    };
    render(
      <MovieCardGrid
        onShowtimeClick={onShowtimeClick}
        items={[
          {
            movie: { title: "Anora" },
            showtimesUrl: "https://example.com/movies/anora",
            showtimes: [showtime],
          },
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("link", { name: "18:30" }));

    expect(onShowtimeClick).toHaveBeenCalledOnce();
    expect(onShowtimeClick).toHaveBeenCalledWith(showtime);
  });

  it("forwards maxShowtimes to limit the default chips", () => {
    const showtimes = [
      { startsAt: "2026-08-03T10:00:00-04:00", ticketUrl: "https://tickets.example.com/a", cinema },
      { startsAt: "2026-08-03T11:00:00-04:00", ticketUrl: "https://tickets.example.com/b", cinema },
      { startsAt: "2026-08-03T12:00:00-04:00", ticketUrl: "https://tickets.example.com/c", cinema },
    ];
    render(
      <MovieCardGrid
        maxShowtimes={2}
        items={[
          {
            movie: { title: "Anora" },
            showtimesUrl: "https://example.com/movies/anora",
            showtimes,
          },
        ]}
      />,
    );

    const chips = screen
      .getAllByRole("link")
      .map((link) => link.textContent)
      .filter(
        (text): text is string =>
          text !== null && /^\d{2}:\d{2}$/.test(text),
      );

    expect(chips).toEqual(["10:00", "11:00"]);
  });

  it("pages through the items when a numeric pageSize is set", () => {
    render(<MovieCardGrid pageSize={4} items={movieItems(9)} />);

    expect(screen.getByRole("heading", { name: "Movie 1" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Movie 4" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Movie 5" })).not.toBeInTheDocument();
    expect(screen.getByText("1 / 3")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Next page" }));

    expect(screen.getByRole("heading", { name: "Movie 5" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Movie 8" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Movie 4" })).not.toBeInTheDocument();
    expect(screen.getByText("2 / 3")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Next page" }));

    expect(screen.getByRole("heading", { name: "Movie 9" })).toBeInTheDocument();
    expect(screen.getByText("3 / 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
  });

  it("disables the previous control on the first page and navigates back", () => {
    render(<MovieCardGrid pageSize={4} items={movieItems(9)} />);

    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    fireEvent.click(screen.getByRole("button", { name: "Previous page" }));

    expect(screen.getByText("1 / 3")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Movie 1" })).toBeInTheDocument();
  });

  it("omits the pagination controls when everything fits on one page", () => {
    render(<MovieCardGrid pageSize={4} items={movieItems(4)} />);

    expect(screen.getByRole("heading", { name: "Movie 4" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Next page" })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Previous page" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/^\d+ \/ \d+$/)).not.toBeInTheDocument();
  });

  it("clamps the page back to the last valid one when the items shrink", () => {
    const { rerender } = render(<MovieCardGrid pageSize={4} items={movieItems(6)} />);

    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(screen.getByRole("heading", { name: "Movie 6" })).toBeInTheDocument();

    rerender(<MovieCardGrid pageSize={4} items={movieItems(4)} />);

    expect(screen.getByRole("heading", { name: "Movie 1" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Next page" })).not.toBeInTheDocument();
  });

  it("navigates pages with the arrow keys", () => {
    render(<MovieCardGrid pageSize={4} items={movieItems(9)} />);

    const list = screen.getByRole("list");
    fireEvent.keyDown(list, { key: "ArrowRight" });

    expect(screen.getByText("2 / 3")).toBeInTheDocument();

    fireEvent.keyDown(list, { key: "ArrowLeft" });

    expect(screen.getByText("1 / 3")).toBeInTheDocument();
  });

  it("auto-fits the page size to the measured container when pageSize is auto", () => {
    class AutoResizeObserver implements ResizeObserver {
      private readonly callback: ResizeObserverCallback;

      constructor(callback: ResizeObserverCallback) {
        this.callback = callback;
      }

      observe(_target: Element): void {
        this.callback(
          [{ contentRect: { width: 896, height: 600 } } as ResizeObserverEntry],
          this,
        );
      }

      unobserve(): void {}
      disconnect(): void {}
    }

    vi.stubGlobal("ResizeObserver", AutoResizeObserver);
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(200);

    render(<MovieCardGrid pageSize="auto" items={movieItems(12)} />);

    expect(screen.getByRole("heading", { name: "Movie 1" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Movie 8" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Movie 9" })).not.toBeInTheDocument();
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
  });

  it("spreads to more columns on wide containers so several rows fit the height", () => {
    class WideResizeObserver implements ResizeObserver {
      private readonly callback: ResizeObserverCallback;

      constructor(callback: ResizeObserverCallback) {
        this.callback = callback;
      }

      observe(_target: Element): void {
        this.callback(
          [{ contentRect: { width: 1430, height: 1200 } } as ResizeObserverEntry],
          this,
        );
      }

      unobserve(): void {}
      disconnect(): void {}
    }

    vi.restoreAllMocks();
    vi.stubGlobal("ResizeObserver", WideResizeObserver);
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(200);

    const { container } = render(
      <MovieCardGrid pageSize="auto" items={movieItems(12)} />,
    );

    const list = container.querySelector("ul");
    expect(list?.getAttribute("style")).toContain("repeat(6");
    expect(screen.getByRole("heading", { name: "Movie 12" })).toBeInTheDocument();
    expect(screen.queryByText(/^\d+ \/ \d+$/)).not.toBeInTheDocument();
  });

  it("uses a larger cardSize to shrink the column count", () => {
    class WideResizeObserver implements ResizeObserver {
      private readonly callback: ResizeObserverCallback;

      constructor(callback: ResizeObserverCallback) {
        this.callback = callback;
      }

      observe(_target: Element): void {
        this.callback(
          [{ contentRect: { width: 1430, height: 1200 } } as ResizeObserverEntry],
          this,
        );
      }

      unobserve(): void {}
      disconnect(): void {}
    }

    vi.restoreAllMocks();
    vi.stubGlobal("ResizeObserver", WideResizeObserver);
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(570);

    const { container } = render(
      <MovieCardGrid pageSize="auto" cardSize={320} items={movieItems(12)} />,
    );

    const list = container.querySelector("ul");
    expect(list?.getAttribute("style")).toContain("repeat(4");
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
  });

  it("uses a smaller cardSize to grow the column count", () => {
    class WideResizeObserver implements ResizeObserver {
      private readonly callback: ResizeObserverCallback;

      constructor(callback: ResizeObserverCallback) {
        this.callback = callback;
      }

      observe(_target: Element): void {
        this.callback(
          [{ contentRect: { width: 1430, height: 1200 } } as ResizeObserverEntry],
          this,
        );
      }

      unobserve(): void {}
      disconnect(): void {}
    }

    vi.restoreAllMocks();
    vi.stubGlobal("ResizeObserver", WideResizeObserver);
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(200);

    const { container } = render(
      <MovieCardGrid pageSize="auto" cardSize={150} items={movieItems(12)} />,
    );

    const list = container.querySelector("ul");
    expect(list?.getAttribute("style")).toContain("repeat(8");
    expect(screen.getByRole("heading", { name: "Movie 12" })).toBeInTheDocument();
    expect(screen.queryByText(/^\d+ \/ \d+$/)).not.toBeInTheDocument();
  });

  it("ignores cardSize when the page size is numeric", () => {
    const { container } = render(
      <MovieCardGrid pageSize={4} cardSize={320} items={movieItems(12)} />,
    );

    const list = container.querySelector("ul");
    expect(list?.getAttribute("style")).toBeNull();
  });

  it("hides card details for every card when hideDetails is set", () => {
    render(<MovieCardGrid pageSize={4} hideDetails items={movieItems(4)} />);

    expect(
      screen.queryByRole("heading", { name: "Movie 1" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Poster for Movie 1" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Movie 4" }),
    ).not.toBeInTheDocument();
  });

  it("renders only the measurement subset until the row height is known", () => {
    vi.restoreAllMocks();
    vi.stubGlobal("ResizeObserver", ControllableResizeObserver);
    ControllableResizeObserver.instances = [];
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(0);

    render(<MovieCardGrid pageSize="auto" items={movieItems(12)} />);

    act(() => lastResizeObserver().emit(896, 600));

    expect(screen.getByRole("heading", { name: "Movie 1" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Movie 4" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Movie 5" })).not.toBeInTheDocument();
    expect(screen.queryByText(/^\d+ \/ \d+$/)).not.toBeInTheDocument();
  });

  it("recovers when the container becomes visible after mounting hidden", () => {
    vi.restoreAllMocks();
    vi.stubGlobal("ResizeObserver", ControllableResizeObserver);
    ControllableResizeObserver.instances = [];
    const offsetHeightMock = vi.spyOn(HTMLElement.prototype, "offsetHeight", "get");

    render(<MovieCardGrid pageSize="auto" items={movieItems(12)} />);
    const observer = lastResizeObserver();

    offsetHeightMock.mockReturnValue(0);
    act(() => observer.emit(896, 600));
    expect(screen.queryByText(/^\d+ \/ \d+$/)).not.toBeInTheDocument();

    offsetHeightMock.mockReturnValue(200);
    act(() => observer.emit(896, 600));

    expect(screen.getByText("1 / 2")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Movie 8" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Movie 9" })).not.toBeInTheDocument();
  });

  it("re-measures the row height when the width changes within the same column band", () => {
    vi.restoreAllMocks();
    vi.stubGlobal("ResizeObserver", ControllableResizeObserver);
    ControllableResizeObserver.instances = [];
    const offsetHeightMock = vi.spyOn(HTMLElement.prototype, "offsetHeight", "get");

    render(<MovieCardGrid pageSize="auto" items={movieItems(12)} />);
    const observer = lastResizeObserver();

    offsetHeightMock.mockReturnValue(200);
    act(() => observer.emit(896, 600));
    expect(screen.getByText("1 / 2")).toBeInTheDocument();

    offsetHeightMock.mockReturnValue(300);
    act(() => observer.emit(860, 600));

    expect(screen.getByText("1 / 3")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Movie 5" })).not.toBeInTheDocument();
  });

  it("repaginates when the container height shrinks", () => {
    vi.restoreAllMocks();
    vi.stubGlobal("ResizeObserver", ControllableResizeObserver);
    ControllableResizeObserver.instances = [];
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(200);

    render(<MovieCardGrid pageSize="auto" items={movieItems(12)} />);
    const observer = lastResizeObserver();

    act(() => observer.emit(896, 600));
    expect(screen.getByText("1 / 2")).toBeInTheDocument();

    act(() => observer.emit(896, 280));

    expect(screen.getByText("1 / 3")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Movie 4" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Movie 5" })).not.toBeInTheDocument();
  });
});
