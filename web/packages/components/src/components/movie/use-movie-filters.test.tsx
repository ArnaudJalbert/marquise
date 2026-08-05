import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Cinema } from "./cinema";
import type { CinemaShowtime } from "./cinema";
import type { MovieCardGridItem } from "./movie-card-grid";
import type { MovieGridClient } from "./movie-grid-client";
import { useMovieFilters } from "./use-movie-filters";

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

interface ClientOverrides {
  dates?: string[];
  byDate?: Record<string, MovieCardGridItem[]>;
}

function createClient(overrides?: ClientOverrides) {
  const dates = overrides?.dates ?? ["2026-08-03", "2026-08-04"];
  const byDate = overrides?.byDate ?? {
    "2026-08-03": dayOne,
    "2026-08-04": dayTwo,
  };
  return {
    listDates: vi.fn(async (): Promise<string[]> => dates),
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

describe("useMovieFilters", () => {
  it("loads the dates and fetches the first date on mount", async () => {
    const client = createClient();
    const { result } = renderHook(() => useMovieFilters(client));

    await waitFor(() => expect(client.fetchForDate).toHaveBeenCalledTimes(1));

    expect(client.listDates).toHaveBeenCalledTimes(1);
    expect(result.current.dates).toEqual(["2026-08-03", "2026-08-04"]);
    expect(result.current.selectedDate).toBe("2026-08-03");
    expect(client.fetchForDate).toHaveBeenCalledWith("2026-08-03");
    expect(result.current.items.map((entry) => entry.key)).toEqual([
      "dune",
      "anora",
    ]);
  });

  it("fetches the initialDate when provided", async () => {
    const client = createClient();
    renderHook(() => useMovieFilters(client, "2026-08-04"));

    await waitFor(() =>
      expect(client.fetchForDate).toHaveBeenCalledWith("2026-08-04"),
    );
  });

  it("selecting a different date triggers exactly one additional fetch", async () => {
    const client = createClient();
    const { result } = renderHook(() => useMovieFilters(client));

    await waitFor(() => expect(client.fetchForDate).toHaveBeenCalledTimes(1));

    act(() => result.current.selectDate("2026-08-04"));

    await waitFor(() => expect(client.fetchForDate).toHaveBeenCalledTimes(2));
    expect(client.fetchForDate).toHaveBeenLastCalledWith("2026-08-04");
    await waitFor(() =>
      expect(result.current.items.map((entry) => entry.key)).toEqual(["dune"]),
    );
  });

  it("does not refetch when the same date is selected again", async () => {
    const client = createClient();
    const { result } = renderHook(() => useMovieFilters(client));

    await waitFor(() => expect(client.fetchForDate).toHaveBeenCalledTimes(1));

    act(() => result.current.selectDate("2026-08-03"));

    await waitFor(() => expect(result.current.selectedDate).toBe("2026-08-03"));
    expect(client.fetchForDate).toHaveBeenCalledTimes(1);
  });

  it("never fetches when local filters are updated", async () => {
    const client = createClient();
    const { result } = renderHook(() => useMovieFilters(client));

    await waitFor(() => expect(client.fetchForDate).toHaveBeenCalledTimes(1));

    act(() => result.current.updateFilters({ genres: ["Sci-Fi"] }));
    act(() => result.current.updateFilters({ cinemas: ["Cinéma A"] }));
    act(() => result.current.updateFilters({ languages: ["VOSTF"] }));
    act(() => result.current.updateFilters({ timeRange: [18, 20] }));

    expect(client.fetchForDate).toHaveBeenCalledTimes(1);
  });

  it("applies local filters to the fetched items", async () => {
    const client = createClient();
    const { result } = renderHook(() => useMovieFilters(client));

    await waitFor(() => expect(client.fetchForDate).toHaveBeenCalledTimes(1));

    act(() => result.current.updateFilters({ genres: ["Comedy"] }));

    expect(result.current.items.map((entry) => entry.key)).toEqual(["anora"]);
  });

  it("prunes showtimes that fall outside the local time range", async () => {
    const client = createClient();
    const { result } = renderHook(() => useMovieFilters(client));

    await waitFor(() => expect(client.fetchForDate).toHaveBeenCalledTimes(1));

    act(() => result.current.updateFilters({ timeRange: [21, 24] }));

    expect(result.current.items).toHaveLength(0);
  });

  it("derives the filter options from the selected date's items", async () => {
    const client = createClient();
    const { result } = renderHook(() => useMovieFilters(client));

    await waitFor(() => expect(client.fetchForDate).toHaveBeenCalledTimes(1));

    expect(result.current.options.cinemas).toEqual(["Cinéma A", "Cinéma B"]);
    expect(result.current.options.genres).toEqual(["Comedy", "Sci-Fi"]);
    expect(result.current.options.languages).toEqual(["VF", "VOSTF"]);
  });

  it("prunes selections that no longer exist on the newly selected date", async () => {
    const client = createClient();
    const { result } = renderHook(() => useMovieFilters(client));

    await waitFor(() => expect(client.fetchForDate).toHaveBeenCalledTimes(1));

    act(() => result.current.updateFilters({ cinemas: ["Cinéma B"] }));
    act(() => result.current.selectDate("2026-08-04"));

    await waitFor(() => expect(result.current.filters.cinemas).toEqual([]));
    expect(result.current.items.map((entry) => entry.key)).toEqual(["dune"]);
  });

  it("is loading while a fetch is pending", async () => {
    const pending = deferred<MovieCardGridItem[]>();
    const client: MovieGridClient = {
      listDates: vi.fn(async () => ["2026-08-03"]),
      fetchForDate: vi.fn(() => pending.promise),
    };
    const { result } = renderHook(() => useMovieFilters(client));

    await waitFor(() => expect(result.current.isLoading).toBe(true));

    act(() => {
      pending.resolve(dayOne);
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.items).toHaveLength(2);
  });

  it("is loading the dates before the first date resolves", async () => {
    const pendingDates = deferred<string[]>();
    const client: MovieGridClient = {
      listDates: vi.fn(() => pendingDates.promise),
      fetchForDate: vi.fn(async () => dayOne),
    };
    const { result } = renderHook(() => useMovieFilters(client));

    expect(result.current.datesLoading).toBe(true);

    act(() => {
      pendingDates.resolve(["2026-08-03"]);
    });

    await waitFor(() => expect(result.current.datesLoading).toBe(false));
    expect(result.current.selectedDate).toBe("2026-08-03");
  });

  it("ignores out-of-order responses from a previously selected date", async () => {
    const pendingA = deferred<MovieCardGridItem[]>();
    const pendingB = deferred<MovieCardGridItem[]>();
    const client: MovieGridClient = {
      listDates: vi.fn(async () => ["2026-08-03", "2026-08-04"]),
      fetchForDate: vi.fn((date: string) =>
        date === "2026-08-03" ? pendingA.promise : pendingB.promise,
      ),
    };
    const { result } = renderHook(() => useMovieFilters(client));

    await waitFor(() =>
      expect(client.fetchForDate).toHaveBeenCalledWith("2026-08-03"),
    );

    act(() => result.current.selectDate("2026-08-04"));
    await waitFor(() =>
      expect(client.fetchForDate).toHaveBeenCalledWith("2026-08-04"),
    );

    act(() => {
      pendingB.resolve(dayTwo);
    });
    await waitFor(() =>
      expect(result.current.items.map((entry) => entry.key)).toEqual(["dune"]),
    );

    act(() => {
      pendingA.resolve(dayOne);
    });

    expect(result.current.items.map((entry) => entry.key)).toEqual(["dune"]);
    expect(result.current.isLoading).toBe(false);
  });

  it("surfaces an error when the dates cannot be loaded", async () => {
    const client: MovieGridClient = {
      listDates: vi.fn(async () => {
        throw new Error("network");
      }),
      fetchForDate: vi.fn(async () => dayOne),
    };
    const { result } = renderHook(() => useMovieFilters(client));

    await waitFor(() =>
      expect(result.current.error).toBe("Could not load the available dates."),
    );
    expect(result.current.datesLoading).toBe(false);
  });

  it("surfaces an error when a date's showtimes fail and retries the fetch", async () => {
    let reject = true;
    const client: MovieGridClient = {
      listDates: vi.fn(async () => ["2026-08-03"]),
      fetchForDate: vi.fn(async () => {
        if (reject) {
          throw new Error("network");
        }
        return dayOne;
      }),
    };
    const { result } = renderHook(() => useMovieFilters(client));

    await waitFor(() =>
      expect(result.current.error).toBe("Could not load showtimes for this date."),
    );
    expect(result.current.isLoading).toBe(false);

    reject = false;
    act(() => result.current.retry());

    await waitFor(() => expect(result.current.error).toBeNull());
    await waitFor(() => expect(result.current.items).toHaveLength(2));
  });

  it("ignores selecting a date that is not among the available dates", async () => {
    const client = createClient();
    const { result } = renderHook(() => useMovieFilters(client));

    await waitFor(() => expect(client.fetchForDate).toHaveBeenCalledTimes(1));

    act(() => result.current.selectDate("2026-08-99"));

    await waitFor(() => expect(client.fetchForDate).toHaveBeenCalledTimes(1));
    expect(result.current.selectedDate).toBe("2026-08-03");
  });
});
