import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type {
  BrowseClient,
  CinemaApi,
  MovieApi,
  Page,
  ScreeningApi,
  ScreeningMovieApi,
} from "marquise-client";
import { MovieNotFoundError } from "marquise-client";
import { App } from "./App";

const movie: MovieApi = {
  id: "movie-1",
  title: "Wanted film",
  release_year: 2026,
  directors: ["A Director"],
  cast: null,
  duration_minutes: 120,
  description: "A real catalogue entry.",
  poster_url: "https://images.example/poster.jpg",
  trailer_url: null,
  genres: null,
  original_title: null,
  rating: null,
  origin_countries: null,
};
const show: ScreeningApi = {
  id: "show-1",
  movie_id: movie.id,
  movie_title: movie.title,
  cinema_id: "c1",
  cinema_name: "Cinema One",
  showtime: "2026-11-01T23:00:00Z",
  ticket_url: "https://tickets.example/seat",
  room: null,
  language: "VOSTF",
};
function page<T>(items: T[]): Page<T> {
  return { items, total: items.length, page: 1, pages: 1, size: 24 };
}
function clients() {
  return {
    fetchCinemaPage: vi.fn<BrowseClient["fetchCinemaPage"]>(async () =>
      page<CinemaApi>([
        {
          id: "c1",
          name: "Cinema One",
          address: null,
          city: "Montreal",
          website: null,
        },
      ]),
    ),
    fetchScreeningMoviesPage: vi.fn<BrowseClient["fetchScreeningMoviesPage"]>(
      async () =>
        page<ScreeningMovieApi>([
          {
            ...movie,
            screenings: [
              show,
              { ...show, id: "show-2", ticket_url: null, language: "VO" },
            ],
          },
        ]),
    ),
    fetchMoviePage: vi.fn<BrowseClient["fetchMoviePage"]>(async () =>
      page([{ ...movie, id: "catalogue-only", title: "Catalogue only" }]),
    ),
    fetchMovieMetadata: vi.fn<BrowseClient["fetchMovieMetadata"]>(
      async (id) => ({ ...movie, id }),
    ),
    fetchScreeningRangePage: vi.fn<BrowseClient["fetchScreeningRangePage"]>(
      async () => page([show]),
    ),
  };
}
beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-02T01:00:00Z")); // Still November 1 in Montreal.
  history.replaceState(null, "", "/");
  vi.stubGlobal("scrollTo", vi.fn());
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

it("opens today's movie-first page without catalogue reads or poster fan-out", async () => {
  const client = clients();
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledExactlyOnceWith(
    {
      start: "2026-11-01",
      end: "2026-11-01",
      page: 1,
      title: "",
      cinemas: [],
      languages: [],
      startHour: 0,
      endHour: 24,
    },
    expect.any(AbortSignal),
  );
  expect(client.fetchMoviePage).not.toHaveBeenCalled();
  expect(client.fetchScreeningRangePage).not.toHaveBeenCalled();
  expect(
    screen
      .getByRole("link", { name: "Screenings" })
      .getAttribute("aria-current"),
  ).toBe("page");
  expect(screen.queryByRole("heading", { name: "Screenings" })).toBeNull();
  expect(screen.getByText("Today")).not.toBeNull();
  expect(screen.getByText("Filters")).not.toBeNull();
  expect(screen.getByText("About this section").closest("details")?.open).toBe(
    false,
  );
});

