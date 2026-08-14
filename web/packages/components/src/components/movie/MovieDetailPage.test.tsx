import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { describe, expect, it, vi } from "vitest";
import type {
  Cinema,
  CinemaShowtime,
  MovieCardData,
  MovieDetailClient,
} from "marquise-client";

import { formatDateLabel } from "./date-selector";
import { MovieDetailPage } from "./MovieDetailPage";

const cinemaModerne: Cinema = {
  id: "cinema-moderne",
  name: "Cinéma Moderne",
  link: "https://example.com/cinemas/cinema-moderne",
};
const cinemaCq: Cinema = {
  id: "cine-cq",
  name: "Cinémathèque québécoise",
  link: "https://example.com/cinemas/cine-cq",
};

function showtime(time: string, cinema: Cinema, language: string): CinemaShowtime {
  return {
    startsAt: `2026-08-03T${time}:00-04:00`,
    ticketUrl: "https://tickets.example.com/t",
    cinema,
    language,
  };
}

const movie: MovieCardData = {
  title: "Dune: Part Two",
  releaseYear: 2024,
  durationMinutes: 166,
  directors: ["Denis Villeneuve"],
  genres: ["Sci-Fi", "Drama"],
};

const dayOne = [
  showtime("18:00", cinemaModerne, "VOSTF"),
  showtime("21:00", cinemaModerne, "VF"),
];

const dayTwo = [showtime("19:30", cinemaCq, "VOSTF")];

const dayThree: CinemaShowtime[] = [];

const dates = ["2026-08-03", "2026-08-04", "2026-08-05"];

const byDate: Record<string, CinemaShowtime[]> = {
  "2026-08-03": dayOne,
  "2026-08-04": dayTwo,
  "2026-08-05": dayThree,
};

function createClient(overrides?: Partial<MovieDetailClient>) {
  const client: MovieDetailClient = {
    fetchMovie: vi.fn(async () => movie),
    listDates: vi.fn(async () => dates),
    fetchShowtimes: vi.fn(
      async (_m: MovieCardData, date: string) => byDate[date] ?? [],
    ),
    ...overrides,
  };
  return client;
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

class ControllableResizeObserver implements ResizeObserver {
  static instances: ControllableResizeObserver[] = [];
  private readonly callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    ControllableResizeObserver.instances.push(this);
  }

  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}

  emit(width: number): void {
    this.callback([{ contentRect: { width, height: 600 } } as ResizeObserverEntry], this);
  }
}

function lastResizeObserver(): ControllableResizeObserver {
  const instance = ControllableResizeObserver.instances[0];
  if (instance === undefined) {
    throw new Error("ResizeObserver was not instantiated");
  }
  return instance;
}

const defaultResizeObserver = globalThis.ResizeObserver;

