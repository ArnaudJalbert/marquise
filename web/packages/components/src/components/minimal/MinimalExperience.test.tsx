import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { BrowseClient, ScreeningMovieQuery } from "marquise-client";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MinimalExperience } from "./MinimalExperience";

const cinemaPage = {
  items: [
    { id: "a", name: "Cinema A", address: null, city: null, website: null },
    { id: "b", name: "Cinema B", address: null, city: null, website: null },
  ],
  total: 2,
  page: 1,
  size: 100,
  pages: 1,
};

function browseClient() {
  const client = {
    fetchCinemaPage: vi.fn(async () => cinemaPage),
    fetchScreeningMoviesPage: vi.fn(async () => ({
      items: [],
      total: 0,
      page: 1,
      size: 20,
      pages: 1,
    })),
    fetchMoviePage: vi.fn(),
    fetchMovieMetadata: vi.fn(),
    fetchScreeningRangePage: vi.fn(),
    fetchUpcomingScreeningsPage: vi.fn(),
  };
  return client satisfies BrowseClient;
}

describe("MinimalExperience fixed-cinema pages", () => {
  it.each([
    ["an excluded cinema", "-a", { cinemas: ["a"], excludedCinemas: [] }],
    ["an included cinema", "b", { cinemas: ["a"], excludedCinemas: [] }],
  ])(
    "ignores %s from the URL on a fixed-cinema page",
    async (_label, cinemaParam, expectedQuery) => {
      /** Scenario: a fixed cinema page queries only that cinema and shows no cinema chip from the URL. */
      const client = browseClient();
      render(
        <MinimalExperience
          client={client}
          href={`/cinemas/a?cinema=${cinemaParam}`}
          navigate={vi.fn()}
          currentTime="2026-10-30T16:00:00Z"
        />,
      );

      await waitFor(() =>
        expect(client.fetchScreeningMoviesPage).toHaveBeenCalled(),
      );
      expect(client.fetchScreeningMoviesPage).toHaveBeenLastCalledWith(
        expect.objectContaining(expectedQuery),
        expect.anything(),
      );
      expect(
        screen.queryByRole("group", { name: "cinema filter" }),
      ).not.toBeInTheDocument();
    },
  );
});

describe("MinimalExperience phone sheet", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("counts the movies matching the sheet's draft before it is applied", async () => {
    /** Scenario: "Show N movies" reads the total for the draft selection, without navigating. */
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: true,
      media: query,
      addEventListener() {},
      removeEventListener() {},
    }));
    const client = {
      ...browseClient(),
      fetchScreeningMoviesPage: vi.fn(async (query: ScreeningMovieQuery) => ({
        items: [],
        total: query.excludedCinemas?.length ? 2 : 7,
        page: 1,
        size: 20,
        pages: 1,
      })),
    };
    const navigate = vi.fn();
    render(
      <MinimalExperience
        client={client}
        href="/?cinema=-a"
        navigate={navigate}
        currentTime="2026-10-30T16:00:00Z"
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Filters (1 active)" }));
    const sheet = screen.getByRole("dialog", { name: "Dates and filters" });
    expect(await within(sheet).findByRole("button", { name: "Show 2 movies" })).toBeInTheDocument();

    fireEvent.click(within(sheet).getByRole("button", { name: "Remove cinema filter" }));
    expect(await within(sheet).findByRole("button", { name: "Show 7 movies" })).toBeInTheDocument();
    expect(client.fetchScreeningMoviesPage).toHaveBeenLastCalledWith(
      expect.objectContaining({ start: "2026-10-30", end: "2026-10-30", excludedCinemas: [] }),
      expect.any(AbortSignal),
    );
    expect(navigate).not.toHaveBeenCalled();
  });
});
