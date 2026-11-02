import {
  act,
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

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
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
      language: "VO",
      bookingUrl: "https://example.com",
    },
    { cinemaId: "b", date: "2026-10-30", time: "19:00", language: "VOSTF" },
    { cinemaId: "a", date: "2026-10-31", time: "20:00", language: "VO" },
    { cinemaId: "b", date: "2026-11-01", time: "21:00", language: "VOSTF" },
  ],
};
const props: MinimalCatalogueProps = {
  movies: [movie],
  screeningLanguages: ["VO", "VOSTF"],
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
  it("keeps inclusive date shortcuts selected from URL-backed dates", () => {
    const onSelection = vi.fn();
    const { rerender } = render(
      <MinimalCatalogue {...props} onSelection={onSelection} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Today" }));
    expect(onSelection).toHaveBeenLastCalledWith(
      expect.objectContaining({ start: "2026-10-30", end: "2026-10-30" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Tomorrow" }));
    expect(onSelection).toHaveBeenLastCalledWith(
      expect.objectContaining({ start: "2026-10-31", end: "2026-10-31" }),
    );
    rerender(
      <MinimalCatalogue
        {...props}
        onSelection={onSelection}
        selection={{ ...props.selection, start: "2026-10-31", end: "2026-11-01" }}
      />,
    );
    expect(screen.getByRole("button", { name: "This weekend" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

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
          languages: ["VOSTF"],
        }}
      />,
    );
    expect(screen.getByText("No matching screenings")).toBeInTheDocument();
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

it("keeps every section available from the cinema directory", () => {
  render(<MinimalCatalogue {...props} href="/cinemas" />);
  const navigation = within(screen.getByRole("navigation", { name: "Main navigation" }));
  expect(
    navigation.getByRole("link", { name: "Screenings" }),
  ).toBeInTheDocument();
  expect(navigation.getByRole("link", { name: "Cinemas" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  fireEvent.click(navigation.getByRole("link", { name: "Movies" }));
  expect(props.navigate).toHaveBeenCalledWith("/?section=movies");
});

it("keeps date-independent catalogue results separate from screening results", () => {
  const laterMovie = {
    ...movie,
    id: "later",
    title: "A future film",
    screenings: [],
  };
  const { rerender } = render(
    <MinimalCatalogue
      {...props}
      catalogueMovies={[laterMovie]}
      href="/?section=movies"
    />,
  );
  expect(
    screen.getByRole("link", { name: "View A future film" }),
  ).toBeInTheDocument();
  expect(screen.queryByLabelText("Start date")).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "unmatched" },
  });
  expect(screen.getByText("No movies found.")).toBeInTheDocument();
  rerender(<MinimalCatalogue {...props} catalogueMovies={[laterMovie]} />);
  expect(
    screen.getByRole("link", { name: `View ${movie.title}` }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "View A future film" }),
  ).not.toBeInTheDocument();
});

it("moves through the loaded screening dates", async () => {
  const loadWeek = vi
    .fn()
    .mockResolvedValue({ screenings: movie.screenings, cinemas });
  render(
    <MinimalCatalogue {...props} href="/movies/film" onLoadWeek={loadWeek} />,
  );
  await screen.findByText("18:00");
  expect(loadWeek).toHaveBeenCalledExactlyOnceWith(
    movie,
    "2026-09-30",
    "2027-01-28",
    expect.any(AbortSignal),
  );
  fireEvent.click(screen.getByRole("button", { name: "Next dates" }));
  expect(screen.getByText("20:00")).toBeInTheDocument();
  expect(screen.getByText("21:00")).toBeInTheDocument();
  expect(screen.queryByText("18:00")).not.toBeInTheDocument();
  expect(loadWeek).toHaveBeenCalledOnce();
  const options = within(
    screen.getByRole("combobox", { name: "Days to show" }),
  ).getAllByRole("option");
  expect(options.map((option) => option.textContent)).toEqual([
    "1",
    "2",
    "3",
    "4",
  ]);
});

it("keeps the date columns when grouping the schedule by cinema", async () => {
  const loadWeek = vi
    .fn()
    .mockResolvedValue({ screenings: movie.screenings, cinemas });
  render(
    <MinimalCatalogue {...props} href="/movies/film" onLoadWeek={loadWeek} />,
  );
  await screen.findByText("18:00");
  fireEvent.change(screen.getByRole("combobox", { name: "Group schedule by" }), {
    target: { value: "cinema" },
  });
  const table = screen.getByRole("table");
  expect(within(table).getAllByRole("columnheader")).toHaveLength(4);
  expect(within(table).getByRole("row", { name: /Cinema A/ })).toBeInTheDocument();
  expect(within(table).getByRole("row", { name: /Cinema B/ })).toBeInTheDocument();
  expect(within(table).queryByText("—")).not.toBeInTheDocument();
});

it("ignores a previous movie's response after navigating to another movie", async () => {
  const pending: {
    finish: (value: {
      screenings: typeof movie.screenings;
      cinemas: typeof cinemas;
    }) => void;
    signal: AbortSignal;
  }[] = [];
  const loadWeek = vi.fn().mockImplementation(
    (
      _movie: typeof movie,
      _start: string,
      _end: string,
      signal: AbortSignal,
    ) =>
      new Promise((resolve) => {
        pending.push({ finish: resolve, signal });
      }),
  );
  const secondMovie = {
    ...movie,
    id: "second",
    title: "Second film",
    screenings: [{ cinemaId: "b", date: "2026-10-30", time: "12:15" }],
  };
  const common = {
    ...props,
    movies: [movie, secondMovie],
    onLoadWeek: loadWeek,
  };
  const { rerender } = render(
    <MinimalCatalogue {...common} href="/movies/film" />,
  );
  expect(loadWeek).toHaveBeenCalledOnce();
  rerender(<MinimalCatalogue {...common} href="/movies/second" />);
  expect(pending[0]!.signal.aborted).toBe(true);
  await act(async () => {
    pending[0]!.finish({ screenings: movie.screenings, cinemas });
    pending[1]!.finish({ screenings: secondMovie.screenings, cinemas });
  });
  expect(screen.getByText("12:15")).toBeInTheDocument();
  expect(screen.queryByText("18:00")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Retry showtimes" }),
  ).not.toBeInTheDocument();
  expect(loadWeek.mock.calls[0]![3].aborted).toBe(true);
});

it("loads the initial schedule for an API catalogue movie and permits retry", async () => {
  const apiMovie = { ...movie, screenings: [] };
  const loadWeek = vi
    .fn()
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValue({ screenings: movie.screenings, cinemas });
  render(
    <MinimalCatalogue
      {...props}
      catalogueMovies={[apiMovie]}
      href="/movies/film"
      onLoadWeek={loadWeek}
    />,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Retry showtimes" }),
  );
  expect(await screen.findByText("18:00")).toBeInTheDocument();
  expect(loadWeek).toHaveBeenCalledTimes(2);
});

it("keeps both time handles on the midnight-to-midnight scale and prevents crossing", () => {
  render(
    <MinimalCatalogue
      {...props}
      selection={{ ...props.selection, from: "18:30", to: "22:45" }}
    />,
  );
  fireEvent.click(screen.getByText(/^Filters/));
  const start = screen.getByRole("slider", { name: "Start time" });
  const end = screen.getByRole("slider", { name: "End time" });
  expect(start).toHaveValue("18");
  expect(end).toHaveValue("22");
  expect(start).toHaveAttribute("max", "24");
  expect(end).toHaveAttribute("min", "0");
  fireEvent.change(start, { target: { value: "23" } });
  expect(props.onSelection).toHaveBeenLastCalledWith(
    expect.objectContaining({ from: "22:00" }),
  );
  fireEvent.change(end, { target: { value: "10" } });
  expect(props.onSelection).toHaveBeenLastCalledWith(
    expect.objectContaining({ to: "18:00" }),
  );
});

it("applies the same floored hours that are shown by the sliders", () => {
  const fractionalMovie = {
    ...movie,
    screenings: [
      { cinemaId: "a", date: "2026-10-30", time: "18:00" },
      { cinemaId: "a", date: "2026-10-30", time: "22:30" },
    ],
  };
  render(
    <MinimalCatalogue
      {...props}
      movies={[fractionalMovie]}
      selection={{ ...props.selection, from: "18:30", to: "22:45" }}
    />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: `Preview ${movie.title}` }),
  );
  const preview = within(
    screen.getByRole("region", { name: `${movie.title} screenings` }),
  );
  expect(preview.getByText("18:00")).toBeInTheDocument();
  expect(preview.queryByText("22:30")).not.toBeInTheDocument();
});

it("recovers the detail poster and highlights Movies after navigating from a failed poster", () => {
  const first = { ...movie, poster: "/broken.jpg" };
  const second = {
    ...movie,
    id: "second",
    title: "Second film",
    poster: "/second.jpg",
  };
  const { rerender } = render(
    <MinimalCatalogue
      {...props}
      movies={[first, second]}
      href="/movies/film"
    />,
  );
  fireEvent.error(screen.getByRole("img", { name: movie.title }));
  rerender(
    <MinimalCatalogue
      {...props}
      movies={[first, second]}
      href="/movies/second"
    />,
  );
  expect(screen.getByRole("img", { name: "Second film" })).toHaveAttribute(
    "src",
    "/second.jpg",
  );
  expect(
    within(screen.getByRole("navigation", { name: "Main navigation" })).getByRole("link", {
      name: "Movies",
    }),
  ).toHaveAttribute("aria-current", "page");
});

it("loads the complete schedule when the movie has cached preview screenings", async () => {
  const loadWeek = vi
    .fn()
    .mockResolvedValue({
      screenings: [{ cinemaId: "a", date: "2026-10-30", time: "15:45" }],
      cinemas,
    });
  const { rerender } = render(
    <MinimalCatalogue
      {...props}
      catalogueMovies={[movie]}
      href="/movies/film"
      onLoadWeek={loadWeek}
    />,
  );
  expect(await screen.findByText("15:45")).toBeInTheDocument();
  expect(loadWeek).toHaveBeenCalledOnce();
  rerender(
    <MinimalCatalogue
      {...props}
      catalogueMovies={[{ ...movie, screenings: [] }]}
      href="/movies/film"
      onLoadWeek={loadWeek}
    />,
  );
  expect(await screen.findByText("15:45")).toBeInTheDocument();
  expect(loadWeek).toHaveBeenCalledTimes(2);
  expect(screen.queryByText("18:00")).not.toBeInTheDocument();
});

it.each([8.1, null])("renders detail score only when present: %s", (score) => {
  render(<MinimalCatalogue {...props} movies={[{...movie, tmdbRating: score}]} catalogueMovies={[{...movie, tmdbRating: score}]} href="/movies/film" />);
  if (score === null) expect(screen.queryByText(/8.1\/10/)).not.toBeInTheDocument();
  else expect(screen.getByText(/8.1\/10/)).toBeInTheDocument();
});

it("marks only the current section and the pressed date shortcut", () => {
  /** Scenario: on screenings for today, assistive tech hears only Screenings as current and only Today as pressed. */
  render(
    <MinimalCatalogue
      {...props}
      selection={{ ...props.selection, end: "2026-10-30" }}
    />,
  );
  const navigation = within(screen.getByRole("navigation", { name: "Main navigation" }));
  expect(navigation.getByRole("link", { name: "Screenings" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  for (const name of ["Movies", "Cinemas"])
    expect(navigation.getByRole("link", { name })).not.toHaveAttribute("aria-current");
  expect(screen.getByRole("button", { name: "Today" })).toHaveAttribute("aria-pressed", "true");
  for (const name of ["Tomorrow", "This weekend"])
    expect(screen.getByRole("button", { name })).toHaveAttribute("aria-pressed", "false");
});