it("shows Screenings filters, shares their URL state, and restores browser history", async () => {
  const client = clients();
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  fireEvent.click(screen.getByText("Filters"));
  fireEvent.click(screen.getByLabelText("Cinema One"));
  fireEvent.click(screen.getByLabelText("VOSTF"));
  fireEvent.change(screen.getByLabelText("Start date"), {
    target: { value: "2026-11-03" },
  });
  fireEvent.change(screen.getByLabelText("End date"), {
    target: { value: "2026-11-05" },
  });
  await waitFor(() => {
    expect(client.fetchScreeningMoviesPage).toHaveBeenLastCalledWith(
      expect.objectContaining({
        start: "2026-11-03",
        end: "2026-11-05",
        cinemas: ["c1"],
        languages: ["VOSTF"],
      }),
      expect.any(AbortSignal),
    );
  });
  expect(new URL(window.location.href).searchParams.getAll("cinema")).toEqual([
    "c1",
  ]);
  expect(new URL(window.location.href).searchParams.getAll("language")).toEqual([
    "VOSTF",
  ]);
  history.replaceState(
    null,
    "",
    "/?section=screenings&start=2026-11-01&end=2026-11-01",
  );
  fireEvent.popState(window);
  await waitFor(() =>
    expect(
      (screen.getByLabelText("Start date") as HTMLInputElement).value,
    ).toBe("2026-11-01"),
  );
});

it("does not show results from a superseded screening query", async () => {
  const client = clients();
  let resolveOld: (result: Page<ScreeningMovieApi>) => void = () => {};
  client.fetchScreeningMoviesPage = vi
    .fn<BrowseClient["fetchScreeningMoviesPage"]>()
    .mockImplementationOnce(
      () => new Promise((resolve) => (resolveOld = resolve)),
    )
    .mockResolvedValueOnce(
      page<ScreeningMovieApi>([
        { ...movie, id: "new", title: "New query result", screenings: [show] },
      ]),
    );
  render(<App client={client} />);
  history.replaceState(
    null,
    "",
    "/?start=2026-11-02&end=2026-11-02",
  );
  fireEvent.popState(window);
  await screen.findByRole("link", { name: "View New query result" });
  resolveOld(
    page<ScreeningMovieApi>([
      { ...movie, id: "old", title: "Old query result", screenings: [show] },
    ]),
  );
  await waitFor(() =>
    expect(screen.queryByRole("link", { name: "View Old query result" })).toBeNull(),
  );
  expect(client.fetchScreeningMoviesPage.mock.calls[0]?.[1]?.aborted).toBe(true);
});

it("uses separate date-independent endpoint search and keeps navigation active", async () => {
  const client = clients();
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  fireEvent.click(screen.getByRole("link", { name: "Movies" }));
  await screen.findByRole("link", { name: "View Catalogue only" });
  fireEvent.change(screen.getByRole("searchbox", { name: "Search movies" }), {
    target: { value: "never screened" },
  });
  await waitFor(() =>
    expect(client.fetchMoviePage).toHaveBeenLastCalledWith(
      1,
      expect.any(AbortSignal),
      "never screened",
      24,
    ),
  );
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("link", { name: "View Wanted film" })).toBeNull();
  expect(
    screen.getByRole("link", { name: "Movies" }).getAttribute("aria-current"),
  ).toBe("page");
  fireEvent.click(screen.getByRole("link", { name: "Cinemas" }));
  expect(
    screen.getByRole("link", { name: "Cinemas" }).getAttribute("aria-current"),
  ).toBe("page");
  expect(screen.getByRole("link", { name: "Screenings" })).toBeTruthy();
});

it("keeps preview activation separate, displays languages, and preserves booking links", async () => {
  render(<App client={clients()} />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Preview Wanted film" }),
  );
  expect(location.pathname).toBe("/");
  const preview = screen.getByRole("region", {
    name: "Wanted film screenings",
  });
  const booking = within(preview).getByRole("link", { name: "18:00" });
  expect(booking.getAttribute("href")).toBe(show.ticket_url);
  expect(booking.getAttribute("target")).toBe("_blank");
  expect(within(preview).getByText("VO")).toBeTruthy();
  expect(within(preview).getAllByRole("link")).toHaveLength(2);
  fireEvent.keyDown(preview, { key: "Escape" });
  expect(
    screen.queryByRole("region", { name: "Wanted film screenings" }),
  ).toBeNull();
  expect(document.activeElement).toBe(
    screen.getByRole("button", { name: "Preview Wanted film" }),
  );
});

