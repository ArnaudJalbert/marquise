import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  MovieNotFoundError,
  type DiscoveryClient,
  type MovieDetailClient,
  type ScreeningPage,
} from "marquise-client";
import { App } from "./App";

const DATE = "2026-08-08";
const NOW = "2026-08-09T01:00:00Z"; // Still August 8 in Montréal.
function screeningPage(page = 1): ScreeningPage {
  return {
    page,
    pages: 3,
    size: 48,
    total: 100,
    screeningCount: 2,
    items: [1, 2].map((index) => ({
      key: `movie-${page}-${index}`,
      movie: {
        id: `movie-${page}-${index}`,
        title: `Movie ${page}.${index}`,
        genres: ["Drama"],
      },
      showtimesUrl: `/movies/movie-${page}-${index}`,
      showtimes: [
        {
          startsAt: `${DATE}T23:00:00-04:00`,
          ticketUrl: "https://tickets.example/seat",
          language: "VOSTF",
          cinema: { id: "cinema-1", name: "Cinema One", link: null },
        },
      ],
    })),
  };
}
function createClients() {
  const client = {
    fetchScreeningPage: vi.fn<DiscoveryClient["fetchScreeningPage"]>(
      async (query) => screeningPage(query.page),
    ),
    fetchCinemaPage: vi.fn<DiscoveryClient["fetchCinemaPage"]>(
      async (page, _signal, name) => ({
        page,
        pages: 2,
        size: 100,
        total: 101,
        items:
          name === "missing"
            ? []
            : [
                {
                  id: "cinema-1",
                  name: "Cinema One",
                  address: "123 Example Street",
                  city: "Montréal",
                  website: "https://cinema.example",
                },
              ],
      }),
    ),
    fetchShowtimePage: vi.fn<DiscoveryClient["fetchShowtimePage"]>(
      async (_id, _date, page) => ({
        page,
        pages: 2,
        total: 50,
        size: 48,
        items: [...(screeningPage().items[0]?.showtimes ?? [])],
      }),
    ),
  };
  const detail = {
    fetchMovie: vi.fn<MovieDetailClient["fetchMovie"]>(async (id) => {
      if (id === "missing") throw new MovieNotFoundError(id);
      return {
        id,
        title: "A Real Movie",
        directors: ["A Director"],
        durationMinutes: 100,
      };
    }),
    listDates: vi.fn(async () => [DATE]),
    fetchShowtimes: vi.fn(async () => []),
  };
  return { client, detail };
}
function visit(href: string) {
  act(() => {
    history.replaceState(null, "", href);
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
}
beforeEach(() => {
  history.replaceState(null, "", "/");
  vi.setSystemTime(new Date(NOW));
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: true })),
  );
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
  document.title = "";
});