describe("MovieDetailPage", () => {
  it("mounts under Strict Mode without a composed-ref update loop", async () => {
    const client = createClient();
    render(
      <StrictMode>
        <MovieDetailPage movie={movie} client={client} />
      </StrictMode>,
    );

    expect(
      await screen.findByRole("heading", { name: "Dune: Part Two" }),
    ).toBeInTheDocument();
  });

  it("renders the movie header and the first date's showtimes", async () => {
    const client = createClient();
    render(<MovieDetailPage movie={movie} client={client} />);

    expect(
      await screen.findByRole("heading", { name: "Dune: Part Two" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("2024 · 2 h 46 min · Denis Villeneuve · Sci-Fi, Drama"),
    ).toBeInTheDocument();

    expect(client.listDates).toHaveBeenCalledWith(movie);
    await waitFor(() =>
      expect(client.fetchShowtimes).toHaveBeenCalledWith(movie, "2026-08-03"),
    );
    expect(screen.getAllByText(formatDateLabel("2026-08-03")).length).toBeGreaterThan(0);
    expect(await screen.findByText("Cinéma Moderne")).toBeInTheDocument();
    expect(screen.getByText("18:00")).toBeInTheDocument();
    expect(screen.getByText("21:00")).toBeInTheDocument();
  });

  it("loads the next date and slides it in with the Later dates arrow", async () => {
    const client = createClient();
    render(<MovieDetailPage movie={movie} client={client} />);

    await screen.findByRole("heading", { name: "Dune: Part Two" });

    expect(
      screen.getByRole("button", { name: "Earlier dates" }),
    ).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Later dates" }));

    await waitFor(() =>
      expect(client.fetchShowtimes).toHaveBeenCalledWith(movie, "2026-08-05"),
    );
    expect(await screen.findByText("No screenings.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Earlier dates" }),
    ).not.toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Later dates" }));

    expect(
      screen.getByRole("button", { name: "Later dates" }),
    ).toBeDisabled();
  });

  it("selects any future calendar date and shows an empty result", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-01T12:00:00Z"));
    try {
      const client = createClient();
      render(<MovieDetailPage movie={movie} client={client} />);

      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
      });
      fireEvent.click(
        screen.getByRole("button", {
          name: `Open calendar, selected ${formatDateLabel("2026-08-03")}`,
        }),
      );
      fireEvent.click(screen.getByRole("button", { name: formatDateLabel("2026-08-10") }));

      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(client.fetchShowtimes).toHaveBeenCalledWith(movie, "2026-08-10");
      expect(screen.getAllByText("No screenings.")).not.toHaveLength(0);
    } finally {
      vi.useRealTimers();
    }
  });

  it("restores and reports the selected showtimes date", async () => {
    const client = createClient();
    const onDateChange = vi.fn();
    render(
      <MovieDetailPage
        movie={movie}
        client={client}
        initialDate="2026-08-04"
        onDateChange={onDateChange}
      />,
    );

    await waitFor(() =>
      expect(client.fetchShowtimes).toHaveBeenCalledWith(movie, "2026-08-04"),
    );
    fireEvent.click(screen.getByRole("button", { name: "Earlier dates" }));

    expect(onDateChange).toHaveBeenCalledWith("2026-08-03", "user");
  });

  it("shows a loading indicator while a date's showtimes are fetched", async () => {
    const pendings = new Map<
      string,
      { resolve: (value: readonly CinemaShowtime[]) => void }
    >();
    const client = createClient({
      fetchShowtimes: vi.fn((_m: MovieCardData, date: string) => {
        const pending = deferred<readonly CinemaShowtime[]>();
        pendings.set(date, pending);
        return pending.promise;
      }),
    });
    render(<MovieDetailPage movie={movie} client={client} />);

    await waitFor(() => expect(pendings.has("2026-08-03")).toBe(true));

    act(() => {
      pendings.get("2026-08-03")?.resolve(dayOne);
    });

    expect(await screen.findByText("Cinéma Moderne")).toBeInTheDocument();
    expect(screen.getAllByText("Loading showtimes…").length).toBeGreaterThan(0);
  });

  it("shows an empty state when the movie has no screening dates", async () => {
    const client = createClient({ listDates: vi.fn(async () => []) });
    render(<MovieDetailPage movie={movie} client={client} />);

    expect(
      await screen.findByText("No screenings scheduled."),
    ).toBeInTheDocument();
  });

  it("renders a back button that calls onBack", async () => {
    const client = createClient();
    const onBack = vi.fn();
    render(<MovieDetailPage movie={movie} client={client} onBack={onBack} />);

    await screen.findByRole("heading", { name: "Dune: Part Two" });

    fireEvent.click(screen.getByRole("button", { name: "Back to listings" }));

    expect(onBack).toHaveBeenCalledOnce();
  });

  it("shows one column per date that fits the container width", async () => {
    vi.stubGlobal("ResizeObserver", ControllableResizeObserver);
    ControllableResizeObserver.instances = [];
    const client = createClient();
    render(<MovieDetailPage movie={movie} client={client} />);

    await waitFor(() =>
      expect(client.fetchShowtimes).toHaveBeenCalledTimes(2),
    );

    act(() => lastResizeObserver().emit(900));

    await waitFor(() =>
      expect(client.fetchShowtimes).toHaveBeenCalledTimes(3),
    );
    expect(
      screen.getByRole("button", { name: "Earlier dates" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Later dates" }),
    ).toBeDisabled();
    expect(screen.getAllByText(formatDateLabel("2026-08-03")).length).toBeGreaterThan(0);
    expect(screen.getAllByText(formatDateLabel("2026-08-04")).length).toBeGreaterThan(0);
    expect(screen.getAllByText(formatDateLabel("2026-08-05")).length).toBeGreaterThan(0);

    globalThis.ResizeObserver = defaultResizeObserver;
  });

  it("keeps offscreen date columns out of the accessibility tree", async () => {
    const client = createClient();
    render(<MovieDetailPage movie={movie} client={client} />);

    await screen.findByText("Cinéma Moderne");

    const firstColumn = screen
      .getByRole("heading", { name: formatDateLabel("2026-08-03"), hidden: true })
      .closest("[aria-hidden]");
    const secondColumn = screen
      .getByRole("heading", { name: formatDateLabel("2026-08-04"), hidden: true })
      .closest("[aria-hidden]");
    expect(firstColumn).toHaveAttribute("aria-hidden", "false");
    expect(firstColumn).not.toHaveAttribute("inert");
    expect(secondColumn).toHaveAttribute("aria-hidden", "true");
    expect(secondColumn).toHaveAttribute("inert");
    expect(
      screen.queryByRole("heading", { name: formatDateLabel("2026-08-04") }),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Later dates" }));

    expect(firstColumn).toHaveAttribute("aria-hidden", "true");
    expect(secondColumn).toHaveAttribute("aria-hidden", "false");
  });

  it("makes a selected date accessible and hides newly offscreen columns on resize", async () => {
    vi.stubGlobal("ResizeObserver", ControllableResizeObserver);
    ControllableResizeObserver.instances = [];
    const client = createClient();
    render(<MovieDetailPage movie={movie} client={client} />);

    await screen.findByText("Cinéma Moderne");
    act(() => lastResizeObserver().emit(900));
    const secondColumn = screen
      .getByRole("heading", { name: formatDateLabel("2026-08-04"), hidden: true })
      .closest("[aria-hidden]");
    expect(secondColumn).toHaveAttribute("aria-hidden", "false");

    fireEvent.click(screen.getByRole("button", { name: "Next date" }));
    fireEvent.click(screen.getByRole("button", { name: "Next date" }));
    const thirdColumn = screen
      .getByRole("heading", { name: formatDateLabel("2026-08-05"), hidden: true })
      .closest("[aria-hidden]");
    expect(thirdColumn).toHaveAttribute("aria-hidden", "false");

    act(() => lastResizeObserver().emit(288));

    await waitFor(() => expect(secondColumn).toHaveAttribute("aria-hidden", "true"));
    expect(thirdColumn).toHaveAttribute("aria-hidden", "false");
    expect(secondColumn).toHaveAttribute("inert");

    globalThis.ResizeObserver = defaultResizeObserver;
  });

  it("keeps the chosen date visible when the viewport narrows", async () => {
    vi.stubGlobal("ResizeObserver", ControllableResizeObserver);
    ControllableResizeObserver.instances = [];
    const client = createClient();
    const onDateChange = vi.fn();
    render(
      <MovieDetailPage
        movie={movie}
        client={client}
        onDateChange={onDateChange}
      />,
    );

    await waitFor(() => expect(client.fetchShowtimes).toHaveBeenCalledTimes(2));
    act(() => lastResizeObserver().emit(900));

    fireEvent.click(screen.getByRole("button", { name: "Next date" }));
    fireEvent.click(screen.getByRole("button", { name: "Next date" }));

    expect(
      screen.getByRole("button", {
        name: `Open calendar, selected ${formatDateLabel("2026-08-05")}`,
      }),
    ).toBeInTheDocument();
    expect(onDateChange).toHaveBeenCalledWith("2026-08-05", "user");

    act(() => lastResizeObserver().emit(288));

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Earlier dates" }),
      ).not.toBeDisabled(),
    );
    expect(screen.getByRole("button", { name: "Later dates" })).toBeDisabled();

    globalThis.ResizeObserver = defaultResizeObserver;
  });

  it("shows an error and retries when the dates cannot be loaded", async () => {
    let fail = true;
    const client = createClient({
      listDates: vi.fn(async () => {
        if (fail) {
          throw new Error("network");
        }
        return dates;
      }),
    });
    render(<MovieDetailPage movie={movie} client={client} />);

    expect(
      await screen.findByText("Could not load the movie's screening dates."),
    ).toBeInTheDocument();

    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Cinéma Moderne")).toBeInTheDocument();
  });

  it("shows an error and retries when a date's showtimes fail", async () => {
    let fail = true;
    const client = createClient({
      fetchShowtimes: vi.fn(async (_m: MovieCardData, date: string) => {
        if (fail) {
          throw new Error("network");
        }
        return byDate[date] ?? [];
      }),
    });
    render(<MovieDetailPage movie={movie} client={client} />);

    expect(
      await screen.findByText(/Could not load showtimes for/),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText("Couldn't load showtimes.").length,
    ).toBeGreaterThan(0);

    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Cinéma Moderne")).toBeInTheDocument();
    expect(screen.queryByText("Couldn't load showtimes.")).not.toBeInTheDocument();
  });

  it("refetches from scratch when the movie changes", async () => {
    const client = createClient();
    const otherMovie: MovieCardData = {
      title: "Anora",
      releaseYear: 2024,
      durationMinutes: 139,
      directors: ["Sean Baker"],
      genres: ["Comedy", "Drama"],
    };
    const { rerender } = render(
      <MovieDetailPage movie={movie} client={client} />,
    );

    await screen.findByRole("heading", { name: "Dune: Part Two" });
    await screen.findByText("Cinéma Moderne");

    rerender(<MovieDetailPage movie={otherMovie} client={client} />);

    expect(
      await screen.findByRole("heading", { name: "Anora" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Dune: Part Two" }),
    ).not.toBeInTheDocument();
    expect(client.listDates).toHaveBeenLastCalledWith(otherMovie);
    await waitFor(() =>
      expect(client.fetchShowtimes).toHaveBeenCalledWith(otherMovie, "2026-08-03"),
    );
  });

  it("ignores showtimes that resolve after the movie has changed", async () => {
    const otherMovie: MovieCardData = {
      title: "Anora",
      releaseYear: 2024,
      durationMinutes: 139,
      directors: ["Sean Baker"],
      genres: ["Comedy", "Drama"],
    };
    const pendings = new Map<
      string,
      { resolve: (value: readonly CinemaShowtime[]) => void }
    >();
    const client = createClient({
      fetchShowtimes: vi.fn((m: MovieCardData, date: string) => {
        const pending = deferred<readonly CinemaShowtime[]>();
        pendings.set(`${m.title}::${date}`, pending);
        return pending.promise;
      }),
    });
    const { rerender } = render(
      <MovieDetailPage movie={movie} client={client} />,
    );

    await waitFor(() =>
      expect(pendings.has("Dune: Part Two::2026-08-03")).toBe(true),
    );

    rerender(<MovieDetailPage movie={otherMovie} client={client} />);

    await waitFor(() =>
      expect(pendings.has("Anora::2026-08-03")).toBe(true),
    );

    act(() => {
      pendings.get("Anora::2026-08-03")?.resolve(dayTwo);
      pendings.get("Anora::2026-08-04")?.resolve([]);
    });

    expect(await screen.findByText("Cinémathèque québécoise")).toBeInTheDocument();

    act(() => {
      pendings.get("Dune: Part Two::2026-08-03")?.resolve(dayOne);
      pendings.get("Dune: Part Two::2026-08-04")?.resolve(dayOne);
    });

    await waitFor(() => {
      expect(screen.queryByText("Cinéma Moderne")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Cinémathèque québécoise")).toBeInTheDocument();
  });

  it("clears the fetch error banner once a failed date loads successfully", async () => {
    vi.stubGlobal("ResizeObserver", ControllableResizeObserver);
    ControllableResizeObserver.instances = [];
    let fail = true;
    const client = createClient({
      fetchShowtimes: vi.fn(async (_m: MovieCardData, date: string) => {
        if (fail && date === "2026-08-03") {
          throw new Error("network");
        }
        return byDate[date] ?? [];
      }),
    });
    render(<MovieDetailPage movie={movie} client={client} />);

    expect(
      await screen.findByText(/Could not load showtimes for/),
    ).toBeInTheDocument();

    fail = false;
    act(() => lastResizeObserver().emit(900));

    await waitFor(() => {
      expect(
        screen.queryByText(/Could not load showtimes for/),
      ).not.toBeInTheDocument();
    });

    globalThis.ResizeObserver = defaultResizeObserver;
  });

  it("retrying a date failure does not reload the dates list", async () => {
    let fail = true;
    const client = createClient({
      fetchShowtimes: vi.fn(async (_m: MovieCardData, date: string) => {
        if (fail) {
          throw new Error("network");
        }
        return byDate[date] ?? [];
      }),
    });
    render(<MovieDetailPage movie={movie} client={client} />);

    expect(
      await screen.findByText(/Could not load showtimes for/),
    ).toBeInTheDocument();

    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Cinéma Moderne")).toBeInTheDocument();
    expect(client.listDates).toHaveBeenCalledTimes(1);
  });
});