it("loads exact metadata and a schedule on catalogue direct entry with no cached shows", async () => {
  history.replaceState(null, "", "/movies/catalogue%2Fid");
  const client = clients();
  render(<App client={client} />);
  await screen.findByRole("heading", { name: movie.title });
  await waitFor(() =>
    expect(client.fetchScreeningRangePage).toHaveBeenCalledExactlyOnceWith(
      "catalogue/id",
      "2026-11-01",
      "2026-11-04",
      1,
      expect.any(AbortSignal),
    ),
  );
  expect(client.fetchMovieMetadata).toHaveBeenCalledWith(
    "catalogue/id",
    expect.any(AbortSignal),
  );
  expect(client.fetchScreeningMoviesPage).not.toHaveBeenCalled();
  expect(client.fetchMoviePage).not.toHaveBeenCalled();
  expect(
    screen.getByRole("link", { name: "Movies" }).getAttribute("aria-current"),
  ).toBe("page");
});

it("shows an initial screening error with Retry, then an honest empty state", async () => {
  const client = clients();
  client.fetchScreeningMoviesPage
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce(page([]));
  render(<App client={client} />);
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Could not load screenings.Retry",
  );
  expect(
    screen.queryByRole("heading", { name: "No matching screenings" }),
  ).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByRole("heading", { name: "No matching screenings" });
  expect(screen.queryByRole("button", { name: "Reset selection" })).not.toBeNull();
  fireEvent.click(screen.getByRole("link", { name: "Movies" }));
  await screen.findByRole("link", { name: "View Catalogue only" });
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledTimes(2);
});

it("distinguishes catalogue loading, failure and Retry from screening state", async () => {
  history.replaceState(null, "", "/?section=movies");
  const client = clients();
  client.fetchMoviePage.mockRejectedValueOnce(new Error("offline"));
  render(<App client={client} />);
  await screen.findByText("Could not load movies.");
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByRole("link", { name: "View Catalogue only" });
  expect(client.fetchScreeningMoviesPage).not.toHaveBeenCalled();
});

it("ignores old catalogue search responses even if the client ignores cancellation", async () => {
  history.replaceState(null, "", "/?section=movies");
  const client = clients();
  let resolveOld!: (value: Page<MovieApi>) => void;
  client.fetchMoviePage.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        resolveOld = resolve;
      }),
  );
  render(<App client={client} />);
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "new" } });
  await screen.findByRole("link", { name: "View Catalogue only" });
  await act(async () => resolveOld(page([{ ...movie, title: "Stale title" }])));
  expect(screen.queryByRole("link", { name: "View Stale title" })).toBeNull();
  expect(client.fetchMoviePage.mock.calls[0]?.[1]?.aborted).toBe(true);
});

it("handles unknown movies and browser navigation between independent sections", async () => {
  const client = clients();
  client.fetchMovieMetadata.mockRejectedValue(
    new MovieNotFoundError("missing"),
  );
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  await act(async () => {
    history.pushState(null, "", "/movies/missing");
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  await screen.findByRole("heading", { name: "Movie not found" });
  await act(async () => {
    history.replaceState(null, "", "/?section=movies");
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  await screen.findByRole("link", { name: "View Catalogue only" });
});

it("handles malformed movie URL escapes without crashing navigation", async () => {
  history.replaceState(null, "", "/movies/bad%escape");
  const client = clients();
  client.fetchMovieMetadata.mockRejectedValue(
    new MovieNotFoundError("bad%escape"),
  );
  render(<App client={client} />);
  await screen.findByRole("heading", { name: "Movie not found" });
  expect(client.fetchMovieMetadata).toHaveBeenCalledWith(
    "bad%escape",
    expect.any(AbortSignal),
  );
  expect(screen.getByRole("link", { name: "Screenings" })).toBeTruthy();
});