describe("Marquise discovery and daily screenings", () => {
  it("shows page categories on landing and defaults to today in Montréal", async () => {
    const { client, detail } = createClients();
    render(<App discoveryClient={client} movieDetailClient={detail} />);
    await screen.findByRole("heading", { name: "Drama, anyone?" });
    expect(
      screen.getByRole("heading", { name: /Less scrolling/ }),
    ).not.toBeNull();
    expect(screen.getByText("On this page")).not.toBeNull();
    expect(client.fetchScreeningPage).toHaveBeenCalledExactlyOnceWith(
      expect.objectContaining({ date: DATE, page: 1 }),
      expect.any(AbortSignal),
    );
    expect(screen.queryByText(/Demo mode/)).toBeNull();
  });
  it("preserves legacy dated cinema links and selected IDs absent from the cinema page", async () => {
    history.replaceState(
      null,
      "",
      `/?date=${DATE}&cinema=outside-page&language=VOF&from=18&to=24`,
    );
    const { client, detail } = createClients();
    render(<App discoveryClient={client} movieDetailClient={detail} />);
    await screen.findByRole("link", { name: "View Movie 1.1" });
    expect(client.fetchScreeningPage).toHaveBeenCalledWith(
      expect.objectContaining({
        date: DATE,
        cinemaId: "outside-page",
        language: "VOF",
        fromTime: "18:00",
        toTime: "23:59",
      }),
      expect.any(AbortSignal),
    );
    expect((screen.getByLabelText("Cinema") as HTMLSelectElement).value).toBe(
      "outside-page",
    );
    expect(document.title).toBe("Daily screenings · Marquise");
  });
  it("applies server filters, pages only on request, and restores filters with browser history", async () => {
    history.replaceState(null, "", "/screenings");
    const { client, detail } = createClients();
    render(<App discoveryClient={client} movieDetailClient={detail} />);
    await screen.findByRole("link", { name: "View Movie 1.1" });
    expect(client.fetchScreeningPage).toHaveBeenCalledTimes(1);
    fireEvent.change(screen.getByLabelText("Find a film"), {
      target: { value: "A & B" },
    });
    fireEvent.change(screen.getByLabelText("Cinema"), {
      target: { value: "cinema-1" },
    });
    fireEvent.change(screen.getByLabelText("Language code"), {
      target: { value: "VOSTF" },
    });
    fireEvent.change(screen.getByLabelText("From"), {
      target: { value: "18:00" },
    });
    fireEvent.change(screen.getByLabelText("Until"), {
      target: { value: "23:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Find screenings →" }));
    await waitFor(() =>
      expect(client.fetchScreeningPage).toHaveBeenLastCalledWith(
        expect.objectContaining({
          movie: "A & B",
          cinemaId: "cinema-1",
          language: "VOSTF",
          fromTime: "18:00",
          toTime: "23:00",
          page: 1,
        }),
        expect.any(AbortSignal),
      ),
    );
    const filtered = window.location.href;
    await screen.findByRole("link", { name: "View Movie 1.1" });
    fireEvent.click(screen.getByRole("button", { name: "Next →" }));
    await screen.findByRole("link", { name: "View Movie 2.1" });
    expect(client.fetchScreeningPage).toHaveBeenCalledTimes(3);
    expect(screen.getByText("Page 2 of 3 · 100 screenings")).not.toBeNull();
    expect(
      screen.getByText(`2 screenings on this page · 2 films · ${DATE}`),
    ).not.toBeNull();
    act(() => history.back());
    await waitFor(() => expect(window.location.href).toBe(filtered));
    await screen.findByRole("link", { name: "View Movie 1.1" });
    expect(
      (screen.getByLabelText("Find a film") as HTMLInputElement).value,
    ).toBe("A & B");
    act(() => history.forward());
    await screen.findByRole("link", { name: "View Movie 2.1" });
    expect((screen.getByLabelText("Cinema") as HTMLSelectElement).value).toBe(
      "cinema-1",
    );
  });
  it("validates reversed time ranges in links and submissions without a screening request", async () => {
    history.replaceState(
      null,
      "",
      `/screenings?date=${DATE}&from=22:00&to=18:00`,
    );
    const { client, detail } = createClients();
    render(<App discoveryClient={client} movieDetailClient={detail} />);
    expect(await screen.findByText(/Choose an Until time/)).not.toBeNull();
    expect(client.fetchScreeningPage).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Find screenings →" }));
    expect(client.fetchScreeningPage).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Until"), {
      target: { value: "23:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Find screenings →" }));
    await screen.findByRole("link", { name: "View Movie 1.1" });
    expect(screen.queryByRole("alert")).toBeNull();
  });
  it("validates skipped DST clock times before fetching screenings", async () => {
    history.replaceState(null, "", "/screenings?date=2027-03-14&from=02:30");
    const { client, detail } = createClients();
    render(<App discoveryClient={client} movieDetailClient={detail} />);
    expect(
      await screen.findByText(/This time does not exist in Montréal/),
    ).not.toBeNull();
    expect(client.fetchScreeningPage).not.toHaveBeenCalled();
  });

  it("leaves skip links native without remounting or refetching results", async () => {
    const { client, detail } = createClients();
    render(<App discoveryClient={client} movieDetailClient={detail} />);
    await screen.findByRole("heading", { name: "Playing around town" });
    const push = vi.spyOn(history, "pushState");
    const click = new MouseEvent("click", { bubbles: true, cancelable: true });
    let nativeLink = false;
    document.addEventListener(
      "click",
      (event) => {
        nativeLink = !event.defaultPrevented;
        event.preventDefault(); // Avoid jsdom's deferred native navigation after this test.
      },
      { once: true },
    );
    fireEvent(screen.getByRole("link", { name: "Skip to content" }), click);
    expect(nativeLink).toBe(true);
    expect(push).not.toHaveBeenCalled();
    expect(client.fetchScreeningPage).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("main").getAttribute("tabindex")).toBe("-1");
  });
  it("aborts old queries and ignores late responses after a query or client change", async () => {
    history.replaceState(null, "", `/screenings?date=${DATE}`);
    const { client, detail } = createClients();
    let resolveOld!: (value: ScreeningPage) => void;
    client.fetchScreeningPage.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve;
        }),
    );
    const view = render(
      <App discoveryClient={client} movieDetailClient={detail} />,
    );
    const oldSignal = client.fetchScreeningPage.mock.calls[0]?.[1];
    visit(`/screenings?date=${DATE}&page=2`);
    await screen.findByRole("link", { name: "View Movie 2.1" });
    expect(oldSignal?.aborted).toBe(true);
    await act(async () => resolveOld(screeningPage(1)));
    expect(screen.queryByRole("link", { name: "View Movie 1.1" })).toBeNull();
    const replacement = createClients().client;
    replacement.fetchScreeningPage.mockResolvedValue(screeningPage(3));
    view.rerender(
      <App discoveryClient={replacement} movieDetailClient={detail} />,
    );
    expect(screen.queryByRole("link", { name: "View Movie 2.1" })).toBeNull();
    await screen.findByRole("link", { name: "View Movie 3.1" });
    expect(replacement.fetchScreeningPage).toHaveBeenCalledTimes(1);
  });
  it("shows request errors, retries, and handles an empty page", async () => {
    history.replaceState(null, "", "/screenings");
    const { client, detail } = createClients();
    client.fetchScreeningPage.mockRejectedValueOnce(new Error("offline"));
    client.fetchScreeningPage.mockResolvedValue({
      ...screeningPage(),
      items: [],
      total: 0,
      pages: 0,
      screeningCount: 0,
    });
    render(<App discoveryClient={client} movieDetailClient={detail} />);
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await screen.findByRole("heading", {
      name: "No screenings in this frame.",
    });
    expect(client.fetchScreeningPage).toHaveBeenCalledTimes(2);
    expect(
      (screen.getByRole("button", { name: "Next →" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });
});

describe("Cinema directory and film routes", () => {
  it("searches cinemas on the server, pages the directory, and prefills screenings", async () => {
    history.replaceState(null, "", "/cinemas");
    const { client, detail } = createClients();
    render(<App discoveryClient={client} movieDetailClient={detail} />);
    await screen.findByRole("heading", { name: "Cinema One" });
    expect(document.title).toBe("Cinemas · Marquise");
    expect(screen.getByText("123 Example Street, Montréal")).not.toBeNull();
    expect(
      screen
        .getByRole("link", { name: "Cinema website ↗" })
        .getAttribute("href"),
    ).toBe("https://cinema.example");
    fireEvent.change(screen.getByLabelText("Find a cinema"), {
      target: { value: "Cinema" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Find cinemas →" }));
    await waitFor(() =>
      expect(client.fetchCinemaPage).toHaveBeenLastCalledWith(
        1,
        expect.any(AbortSignal),
        "Cinema",
      ),
    );
    await screen.findByRole("heading", { name: "Cinema One" });
    fireEvent.click(screen.getByRole("button", { name: "Next →" }));
    await waitFor(() =>
      expect(client.fetchCinemaPage).toHaveBeenLastCalledWith(
        2,
        expect.any(AbortSignal),
        "Cinema",
      ),
    );
    await screen.findByRole("heading", { name: "Cinema One" });
    fireEvent.click(screen.getByRole("link", { name: "See screenings →" }));
    await screen.findByRole("link", { name: "View Movie 1.1" });
    expect((screen.getByLabelText("Cinema") as HTMLSelectElement).value).toBe(
      "cinema-1",
    );
    expect(client.fetchScreeningPage).toHaveBeenCalledWith(
      expect.objectContaining({ cinemaId: "cinema-1", date: DATE }),
      expect.any(AbortSignal),
    );
  });
  it("handles directory failure, retry and empty search results", async () => {
    history.replaceState(null, "", "/cinemas?name=missing");
    const { client, detail } = createClients();
    client.fetchCinemaPage.mockRejectedValueOnce(new Error("offline"));
    render(<App discoveryClient={client} movieDetailClient={detail} />);
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await screen.findByRole("heading", { name: "No cinemas found." });
    expect(client.fetchCinemaPage).toHaveBeenCalledTimes(2);
  });
  it("loads direct film links, uses the real title, pages showtimes and changes dates", async () => {
    history.replaceState(null, "", `/movies/film-id?date=${DATE}`);
    const { client, detail } = createClients();
    render(<App discoveryClient={client} movieDetailClient={detail} />);
    await screen.findByRole("heading", { name: "A Real Movie" });
    await waitFor(() => expect(document.title).toBe("A Real Movie — Marquise"));
    expect(detail.fetchMovie).toHaveBeenCalledExactlyOnceWith("film-id");
    expect(client.fetchShowtimePage).toHaveBeenCalledExactlyOnceWith(
      "film-id",
      DATE,
      1,
      expect.any(AbortSignal),
    );
    fireEvent.click(screen.getByRole("button", { name: "Next →" }));
    await waitFor(() =>
      expect(client.fetchShowtimePage).toHaveBeenLastCalledWith(
        "film-id",
        DATE,
        2,
        expect.any(AbortSignal),
      ),
    );
    fireEvent.change(screen.getByLabelText("Screening date"), {
      target: { value: "2026-08-09" },
    });
    await waitFor(() =>
      expect(client.fetchShowtimePage).toHaveBeenLastCalledWith(
        "film-id",
        "2026-08-09",
        1,
        expect.any(AbortSignal),
      ),
    );
    expect(detail.fetchMovie).toHaveBeenCalledTimes(1);
  });
  it("distinguishes missing films from failures and retries transient errors", async () => {
    history.replaceState(null, "", `/movies/missing?date=${DATE}`);
    const { client, detail } = createClients();
    render(<App discoveryClient={client} movieDetailClient={detail} />);
    await screen.findByRole("heading", { name: "Movie not found." });
    await waitFor(() =>
      expect(document.title).toBe("Movie not found — Marquise"),
    );
    detail.fetchMovie.mockRejectedValueOnce(new Error("offline"));
    visit(`/movies/film-id?date=${DATE}`);
    await screen.findByRole("alert");
    expect(screen.queryByText("Movie not found.")).toBeNull();
    await waitFor(() =>
      expect(document.title).toBe("Movie unavailable — Marquise"),
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await screen.findByRole("heading", { name: "A Real Movie" });
  });
  it("ignores a late film response and refreshes metadata when the detail client changes", async () => {
    history.replaceState(null, "", `/movies/old-film?date=${DATE}`);
    const { client, detail } = createClients();
    let resolveOld!: (movie: { id: string; title: string }) => void;
    detail.fetchMovie.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve;
        }),
    );
    const view = render(
      <App discoveryClient={client} movieDetailClient={detail} />,
    );
    visit(`/movies/new-film?date=${DATE}`);
    await screen.findByRole("heading", { name: "A Real Movie" });
    await act(async () => resolveOld({ id: "old-film", title: "Old film" }));
    expect(screen.queryByRole("heading", { name: "Old film" })).toBeNull();
    const replacement = createClients().detail;
    replacement.fetchMovie.mockResolvedValue({
      id: "new-film",
      title: "Fresh metadata",
    });
    view.rerender(
      <App discoveryClient={client} movieDetailClient={replacement} />,
    );
    expect(screen.queryByRole("heading", { name: "A Real Movie" })).toBeNull();
    await screen.findByRole("heading", { name: "Fresh metadata" });
    await waitFor(() =>
      expect(document.title).toBe("Fresh metadata — Marquise"),
    );
  });
  it("retries film screenings without reloading metadata and handles an empty date", async () => {
    history.replaceState(null, "", `/movies/film-id?date=${DATE}`);
    const { client, detail } = createClients();
    client.fetchShowtimePage.mockRejectedValueOnce(new Error("offline"));
    client.fetchShowtimePage.mockResolvedValue({
      items: [],
      page: 1,
      pages: 0,
      size: 48,
      total: 0,
    });
    render(<App discoveryClient={client} movieDetailClient={detail} />);
    await screen.findByRole("heading", { name: "A Real Movie" });
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await screen.findByText("No screenings for this date. Try another day.");
    expect(detail.fetchMovie).toHaveBeenCalledTimes(1);
    expect(client.fetchShowtimePage).toHaveBeenCalledTimes(2);
  });
  it("makes preview tickets and details reachable from hover and explicit touch/keyboard controls", async () => {
    history.replaceState(null, "", "/screenings");
    const { client, detail } = createClients();
    render(<App discoveryClient={client} movieDetailClient={detail} />);
    const link = await screen.findByRole("link", { name: "View Movie 1.1" });
    fireEvent.pointerEnter(link, { pointerType: "mouse" });
    let dialog = await screen.findByRole("dialog", {
      name: "Showtimes for Movie 1.1",
    });
    expect(
      within(dialog)
        .getByRole("link", { name: "23:00" })
        .getAttribute("target"),
    ).toBe("_blank");
    expect(within(dialog).getByText("VOSTF")).not.toBeNull();
    expect(dialog.closest(".daily-poster-grid")).toBeNull();
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Close preview" }),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    const trigger = screen.getByRole("button", {
      name: "Showtimes for Movie 1.1",
    });
    fireEvent.pointerDown(trigger, { pointerType: "touch" });
    fireEvent.click(trigger);
    dialog = await screen.findByRole("dialog");
    fireEvent.keyDown(dialog, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    trigger.focus();
    fireEvent.keyDown(trigger, { key: "Enter" });
    fireEvent.click(trigger); // Native Enter activates a button in the browser.
    dialog = await screen.findByRole("dialog");
    fireEvent.click(
      within(dialog).getByRole("link", {
        name: "Movie details & all screening pages →",
      }),
    );
    await screen.findByRole("heading", { name: "A Real Movie" });
    expect(window.location.pathname).toBe("/movies/movie-1-1");
    expect(window.location.search).toBe(`?date=${DATE}`);
  });
});
