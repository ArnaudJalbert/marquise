import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  MinimalCatalogue,
  MinimalMovieCard,
  type MinimalCatalogueProps,
  type CatalogueMovie,
} from "./MinimalCatalogue";

afterEach(cleanup);
const cinemas = [
  { id: "a", name: "Cinema A" },
  { id: "b", name: "Cinema B" },
];
const movie: CatalogueMovie = {
  id: "film",
  title: "A title with its complete accessible name",
  screenings: [
    {
      cinemaId: "a",
      date: "2026-10-30",
      time: "18:00",
      language: "English",
      bookingUrl: "https://example.com",
    },
    { cinemaId: "b", date: "2026-10-30", time: "19:00", language: "French" },
    { cinemaId: "a", date: "2026-10-31", time: "20:00", language: "English" },
    { cinemaId: "b", date: "2026-11-01", time: "21:00", language: "French" },
  ],
};
const props: MinimalCatalogueProps = {
  movies: [movie],
  screeningLanguages: ["English", "French"],
  cinemas,
  selection: {
    start: "2026-10-30",
    end: "2026-11-01",
    title: "",
    cinemas: [],
    languages: [],
    from: "",
    to: "",
  },
  href: "/",
  today: "2026-10-30",
  tomorrow: "2026-10-31",
  weekend: ["2026-10-31", "2026-11-01"],
  onSelection: vi.fn(),
  navigate: vi.fn(),
  onRetry: vi.fn(),
};

describe("minimalist prototype", () => {
  it("opens only three screenings with the arrow, separate from movie navigation", () => {
    render(<MinimalMovieCard movie={movie} cinemas={cinemas} />);
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
    const arrow = screen.getByRole("button", {
      name: `Preview ${movie.title}`,
    });
    fireEvent.click(arrow);
    const preview = screen.getByRole("region", {
      name: `${movie.title} screenings`,
    });
    expect(within(preview).getAllByText(/Cinema [AB]/)).toHaveLength(2);
    expect(within(preview).getByText("2026-10-31")).toBeInTheDocument();
    expect(within(preview).queryByText("21:00")).not.toBeInTheDocument();
    expect(
      within(preview).getByRole("link", { name: "18:00" }),
    ).toHaveAttribute("target", "_blank");
    expect(
      within(preview).queryByRole("link", { name: "19:00" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: `View ${movie.title}` }),
    ).toHaveAttribute("href", "/movies/film");
    fireEvent.keyDown(arrow, { key: "Escape" });
    expect(arrow).toHaveFocus();
    expect(arrow).toHaveAttribute("aria-expanded", "false");
  });
  it("combines cinema, language and daily time on the same screening", () => {
    render(
      <MinimalCatalogue
        {...props}
        selection={{
          ...props.selection,
          cinemas: ["a"],
          languages: ["French"],
        }}
      />,
    );
    expect(screen.getByText("No matching movies")).toBeInTheDocument();
  });
  it("shows complete unfiltered detail and honest missing metadata", () => {
    render(
      <MinimalCatalogue
        {...props}
        href="/movies/film"
        selection={{ ...props.selection, title: "no match", end: "2026-10-30" }}
      />,
    );
    expect(screen.getByText("21:00")).toBeInTheDocument();
    expect(screen.getByText("Movie metadata unavailable")).toBeInTheDocument();
    expect(screen.getByText("Synopsis unavailable.")).toBeInTheDocument();
    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
  });
  it("fixes the cinema and omits its selector", () => {
    render(<MinimalCatalogue {...props} href="/cinemas/a" />);
    expect(
      screen.queryByRole("group", { name: "Cinemas" }),
    ).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: `Preview ${movie.title}` }),
    );
    const preview = screen.getByRole("region", {
      name: `${movie.title} screenings`,
    });
    expect(within(preview).queryByText("Cinema B")).not.toBeInTheDocument();
  });
  it("preserves cards and offers an explicit retry", () => {
    render(<MinimalCatalogue {...props} state="error" />);
    expect(
      screen.getByRole("link", { name: `View ${movie.title}` }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(props.onRetry).toHaveBeenCalledOnce();
  });
  it("reports invalid daily windows without displaying misleading results", () => {
    render(
      <MinimalCatalogue
        {...props}
        selection={{ ...props.selection, from: "22:00", to: "18:00" }}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Start must be before end",
    );
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
  });
});
