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
const endObservers: TestIntersectionObserver[] = [];
class TestIntersectionObserver implements IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "0px";
  readonly scrollMargin = "0px";
  readonly thresholds = [0];
  private target?: Element;
  connected = false;

  constructor(private readonly callback: IntersectionObserverCallback) {
    endObservers.push(this);
  }

  observe(target: Element) {
    this.target = target;
    this.connected = true;
  }

  unobserve() {}
  disconnect() {
    this.connected = false;
  }
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }

  reachEnd() {
    if (!this.target || !this.connected) throw new Error("No connected end sentinel");
    this.callback(
      [{ isIntersecting: true, target: this.target } as IntersectionObserverEntry],
      this,
    );
  }
}
// findBy* can resolve on the DOM commit before the sentinel effect subscribes, and
// earlier observers are disconnected when a page starts loading, so wait for a connected one.
async function reachEnd(times = 1) {
  const observer = await waitFor(() => {
    const latest = endObservers.filter((candidate) => candidate.connected).at(-1);
    if (!latest) throw new Error("End sentinel not subscribed yet");
    return latest;
  });
  await act(async () => {
    for (let call = 0; call < times; call++) observer.reachEnd();
  });
}
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
    fetchUpcomingScreeningsPage: vi.fn<
      BrowseClient["fetchUpcomingScreeningsPage"]
    >(async () => page([show])),
  };
}
beforeEach(() => {
  endObservers.length = 0;
  vi.stubGlobal("IntersectionObserver", TestIntersectionObserver);
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-01T22:00:00Z")); // Still November 1 in Montreal.
  history.replaceState(null, "", "/");
  vi.stubGlobal("scrollTo", vi.fn());
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

it("appends catalogue pages at the end and stops at the reported last page", async () => {
  history.replaceState(null, "", "/?section=movies");
  const client = clients();
  const pages = Array.from({ length: 3 }, (_, pageIndex) =>
    Array.from({ length: pageIndex === 2 ? 1 : 2 }, (_, itemIndex) => {
      const number = pageIndex * 2 + itemIndex + 1;
      const id = `movie-${number}`;
      const title = `Movie ${number}`;
      return {
        ...movie,
        id,
        title,
        screenings: [{ ...show, movie_id: id, movie_title: title }],
      };
    }),
  );
  client.fetchScreeningMoviesPage.mockImplementation(
    async ({ page: requestedPage }) => ({
      items: pages[requestedPage - 1] ?? [],
      total: 5,
      page: requestedPage,
      size: 2,
      pages: 3,
    }),
  );
  render(<App client={client} />);

  await screen.findByRole("link", { name: "View Movie 2" });
  expect(screen.queryByRole("link", { name: "View Movie 3" })).toBeNull();
  await reachEnd(2);
  await screen.findByRole("link", { name: "View Movie 3" });
  expect(client.fetchScreeningMoviesPage).toHaveBeenNthCalledWith(
    2,
    { start: "2026-11-01", page: 2, title: undefined },
    expect.any(AbortSignal),
  );
  await reachEnd();
  await screen.findByRole("link", { name: "View Movie 5" });
  expect(screen.getAllByRole("article")).toHaveLength(5);
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledTimes(3);
  expect(endObservers.some((candidate) => candidate.connected)).toBe(false);
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledTimes(3);
});

it("appends distinct screening movies when their end enters view", async () => {
  const client = clients();
  const result = (id: string, title: string, pageNumber: number) => ({
    items: [id].map((movieId) => ({
      ...movie,
      id: movieId,
      title,
      screenings: [{ ...show, movie_id: movieId, movie_title: title }],
    })),
    total: 3,
    page: pageNumber,
    size: 24,
    pages: 2,
  });
  client.fetchScreeningMoviesPage.mockImplementation(async (query) =>
    query.page === 1
      ? {
          ...result("screening-1", "Screening 1", 1),
          items: [
            ...result("screening-1", "Screening 1", 1).items,
            ...result("screening-2", "Screening 2", 1).items,
          ],
        }
      : {
          ...result("screening-3", "Screening 3", 2),
          items: [
            ...result("screening-2", "Screening 2", 2).items,
            ...result("screening-3", "Screening 3", 2).items,
          ],
        },
  );
  render(<App client={client} />);

  await screen.findByRole("link", { name: "View Screening 2" });
  await reachEnd();
  await screen.findByRole("link", { name: "View Screening 3" });
  expect(screen.getAllByRole("link", { name: "View Screening 2" })).toHaveLength(
    1,
  );
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledTimes(2);
  expect(client.fetchScreeningMoviesPage.mock.calls[1]?.[0].page).toBe(2);
});

it("keeps loaded catalogue movies after a page failure and retries that page", async () => {
  history.replaceState(null, "", "/?section=movies");
  const client = clients();
  const movies = Array.from({ length: 25 }, (_, index) => {
    const id = `movie-${index + 1}`;
    const title = `Movie ${index + 1}`;
    return {
      ...movie,
      id,
      title,
      screenings: [{ ...show, movie_id: id, movie_title: title }],
    };
  });
  let failNext = true;
  client.fetchScreeningMoviesPage.mockImplementation(
    async ({ page: requestedPage }) => {
      if (requestedPage === 2 && failNext) {
        failNext = false;
        throw new Error("offline");
      }
      return {
        items: requestedPage === 1 ? movies.slice(0, 24) : movies.slice(24),
        total: 25,
        page: requestedPage,
        size: 24,
        pages: 2,
      };
    },
  );
  render(<App client={client} />);

  await screen.findByRole("link", { name: "View Movie 24" });
  await reachEnd();
  await screen.findByRole("alert");
  expect(screen.getByRole("link", { name: "View Movie 1" })).toBeTruthy();
  expect(screen.queryByRole("link", { name: "View Movie 25" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByRole("link", { name: "View Movie 25" });
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledTimes(3);
});

it("resets a fresh visit to Today and keeps the other filters", async () => {
  /** Scenario: a loaded URL drops its period; only in-session history keeps one. */
  history.replaceState(
    null,
    "",
    "/?start=2026-11-03&end=2026-11-05&cinema=c1&q=Wanted",
  );
  const client = clients();
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  expect(location.search).toBe("?cinema=c1&q=Wanted");
  expect(screen.getByRole("heading", { level: 1, name: "Today" })).toBeTruthy();
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledExactlyOnceWith(
    expect.objectContaining({
      start: "2026-11-01",
      end: "2026-11-01",
      cinemas: ["c1"],
      title: "Wanted",
    }),
    expect.any(AbortSignal),
  );
});

it.each(["/", "/cinemas/c1"])("restores filtered pages from %s after visiting a movie", async (route) => {
  // Fresh visits open on Today, so the restored listing carries today's period.
  const listing =
    `${route}?start=2026-11-01&end=2026-11-01&cinema=c1&language=VO&q=Wanted&from=18:00&to=22:00`;
  history.replaceState(null, "", listing);
  const client = clients();
  client.fetchScreeningMoviesPage.mockImplementation(
    async ({ page: number }) => ({
      items: [
        {
          ...movie,
          id: `movie-${number}`,
          title: `Wanted ${number}`,
          screenings: [show],
        },
      ],
      total: 2,
      page: number,
      size: 1,
      pages: 2,
    }),
  );
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted 1" });
  await reachEnd();
  fireEvent.click(await screen.findByRole("link", { name: "View Wanted 2" }));
  await screen.findByRole("heading", { name: movie.title });

  history.replaceState({ scrollY: 900 }, "", listing);
  fireEvent.popState(window);
  await screen.findByRole("link", { name: "View Wanted 2" });
  expect(screen.getByRole("link", { name: "View Wanted 1" })).toBeTruthy();
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledTimes(2);
  await waitFor(() =>
    expect(window.scrollTo).toHaveBeenLastCalledWith({
      top: 900,
      behavior: "instant",
    }),
  );

  fireEvent.click(screen.getByRole("link", { name: "Movies" }));
  await screen.findByRole("link", { name: "View Wanted 1" });
  history.replaceState(null, "", listing);
  fireEvent.popState(window);
  await screen.findByRole("link", { name: "View Wanted 2" });
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledTimes(3);
});

it.each([
  ["matinee", "is", [{ start: 0, end: 17 }]],
  ["evening", "is", [{ start: 17, end: 21 }]],
  ["late", "is_not", [{ start: 21, end: 24 }]],
])("sends the %s bucket with the server-side %s operator", async (time, operator, ranges) => {
  history.replaceState(null, "", `/?start=2026-11-03&end=2026-11-03&time=${operator === "is_not" ? "-" : ""}${time}`);
  const client = clients();
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledWith(
    expect.objectContaining({
      hours: { operator, ranges },
    }),
    expect.any(AbortSignal),
  );
});

it("ignores retired language and slider URL parameters", async () => {
  history.replaceState(null, "", "/?language=VOSTF&from=18&to=22");
  const client = clients();
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledWith(
    expect.objectContaining({ hours: undefined, cinemas: [], excludedCinemas: [] }),
    expect.any(AbortSignal),
  );
});

it("ignores unsupported audio and subtitle filters from the URL", async () => {
  history.replaceState(
    null,
    "",
    "/?cinema=c1&time=matinee&audio=VO&subtitles=VOSTF",
  );
  const client = clients();
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });

  expect(screen.getByRole("group", { name: "cinema filter" }).textContent).toContain(
    "Cinema is Cinema One",
  );
  expect(screen.getByRole("group", { name: "time filter" }).textContent).toContain(
    "Time is Matinée",
  );
  expect(screen.queryByRole("group", { name: "audio filter" })).toBeNull();
  expect(screen.queryByRole("group", { name: "subtitles filter" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Clear all" })).not.toBeNull();
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledWith(
    expect.objectContaining({
      cinemas: ["c1"],
      excludedCinemas: [],
      hours: { operator: "is", ranges: [{ start: 0, end: 17 }] },
    }),
    expect.any(AbortSignal),
  );

  fireEvent.click(screen.getByRole("button", { name: "Clear all" }));
  await waitFor(() => {
    const params = new URL(window.location.href).searchParams;
    expect(params.has("audio")).toBe(false);
    expect(params.has("subtitles")).toBe(false);
    expect(client.fetchScreeningMoviesPage).toHaveBeenLastCalledWith(
      expect.objectContaining({ cinemas: [], excludedCinemas: [], hours: undefined }),
      expect.any(AbortSignal),
    );
  });
});

it("sends a negative Cinema chip as a cinema exclusion", async () => {
  history.replaceState(null, "", "/?cinema=-c1");
  const client = clients();
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledWith(
    expect.objectContaining({ cinemas: [], excludedCinemas: ["c1"] }),
    expect.any(AbortSignal),
  );
  expect(screen.getByRole("group", { name: "cinema filter" }).textContent).toContain("Cinema is not Cinema One");
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
      excludedCinemas: [],
      hours: undefined,
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
  expect(screen.getByRole("heading", { level: 1, name: "Today" })).toBeTruthy();
  expect(screen.queryByLabelText("Start date")).toBeNull();
  expect(screen.getByText("+ Filter")).not.toBeNull();
  expect(screen.getByText("About this section").closest("details")?.open).toBe(
    false,
  );
});

it("round-trips cinema and time chips through the URL", async () => {
  const client = clients();
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  fireEvent.click(screen.getByText("+ Filter"));
  fireEvent.click(screen.getByRole("button", { name: "Cinema" }));
  fireEvent.click(screen.getByText("+ Filter"));
  fireEvent.click(screen.getByRole("button", { name: "Time" }));
  fireEvent.click(screen.getByRole("button", { name: "Change time operator from is" }));
  fireEvent.click(screen.getByRole("button", { name: "Next period" }));
  await waitFor(() => {
    expect(client.fetchScreeningMoviesPage).toHaveBeenLastCalledWith(
      expect.objectContaining({
        start: "2026-11-02",
        end: "2026-11-02",
        cinemas: ["c1"],
        excludedCinemas: [],
        hours: { operator: "is_not", ranges: [{ start: 0, end: 17 }] },
      }),
      expect.any(AbortSignal),
    );
  });
  const params = new URL(window.location.href).searchParams;
  expect(params.get("cinema")).toBe("c1");
  expect(params.get("time")).toBe("-matinee");
  expect(params.has("language")).toBe(false);
  expect(params.has("from")).toBe(false);
  expect(params.has("to")).toBe(false);
  expect(screen.getByRole("heading", { level: 1, name: "Tomorrow" })).toBeTruthy();
  expect(new URL(window.location.href).searchParams.get("start")).toBe(
    "2026-11-02",
  );
  history.replaceState(
    null,
    "",
    "/?section=screenings&start=2026-11-01&end=2026-11-01&cinema=c1&time=-matinee",
  );
  fireEvent.popState(window);
  await screen.findByRole("heading", { level: 1, name: "Today" });
  expect(screen.getByRole("group", { name: "cinema filter" }).textContent).toContain("Cinema is Cinema One");
  expect(screen.getByRole("group", { name: "time filter" }).textContent).toContain("Time is not Matinée");
});

it("keeps the movie search focused while its URL and results update", async () => {
  /** Scenario: typing in the screenings search field queries by title, writes `q` to the URL and keeps focus. */
  const client = clients();
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  const search = screen.getByRole("searchbox", { name: "Search movies" });
  search.focus();
  fireEvent.change(search, { target: { value: "Dune" } });

  await waitFor(() => {
    expect(client.fetchScreeningMoviesPage).toHaveBeenLastCalledWith(
      expect.objectContaining({ title: "Dune" }),
      expect.any(AbortSignal),
    );
  });
  const params = new URL(window.location.href).searchParams;
  expect(params.get("q")).toBe("Dune");
  expect(params.has("title")).toBe(false);
  expect(document.activeElement).toBe(search);
});

it("restores movie search from `q` and ignores the old `title` param", async () => {
  /** Scenario: a shared link with `q` opens with that search; an old `title` link opens unsearched. */
  history.replaceState(null, "", "/?start=2026-11-01&end=2026-11-01&q=Wanted");
  const client = clients();
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  expect(
    (screen.getByRole("searchbox", { name: "Search movies" }) as HTMLInputElement)
      .value,
  ).toBe("Wanted");
  expect(client.fetchScreeningMoviesPage).toHaveBeenLastCalledWith(
    expect.objectContaining({ title: "Wanted" }),
    expect.any(AbortSignal),
  );

  history.replaceState(null, "", "/?start=2026-11-01&end=2026-11-01&title=Wanted");
  fireEvent.popState(window);
  await waitFor(() =>
    expect(
      (screen.getByRole("searchbox", { name: "Search movies" }) as HTMLInputElement)
        .value,
    ).toBe(""),
  );
  expect(client.fetchScreeningMoviesPage).toHaveBeenLastCalledWith(
    expect.objectContaining({ title: "" }),
    expect.any(AbortSignal),
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

it("searches only movies with upcoming screenings and keeps navigation active", async () => {
  const client = clients();
  client.fetchScreeningMoviesPage.mockImplementation(async ({ end, title }) =>
    title
      ? page<ScreeningMovieApi>([])
      : page<ScreeningMovieApi>([
          {
            ...movie,
            id: end ? movie.id : "upcoming",
            title: end ? movie.title : "Upcoming film",
            screenings: [show],
          },
        ]),
  );
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  fireEvent.click(screen.getByRole("link", { name: "Movies" }));
  await screen.findByRole("link", { name: "View Upcoming film" });
  fireEvent.change(screen.getByRole("searchbox", { name: "Search movies" }), {
    target: { value: "never screened" },
  });
  await waitFor(() =>
    expect(client.fetchScreeningMoviesPage).toHaveBeenLastCalledWith(
      {
        start: "2026-11-01",
        page: 1,
        title: "never screened",
      },
      expect.any(AbortSignal),
    ),
  );
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledTimes(3);
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

it("loads the cinema directory and fixes screening results to the selected venue", async () => {
  history.replaceState(null, "", "/cinemas");
  const client = clients();
  client.fetchCinemaPage.mockResolvedValueOnce({
    items: [
      {
        id: "c1",
        name: "Cinema One",
        address: "123 Example Street",
        city: "Montréal",
        website: "https://cinema.example",
      },
    ],
    total: 1,
    page: 1,
    pages: 1,
    size: 100,
  });
  render(<App client={client} />);
  const venue = await screen.findByRole("link", { name: "Cinema One" });
  fireEvent.click(venue);
  expect(await screen.findByRole("heading", { name: "Cinema One" })).toBeTruthy();
  expect(screen.getByText("123 Example Street")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Cinema website" }).getAttribute("href")).toBe(
    "https://cinema.example",
  );
  expect(screen.queryByRole("group", { name: "Cinemas" })).toBeNull();
  await waitFor(() =>
    expect(client.fetchScreeningMoviesPage).toHaveBeenCalledWith(
      expect.objectContaining({ cinemas: ["c1"] }),
      expect.any(AbortSignal),
    ),
  );
  history.replaceState(null, "", "/cinemas/c1?cinema=other");
  window.dispatchEvent(new PopStateEvent("popstate"));
  await screen.findByRole("heading", { name: "Cinema One" });
  await waitFor(() =>
    expect(client.fetchScreeningMoviesPage).toHaveBeenLastCalledWith(
      expect.objectContaining({ cinemas: ["c1"] }),
      expect.any(AbortSignal),
    ),
  );
});

it("reads every cinema directory page", async () => {
  history.replaceState(null, "", "/cinemas");
  const client = clients();
  client.fetchCinemaPage.mockImplementation(async (pageNumber) => ({
    items: [
      {
        id: `c${pageNumber}`,
        name: `Cinema ${pageNumber}`,
        address: null,
        city: "Montréal",
        website: null,
      },
    ],
    total: 2,
    page: pageNumber,
    pages: 2,
    size: 1,
  }));
  render(<App client={client} />);
  expect(await screen.findByRole("link", { name: "Cinema 2" })).toBeTruthy();
  expect(client.fetchCinemaPage).toHaveBeenNthCalledWith(
    1,
    1,
    expect.any(AbortSignal),
  );
  expect(client.fetchCinemaPage).toHaveBeenNthCalledWith(
    2,
    2,
    expect.any(AbortSignal),
  );
});

it("previews a movies section card from its upcoming screenings as of now", async () => {
  history.replaceState(null, "", "/?section=movies");
  const client = clients();
  render(<App client={client} />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Preview Wanted film" }),
  );
  const preview = screen.getByRole("region", {
    name: "Wanted film screenings",
  });
  const booking = await within(preview).findByRole("link", { name: "18:00" });
  expect(booking.getAttribute("href")).toBe(show.ticket_url);
  expect(within(preview).getByText("VOSTF")).toBeTruthy();
  expect(within(preview).getByText("Cinema One")).toBeTruthy();
  expect(client.fetchUpcomingScreeningsPage).toHaveBeenCalledExactlyOnceWith(
    movie.id,
    "2026-11-01T22:00:00.000Z",
    expect.any(AbortSignal),
  );
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
      "2026-10-02",
      "2027-01-30",
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

it("loads every page in the movie's requested Montréal date window", async () => {
  history.replaceState(null, "", "/movies/movie-1");
  const client = clients();
  const secondShow = {
    ...show,
    id: "show-2",
    showtime: "2026-11-02T15:00:00Z",
    ticket_url: null,
  };
  client.fetchScreeningRangePage.mockImplementation(
    async (_id, _start, _end, pageNumber) => ({
      items: pageNumber === 1 ? [show] : [secondShow],
      total: 2,
      page: pageNumber,
      pages: 2,
      size: 100,
    }),
  );
  render(<App client={client} />);
  expect(await screen.findByText("18:00")).toBeTruthy();
  expect(await screen.findByText("10:00")).toBeTruthy();
  expect(client.fetchScreeningRangePage).toHaveBeenNthCalledWith(
    1,
    "movie-1",
    "2026-10-02",
    "2027-01-30",
    1,
    expect.any(AbortSignal),
  );
  expect(client.fetchScreeningRangePage).toHaveBeenNthCalledWith(
    2,
    "movie-1",
    "2026-10-02",
    "2027-01-30",
    2,
    expect.any(AbortSignal),
  );
});

it("does not refetch a movie schedule when the clock updates", async () => {
  history.replaceState(null, "", "/movies/movie-1");
  const client = clients();
  render(<App client={client} />);
  expect(await screen.findByText("18:00")).toBeTruthy();
  expect(client.fetchScreeningRangePage).toHaveBeenCalledOnce();
  await act(async () => {
    vi.advanceTimersByTime(60_000);
  });
  expect(client.fetchScreeningRangePage).toHaveBeenCalledOnce();
});

it("excludes started screenings from the complete schedule window", async () => {
  history.replaceState(null, "", "/movies/movie-1");
  const client = clients();
  client.fetchScreeningRangePage.mockResolvedValue(page([
    { ...show, id: "past", showtime: "2026-11-01T21:00:00Z" },
    { ...show, id: "now", showtime: "2026-11-01T22:00:00Z" },
    show,
  ]));
  render(<App client={client} />);
  expect(await screen.findByText("18:00")).toBeTruthy();
  expect(screen.queryByText("16:00")).toBeNull();
  expect(screen.queryByText("17:00")).toBeNull();
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
    screen.queryByRole("heading", { name: "No screenings left today" }),
  ).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByRole("heading", { name: "No screenings left today" });
  expect(screen.queryByRole("button", { name: "See tomorrow" })).not.toBeNull();
  fireEvent.click(screen.getByRole("link", { name: "Movies" }));
  await screen.findByRole("link", { name: "View Wanted film" });
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledTimes(3);
});

it("distinguishes catalogue loading, failure and Retry from screening state", async () => {
  history.replaceState(null, "", "/?section=movies");
  const client = clients();
  client.fetchScreeningMoviesPage.mockRejectedValueOnce(new Error("offline"));
  render(<App client={client} />);
  await screen.findByText("Could not load movies.");
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByRole("link", { name: "View Wanted film" });
  expect(client.fetchScreeningMoviesPage).toHaveBeenCalledTimes(2);
});

it("ignores old catalogue search responses even if the client ignores cancellation", async () => {
  history.replaceState(null, "", "/?section=movies");
  const client = clients();
  let resolveOld!: (value: Page<ScreeningMovieApi>) => void;
  client.fetchScreeningMoviesPage.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        resolveOld = resolve;
      }),
  );
  render(<App client={client} />);
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "new" } });
  await screen.findByRole("link", { name: "View Wanted film" });
  await act(async () =>
    resolveOld(
      page<ScreeningMovieApi>([
        { ...movie, title: "Stale title", screenings: [show] },
      ]),
    ),
  );
  expect(screen.queryByRole("link", { name: "View Stale title" })).toBeNull();
  expect(client.fetchScreeningMoviesPage.mock.calls[0]?.[1]?.aborted).toBe(true);
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
  await screen.findByRole("link", { name: "View Wanted film" });
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

function destinationLinks(name: string) {
  return within(screen.getByRole("navigation", { name }))
    .getAllByRole("link")
    .map((link) => [link.getAttribute("aria-label") ?? link.textContent, link.getAttribute("href")]);
}

it("offers the same five destinations in the footer and the header Info menu", async () => {
  render(<App client={clients()} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  fireEvent.click(screen.getByRole("button", { name: "Info" }));

  const footer = destinationLinks("Footer");
  expect(footer).toEqual([
    ["About", "/about"],
    ["API docs (external site: api.marquise.mov)", "https://api.marquise.mov/docs"],
    ["Contact", "/contact"],
    ["Terms", "/terms"],
    ["Privacy", "/privacy"],
  ]);
  expect(destinationLinks("Site information")).toEqual(footer);
  expect(within(screen.getByRole("contentinfo")).getByText("Marquise")).toBeTruthy();

  const apiDocs = within(screen.getByRole("navigation", { name: "Footer" })).getByRole("link", {
    name: "API docs (external site: api.marquise.mov)",
  });
  expect(apiDocs.hasAttribute("target")).toBe(false);
  expect(apiDocs.textContent).toBe("API docs↗");
});

it("opens Info, closes it with Escape and restores focus, then navigates from it", async () => {
  const client = clients();
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Wanted film" });
  const info = screen.getByRole("button", { name: "Info" });
  expect(info.getAttribute("aria-expanded")).toBe("false");
  expect(screen.queryByRole("navigation", { name: "Site information" })).toBeNull();

  fireEvent.click(info);
  expect(info.getAttribute("aria-expanded")).toBe("true");
  const menu = screen.getByRole("navigation", { name: "Site information" });
  within(menu).getByRole("link", { name: "Contact" }).focus();
  fireEvent.keyDown(document.activeElement!, { key: "Escape" });
  expect(info.getAttribute("aria-expanded")).toBe("false");
  expect(document.activeElement).toBe(info);

  fireEvent.click(info);
  fireEvent.pointerDown(document.body);
  expect(info.getAttribute("aria-expanded")).toBe("false");

  fireEvent.click(info);
  fireEvent.click(
    within(screen.getByRole("navigation", { name: "Site information" })).getByRole("link", {
      name: "About",
    }),
  );
  expect(location.pathname).toBe("/about");
  expect(screen.getByRole("heading", { level: 1, name: "About Marquise" })).toBeTruthy();
  expect(document.title).toBe("About · Marquise");
  expect(document.activeElement).toBe(screen.getByRole("main"));
  expect(screen.getByRole("button", { name: "Info" }).getAttribute("aria-expanded")).toBe("false");
  expect(
    within(screen.getByRole("navigation", { name: "Footer" }))
      .getByRole("link", { name: "About" })
      .getAttribute("aria-current"),
  ).toBe("page");

  fireEvent.click(screen.getByRole("button", { name: "Info" }));
  fireEvent.click(
    within(screen.getByRole("navigation", { name: "Site information" })).getByRole("link", {
      name: "About",
    }),
  );
  expect(location.pathname).toBe("/about");
  expect(screen.getByRole("button", { name: "Info" }).getAttribute("aria-expanded")).toBe("false");
});

it.each([
  ["/contact", "Contact"],
  ["/terms", "Terms of use"],
  ["/privacy", "Privacy"],
  ["/about/", "About Marquise"],
])("loads %s on direct entry without reading listings", async (path, heading) => {
  history.replaceState(null, "", path);
  const client = clients();
  render(<App client={client} />);
  expect(screen.getByRole("heading", { level: 1, name: heading })).toBeTruthy();
  expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeTruthy();
  expect(screen.getByRole("contentinfo")).toBeTruthy();
  await act(async () => {});
  for (const read of Object.values(client)) expect(read).not.toHaveBeenCalled();
});

it("shows the approved contact and information pages without draft labels", () => {
  history.replaceState(null, "", "/contact");
  const { unmount } = render(<App client={clients()} />);
  expect(
    screen.getByRole("link", { name: "me@arnaudjalbert.com" }).getAttribute("href"),
  ).toBe("mailto:me@arnaudjalbert.com");
  expect(screen.queryByRole("note")).toBeNull();
  expect(screen.getByText(/booking/i, { selector: "h2" })).toBeTruthy();
  unmount();

  history.replaceState(null, "", "/about");
  const about = render(<App client={clients()} />);
  expect(screen.queryByRole("note")).toBeNull();
  expect(screen.getByText(/not officially affiliated with Cineplex, TMDB/)).toBeTruthy();
  expect(screen.getByRole("main").textContent).not.toMatch(/public website|ticketing pages|API key/);
  expect(screen.getByText(/not endorsed, certified, or otherwise approved by TMDB/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "Cinemas page" }).getAttribute("href")).toBe("/cinemas");
  const logo = screen.getByRole("img", { name: "The Movie Database (TMDB)" });
  expect(logo.closest("a")?.getAttribute("href")).toBe("https://www.themoviedb.org");
  expect(logo.getAttribute("src")).not.toMatch(/^https?:/);
  about.unmount();

  for (const path of ["/terms", "/privacy"]) {
    history.replaceState(null, "", path);
    const policy = render(<App client={clients()} />);
    expect(screen.queryByRole("note")).toBeNull();
    expect(screen.getByText("Last updated November 1, 2026.")).toBeTruthy();
    expect(screen.queryByText(/Placeholder paragraph/)).toBeNull();
    policy.unmount();
  }
});

it("explains public API use without granting third-party content rights", () => {
  history.replaceState(null, "", "/terms");
  render(<App client={clients()} />);
  expect(screen.getByRole("heading", { name: "Public API" })).toBeTruthy();
  expect(screen.getByText(/intended for independent applications/)).toBeTruthy();
  expect(screen.getByText(/does not grant permission to reuse third-party material/)).toBeTruthy();
  expect(screen.getByText(/not officially affiliated with Cineplex, TMDB/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "source credits" }).getAttribute("href")).toBe("/about");
});

it("discloses server logs, editor records, forwarded email, and the privacy contact", () => {
  history.replaceState(null, "", "/privacy");
  render(<App client={clients()} />);
  expect(screen.getByText(/Routine web-server access logs are disabled/)).toBeTruthy();
  expect(screen.getByText(/separate request-completion log/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "published logging policy" }).getAttribute("href")).toBe("https://fly.io/legal/security-questionnaire/");
  expect(screen.getByText(/outside Québec/)).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Authorized editors" })).toBeTruthy();
  expect(screen.getByText(/personal Gmail inbox/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "Google's privacy policy" }).getAttribute("href")).toBe("https://policies.google.com/privacy");
  expect(screen.getByText(/Arnaud Jalbert is responsible/)).toBeTruthy();
  for (const contact of screen.getAllByRole("link", { name: "me@arnaudjalbert.com" })) {
    expect(contact.getAttribute("href")).toBe("mailto:me@arnaudjalbert.com");
  }
});

it("moves between information pages and listings with Back and Forward", async () => {
  history.replaceState(null, "", "/?section=movies");
  const client = clients();
  client.fetchScreeningMoviesPage.mockImplementation(
    async ({ page: requestedPage }) => ({
      items: [
        {
          ...movie,
          id: `movie-${requestedPage}`,
          title: `Movie ${requestedPage}`,
          screenings: [show],
        },
      ],
      total: 2,
      page: requestedPage,
      pages: 2,
      size: 24,
    }),
  );
  render(<App client={client} />);
  await screen.findByRole("link", { name: "View Movie 1" });
  const footer = () => within(screen.getByRole("navigation", { name: "Footer" }));
  fireEvent.click(footer().getByRole("link", { name: "About" }));
  fireEvent.click(footer().getByRole("link", { name: "Terms" }));
  expect(screen.getByRole("heading", { level: 1, name: "Terms of use" })).toBeTruthy();

  const traverse = async (url: string) =>
    act(async () => {
      history.replaceState(null, "", url);
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
  await traverse("/about");
  expect(screen.getByRole("heading", { level: 1, name: "About Marquise" })).toBeTruthy();
  await traverse("/?section=movies");
  await screen.findByRole("link", { name: "View Movie 1" });
  await reachEnd();
  await screen.findByRole("link", { name: "View Movie 2" });
  await traverse("/about");
  expect(screen.getByRole("heading", { level: 1, name: "About Marquise" })).toBeTruthy();
});

it.each(["/", "/?section=movies", "/cinemas", "/about"])(
  "skips to content on %s without changing the URL",
  async (path) => {
    history.replaceState(null, "", path);
    render(<App client={clients()} />);
    const before = location.href;
    fireEvent.click(screen.getByRole("link", { name: "Skip to content" }));
    expect(document.activeElement).toBe(screen.getByRole("main"));
    expect(location.href).toBe(before);
    await act(async () => {});
  },
);

it("preserves API instants through the repeated Montréal hour", async () => {
  /** Scenario: an earlier 01:45 is hidden while the second 01:45 remains bookable today. */
  vi.setSystemTime(new Date("2026-11-01T06:15:00Z"));
  const client = clients();
  client.fetchScreeningMoviesPage.mockResolvedValue(page([{
    ...movie,
    screenings: [
      { ...show, showtime: "2026-11-01T05:45:00Z", ticket_url: "https://tickets.example/started" },
      { ...show, id: "upcoming", showtime: "2026-11-01T06:45:00Z", ticket_url: "https://tickets.example/upcoming" },
    ],
  }]));
  render(<App client={client} />);
  fireEvent.click(await screen.findByRole("button", { name: `Preview ${movie.title}` }));
  const preview = within(screen.getByRole("region", { name: `${movie.title} screenings` }));
  expect(preview.getAllByRole("link", { name: "01:45" })).toHaveLength(1);
  expect(preview.getByRole("link", { name: "01:45" }).getAttribute("href")).toBe("https://tickets.example/upcoming");
  expect(preview.queryByText(/Tomorrow|In \d+ days/)).toBeNull();
});
