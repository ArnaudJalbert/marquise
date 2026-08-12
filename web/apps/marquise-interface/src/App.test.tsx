import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type {
  MovieCardData,
  MovieCardGridItem,
  MovieDetailClient,
  MovieGridClient,
} from "marquise-components";
import { MovieNotFoundError } from "marquise-client";

import { App } from "./App";

const DATE = "2026-08-08";

class AutoResizeObserver implements ResizeObserver {
  constructor(private readonly callback: ResizeObserverCallback) {}

  observe(target: Element): void {
    const width = target.classList.contains("overflow-hidden") ? 288 : 896;
    this.callback(
      [{ contentRect: { width, height: 600 } } as ResizeObserverEntry],
      this,
    );
  }

  unobserve(): void {}
  disconnect(): void {}
}

function movie(index: number): MovieCardData {
  return { id: `movie-${index}`, title: `Movie ${index}` };
}

function createClients(): {
  grid: MovieGridClient;
  detail: MovieDetailClient;
} {
  const items: MovieCardGridItem[] = Array.from({ length: 10 }, (_, index) => ({
    key: `movie-${index + 1}`,
    movie: movie(index + 1),
    showtimesUrl: "#",
    showtimes: [
      {
        startsAt: `${DATE}T23:00:00-04:00`,
        ticketUrl: "#",
        cinema: { id: "cinema-1", name: "Cinema One", link: "#" },
      },
    ],
  }));
  return {
    grid: {
      listDates: vi.fn(async () => [DATE, "2026-08-09"]),
      fetchForDate: vi.fn(async () => items),
    },
    detail: {
      fetchMovie: vi.fn(async (movieId) => {
        const found = items.find((item) => item.movie.id === movieId)?.movie;
        if (found === undefined) throw new MovieNotFoundError(movieId);
        return found;
      }),
      listDates: vi.fn(async () => [DATE, "2026-08-09"]),
      fetchShowtimes: vi.fn(async () => []),
    },
  };
}

beforeEach(() => {
  history.replaceState(null, "", "/");
  vi.stubGlobal("ResizeObserver", AutoResizeObserver);
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(200);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.title = "";
});

describe("App URL navigation", () => {
  it("pushes page navigation and replaces display-control state", async () => {
    history.replaceState(null, "", `/?date=${DATE}&from=0&to=24`);
    const clients = createClients();
    render(<App movieGridClient={clients.grid} movieDetailClient={clients.detail} />);

    await screen.findByRole("heading", { name: "Movie 1" });
    const pushState = vi.spyOn(history, "pushState");
    const replaceState = vi.spyOn(history, "replaceState");

    fireEvent.click(screen.getByRole("checkbox", { name: "Show details" }));
    expect(window.location.search).toContain("details=hidden");
    expect(replaceState).toHaveBeenCalled();
    expect(pushState).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(window.location.search).toContain("page=2");
    expect(pushState).toHaveBeenCalled();
  });

  it("opens a dedicated movie route and Back restores the exact listings page", async () => {
    const initialUrl =
      `/?date=${DATE}&from=0&to=24&page=2&card=240` +
      "&details=hidden&filters=closed";
    history.replaceState(null, "", initialUrl);
    const clients = createClients();
    render(
      <StrictMode>
        <App movieGridClient={clients.grid} movieDetailClient={clients.detail} />
      </StrictMode>,
    );

    expect(
      await screen.findByRole("heading", { name: "Movie 9" }),
    ).not.toBeNull();
    const listingsHref = window.location.href;

    fireEvent.click(screen.getByRole("button", { name: "Movie 9" }));

    await waitFor(() =>
      expect(window.location.pathname).toBe("/movies/movie-9"),
    );
    expect(window.location.search).toBe(`?date=${DATE}`);
    expect(
      await screen.findByRole("heading", { name: "Movie 9", level: 1 }),
    ).not.toBeNull();

    fireEvent.click(
      await screen.findByRole("button", { name: "Later dates" }),
    );
    expect(window.location.search).toBe("?date=2026-08-09");

    fireEvent.click(screen.getByRole("button", { name: "Back to listings" }));

    await waitFor(() => expect(window.location.href).toBe(listingsHref));
    expect(
      await screen.findByRole("heading", { name: "Movie 9" }),
    ).not.toBeNull();
    expect(screen.getByText("2 / 2")).not.toBeNull();

    history.forward();
    await waitFor(() =>
      expect(window.location.pathname).toBe("/movies/movie-9"),
    );
    expect(window.location.search).toBe("?date=2026-08-09");
  });

  it("loads a directly visited movie URL by id", async () => {
    history.replaceState(null, "", `/movies/movie-1?date=${DATE}`);
    const clients = createClients();

    render(<App movieGridClient={clients.grid} movieDetailClient={clients.detail} />);

    expect(
      await screen.findByRole("heading", { name: "Movie 1", level: 1 }),
    ).not.toBeNull();
    expect(clients.detail.fetchMovie).toHaveBeenCalledWith("movie-1");
    expect(document.title).toBe("Movie 1 — Marquise");
  });

  it("falls back to listings from a direct movie link", async () => {
    history.replaceState(null, "", `/movies/missing?date=${DATE}`);
    const clients = createClients();
    render(<App movieGridClient={clients.grid} movieDetailClient={clients.detail} />);

    expect(await screen.findByText("Movie not found.")).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Back to listings" }));

    await waitFor(() => expect(window.location.pathname).toBe("/"));
    expect(
      await screen.findByRole("heading", { name: "Movie 1" }),
    ).not.toBeNull();
  });
});
