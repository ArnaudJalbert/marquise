import { render, screen, waitFor } from "@testing-library/react";
import type { BrowseClient } from "marquise-client";
import { describe, expect, it, vi } from "vitest";
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
    fetchScreeningDayCounts: vi.fn(async () => []),
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
