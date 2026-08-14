import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CinemaShowtimeGroups, groupByCinema } from "./CinemaShowtimes";
import { MovieCard } from "./MovieCard";

describe("MovieCard", () => {
  it("renders title, year, duration and flat showtimes", () => {
    render(
      <MovieCard
        movie={{
          title: "Anora",
          releaseYear: 2024,
          durationMinutes: 139,
          directors: ["Sean Baker"],
        }}
        showtimesUrl="https://example.com/movies/anora"
        showtimes={[
          {
            startsAt: "2026-08-03T22:30:00Z",
            language: "VOSTF",
            format: "2D",
            ticketUrl: "https://tickets.example.com/anora",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
        ]}
      />,
    );

    expect(screen.getByRole("heading", { name: "Anora" })).toBeInTheDocument();
    expect(
      screen.getByText("2024 · 2 h 19 min"),
    ).toBeInTheDocument();
    expect(screen.getByText("18:30")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Anora" })).toHaveClass("text-center");
  });

  it("shrinks and truncates long titles to one line", () => {
    const title = "The Incredibly Long Movie Title That Must Stay Readable";
    render(
      <MovieCard
        movie={{ title }}
        showtimesUrl="https://example.com/movies/long-title"
      />,
    );

    const heading = screen.getByRole("heading", { name: title });
    expect(heading).toHaveClass("text-sm");
    expect(heading).not.toHaveClass("line-clamp-2");
    expect(screen.getByRole("link", { name: title })).toHaveClass("truncate");
  });

  it("retains the title but hides details when hideDetails is true", () => {
    render(
      <MovieCard
        movie={{
          title: "Anora",
          releaseYear: 2024,
          durationMinutes: 139,
          directors: ["Sean Baker"],
        }}
        showtimesUrl="https://example.com/movies/anora"
        showtimes={[
          {
            startsAt: "2026-08-03T22:30:00Z",
            language: "VOSTF",
            format: "2D",
            ticketUrl: "https://tickets.example.com/anora",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
        ]}
        hideDetails
      />,
    );

    const poster = screen.getByRole("link", { name: "Poster for Anora" });
    expect(poster).toBeInTheDocument();
    expect(poster).toHaveClass("aspect-[2/3]");
    expect(screen.getByRole("heading", { name: "Anora" })).toBeInTheDocument();
    expect(
      screen.queryByText("2024 · 2 h 19 min"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("18:30")).not.toBeInTheDocument();
  });

  it("sorts the card showtimes by time, not by input order", () => {
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        showtimesUrl="https://example.com/movies/anora"
        showtimes={[
          {
            startsAt: "2026-08-03T21:00:00-04:00",
            ticketUrl: "https://tickets.example.com/a",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
          {
            startsAt: "2026-08-03T16:15:00-04:00",
            ticketUrl: "https://tickets.example.com/b",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
          {
            startsAt: "2026-08-03T18:30:00-04:00",
            ticketUrl: "https://tickets.example.com/c",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
        ]}
      />,
    );

    const times = screen
      .getAllByRole("link")
      .map((link) => link.textContent)
      .filter(
        (text): text is string =>
          text !== null && /^\d{2}:\d{2}$/.test(text),
      );

    expect(times).toEqual(["16:15", "18:30", "21:00"]);
  });

  it("shows a compact, wrapping subset and expands to every showtime", () => {
    const showtimes = Array.from({ length: 8 }, (_, index) => {
      const hour = String(10 + index).padStart(2, "0");
      return {
        startsAt: `2026-08-03T${hour}:00:00-04:00`,
        ticketUrl: `https://tickets.example.com/${hour}`,
        cinema: {
          id: "cinema-moderne",
          name: "Cinéma Moderne",
          link: "https://example.com/cinemas/cinema-moderne",
        },
      };
    });
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        showtimesUrl="https://example.com/movies/anora"
        showtimes={showtimes}
      />,
    );

    const chips = screen
      .getAllByRole("link")
      .map((link) => link.textContent)
      .filter(
        (text): text is string =>
          text !== null && /^\d{2}:\d{2}$/.test(text),
      );

    expect(chips).toEqual(["10:00", "11:00", "12:00"]);
    const compactShowtimes = screen.getByText("10:00").parentElement;
    expect(compactShowtimes).toHaveClass("flex-wrap");
    expect(compactShowtimes).not.toHaveClass("overflow-hidden");

    fireEvent.click(screen.getByRole("button", { name: "All showtimes for Anora" }));

    expect(
      within(screen.getByRole("dialog", { name: "All showtimes for Anora" }))
        .getAllByRole("link")
        .map((link) => link.textContent)
        .filter((text): text is string => text !== null && /^\d{2}:\d{2}$/.test(text)),
    ).toEqual(["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"]);
  });

  it("shows showtimes and marks started ones as crossed out", () => {
    const showtimes = Array.from({ length: 6 }, (_, index) => {
      const hour = String(12 + index).padStart(2, "0");
      return {
        startsAt: `2026-08-03T${hour}:00:00-04:00`,
        ticketUrl: `https://tickets.example.com/${hour}`,
        cinema: {
          id: "cinema-moderne",
          name: "Cinéma Moderne",
          link: "https://example.com/cinemas/cinema-moderne",
        },
      };
    });
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        showtimesUrl="https://example.com/movies/anora"
        currentTime="2026-08-03T14:30:00-04:00"
        showtimes={showtimes}
      />,
    );

    const chips = screen
      .getAllByRole("link")
      .map((link) => link.textContent)
      .filter(
        (text): text is string =>
          text !== null && /^\d{2}:\d{2}$/.test(text),
      );

    expect(chips).toEqual(["12:00", "13:00", "14:00"]);
    expect(screen.getByText("12:00")).toHaveClass("line-through");
    expect(screen.getByText("14:00")).toHaveClass("line-through");
  });

  it("respects a custom maxShowtimes limit", () => {
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        showtimesUrl="https://example.com/movies/anora"
        maxShowtimes={2}
        showtimes={[
          {
            startsAt: "2026-08-03T10:00:00-04:00",
            ticketUrl: "https://tickets.example.com/a",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
          {
            startsAt: "2026-08-03T11:00:00-04:00",
            ticketUrl: "https://tickets.example.com/b",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
          {
            startsAt: "2026-08-03T12:00:00-04:00",
            ticketUrl: "https://tickets.example.com/c",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
        ]}
      />,
    );

    const chips = screen
      .getAllByRole("link")
      .map((link) => link.textContent)
      .filter(
        (text): text is string =>
          text !== null && /^\d{2}:\d{2}$/.test(text),
      );

    expect(chips).toEqual(["10:00", "11:00"]);
  });

  it("uses one expansion control for showtimes", () => {
    const showtimes = Array.from({ length: 6 }, (_, index) => {
      const hour = String(10 + index).padStart(2, "0");
      return {
        startsAt: `2026-08-03T${hour}:00:00-04:00`,
        ticketUrl: `https://tickets.example.com/${hour}`,
        cinema: {
          id: "cinema-moderne",
          name: "Cinéma Moderne",
          link: "https://example.com/cinemas/cinema-moderne",
        },
      };
    });
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        showtimesUrl="https://example.com/movies/anora"
        showtimes={showtimes}
      />,
    );

    expect(screen.getByText("12:00")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "All showtimes for Anora" }),
    ).toHaveAttribute("aria-expanded", "false");
    expect(
      screen.queryByRole("button", { name: "More showtimes for Anora" }),
    ).not.toBeInTheDocument();
  });

  it("renders a poster placeholder when no posterUrl is given", () => {
    render(
      <MovieCard
        movie={{ title: "No Poster" }}
        showtimesUrl="https://example.com/movies/no-poster"
      />,
    );

    expect(screen.getAllByText("No Poster")).toHaveLength(2);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("links the poster to the movie page", () => {
    render(
      <MovieCard
        movie={{ title: "Anora", posterUrl: "https://example.com/anora.jpg" }}
        showtimesUrl="https://example.com/movies/anora"
      />,
    );

    const posterLink = screen.getByRole("link", { name: "Poster for Anora" });
    expect(posterLink).toHaveAttribute("href", "https://example.com/movies/anora");
    expect(posterLink).toHaveAttribute("target", "_blank");
  });

  it("turns the title and poster into buttons that call onMovieClick", () => {
    const onMovieClick = vi.fn();
    const movie = { title: "Anora", posterUrl: "https://example.com/anora.jpg" };
    render(
      <MovieCard
        movie={movie}
        showtimesUrl="https://example.com/movies/anora"
        onMovieClick={onMovieClick}
      />,
    );

    expect(
      screen.queryByRole("link", { name: "Poster for Anora" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Anora" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Anora" }));
    fireEvent.click(screen.getByRole("button", { name: "Poster for Anora" }));

    expect(onMovieClick).toHaveBeenCalledTimes(2);
    expect(onMovieClick).toHaveBeenCalledWith(movie);
  });

  it("keeps the placeholder behind the poster and loads the image at low priority", () => {
    render(
      <MovieCard
        movie={{ title: "Anora", posterUrl: "https://example.com/anora.jpg" }}
        showtimesUrl="https://example.com/movies/anora"
      />,
    );

    expect(screen.getAllByText("Anora")).toHaveLength(2);

    const img = screen.getByRole("img", { name: "Poster for Anora" });
    expect(img).toHaveAttribute("loading", "lazy");
    expect(img).toHaveAttribute("decoding", "async");
    expect(img).toHaveAttribute("fetchpriority", "low");
  });

  it("shows a loading bar while the poster loads and fades the image in", () => {
    render(
      <MovieCard
        movie={{ title: "Anora", posterUrl: "https://example.com/anora.jpg" }}
        showtimesUrl="https://example.com/movies/anora"
      />,
    );

    const img = screen.getByRole("img", { name: "Poster for Anora" });

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    expect(img).toHaveClass("opacity-0");

    fireEvent.load(img);

    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    expect(img).toHaveClass("opacity-100");
  });

  it("hides the poster and the loading bar when the image fails to load", () => {
    render(
      <MovieCard
        movie={{ title: "Anora", posterUrl: "https://example.com/anora.jpg" }}
        showtimesUrl="https://example.com/movies/anora"
      />,
    );

    fireEvent.error(screen.getByRole("img", { name: "Poster for Anora" }));

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    expect(screen.getAllByText("Anora")).toHaveLength(2);
  });

  it("renders a muted note when there are no showtimes", () => {
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        showtimesUrl="https://example.com/movies/anora"
      />,
    );

    expect(screen.getByText("No showtimes yet")).toBeInTheDocument();
  });

  it("fills the card background when backgroundColor is set", () => {
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        showtimesUrl="https://example.com/movies/anora"
        backgroundColor="#ff0000"
      />,
    );

    const card = screen
      .getByRole("heading", { name: "Anora" })
      .closest("[data-slot='card']") as HTMLElement;
    expect(card).toHaveStyle({ backgroundColor: "#ff0000" });
  });

  it("marks started showtimes as crossed out next to upcoming ones", () => {
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        showtimesUrl="https://example.com/movies/anora"
        currentTime="2026-08-03T19:00:00-04:00"
        showtimes={[
          {
            startsAt: "2026-08-03T18:30:00-04:00",
            ticketUrl: "https://tickets.example.com/a",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
          {
            startsAt: "2026-08-03T20:30:00-04:00",
            ticketUrl: "https://tickets.example.com/b",
            cinema: {
              id: "cine-cq",
              name: "Cinémathèque québécoise",
              link: "https://example.com/cinemas/cine-cq",
            },
          },
        ]}
      />,
    );

    expect(screen.getByRole("link", { name: "18:30" })).toHaveClass(
      "line-through",
    );
    expect(screen.getByRole("link", { name: "20:30" })).not.toHaveClass(
      "line-through",
    );

    fireEvent.click(
      screen.getByRole("button", { name: "All showtimes for Anora" }),
    );

    const links = screen.getAllByRole("link", { name: "18:30" });
    expect(links.some((link) => link.classList.contains("line-through"))).toBe(
      true,
    );
  });

  it("renders a showtime as a link to its ticketing URL", () => {
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        showtimesUrl="https://example.com/movies/anora"
        showtimes={[
          {
            startsAt: "2026-08-03T22:30:00Z",
            ticketUrl: "https://tickets.example.com/anora",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
        ]}
      />,
    );

    const link = screen.getByRole("link", { name: "18:30" });
    expect(link).toHaveAttribute("href", "https://tickets.example.com/anora");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("renders missing cinema and ticket URLs as plain text", () => {
    render(
      <CinemaShowtimeGroups
        groups={groupByCinema([
          {
            startsAt: "2026-08-03T22:30:00Z",
            ticketUrl: null,
            cinema: { id: "cinema-1", name: "Cinema One", link: null },
          },
        ])}
      />,
    );

    expect(screen.getByText("Cinema One")).not.toHaveAttribute("href");
    expect(screen.getByText("18:30")).not.toHaveAttribute("href");
  });

  it("invokes onShowtimeClick when a showtime chip is clicked", () => {
    const onShowtimeClick = vi.fn();
    const showtime = {
      startsAt: "2026-08-03T22:30:00Z",
      ticketUrl: "https://tickets.example.com/anora",
      cinema: {
        id: "cinema-moderne",
        name: "Cinéma Moderne",
        link: "https://example.com/cinemas/cinema-moderne",
      },
    };
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        showtimesUrl="https://example.com/movies/anora"
        showtimes={[showtime]}
        onShowtimeClick={onShowtimeClick}
      />,
    );

    fireEvent.click(screen.getByRole("link", { name: "18:30" }));

    expect(onShowtimeClick).toHaveBeenCalledOnce();
    expect(onShowtimeClick).toHaveBeenCalledWith(showtime);
  });

  it("renders a custom showtime via the renderShowtime render prop", () => {
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        showtimesUrl="https://example.com/movies/anora"
        showtimes={[
          {
            startsAt: "2026-08-03T22:30:00Z",
            ticketUrl: "https://tickets.example.com/anora",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
        ]}
        renderShowtime={(showtime) => <span>Custom {showtime.startsAt}</span>}
      />,
    );

    expect(screen.getByText("Custom 2026-08-03T22:30:00Z")).toBeInTheDocument();
  });

  it("renders the title as a link to all showtimes when showtimesUrl is set", () => {
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        showtimesUrl="https://example.com/movies/anora"
      />,
    );

    const link = screen.getByRole("link", { name: "Anora" });
    expect(link).toHaveAttribute("href", "https://example.com/movies/anora");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("opens grouped showtimes in a portaled popover via the caret", () => {
    const { container } = render(
      <MovieCard
        movie={{ title: "Anora" }}
        showtimesUrl="https://example.com/movies/anora"
        showtimes={[
          {
            startsAt: "2026-08-03T22:30:00Z",
            ticketUrl: "https://tickets.example.com/a",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
          {
            startsAt: "2026-08-03T20:15:00Z",
            ticketUrl: "https://tickets.example.com/b",
            cinema: {
              id: "cine-cq",
              name: "Cinémathèque québécoise",
              link: "https://example.com/cinemas/cine-cq",
            },
          },
        ]}
      />,
    );

    expect(screen.queryByText("Cinéma Moderne")).not.toBeInTheDocument();

    const caret = screen.getByRole("button", {
      name: "All showtimes for Anora",
    });
    fireEvent.click(caret);

    expect(screen.getByText("Cinéma Moderne")).toBeInTheDocument();
    expect(screen.getByText("Cinémathèque québécoise")).toBeInTheDocument();
    expect(caret).toHaveAttribute("aria-expanded", "true");
    const popover = screen.getByRole("dialog", {
      name: "All showtimes for Anora",
    });
    expect(popover).toHaveClass("border", "border-border", "shadow-sm");
    expect(container).not.toContainElement(popover);
    expect(
      screen.getByRole("button", { name: "Close all showtimes for Anora" }),
    ).toHaveClass("bg-card");

    fireEvent.click(
      screen.getByRole("button", { name: "Close all showtimes for Anora" }),
    );

    expect(screen.queryByText("Cinéma Moderne")).not.toBeInTheDocument();
  });

  it("renders grouped showtimes as ticket links and crosses out started ones", () => {
    const groups = groupByCinema([
      {
        startsAt: "2026-08-03T18:30:00-04:00",
        ticketUrl: "https://tickets.example.com/a",
        cinema: {
          id: "cinema-moderne",
          name: "Cinéma Moderne",
          link: "https://example.com/cinemas/cinema-moderne",
        },
      },
      {
        startsAt: "2026-08-03T21:00:00-04:00",
        ticketUrl: "https://tickets.example.com/b",
        cinema: {
          id: "cinema-moderne",
          name: "Cinéma Moderne",
          link: "https://example.com/cinemas/cinema-moderne",
        },
      },
    ]);

    render(
      <CinemaShowtimeGroups
        groups={groups}
        currentTime="2026-08-03T19:00:00-04:00"
      />,
    );

    const passedLink = screen.getByRole("link", { name: "18:30" });
    expect(passedLink).toHaveAttribute("href", "https://tickets.example.com/a");
    expect(passedLink).toHaveClass("line-through");

    const upcomingLink = screen.getByRole("link", { name: "21:00" });
    expect(upcomingLink).toHaveAttribute(
      "href",
      "https://tickets.example.com/b",
    );
    expect(upcomingLink).not.toHaveClass("line-through");
  });

  it("opens the hover popover with grouped showtimes on hover", async () => {
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        hoverOpenDelay={0}
        showtimesUrl="https://example.com/movies/anora"
        showtimes={[
          {
            startsAt: "2026-08-03T22:30:00Z",
            ticketUrl: "https://tickets.example.com/a",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
        ]}
      />,
    );

    fireEvent.pointerEnter(
      screen.getByRole("link", { name: "Poster for Anora" }),
    );

    expect(await screen.findByText("Cinéma Moderne")).toBeInTheDocument();
  });

  it("opens the hover popover with grouped showtimes when hovering the poster", async () => {
    render(
      <MovieCard
        movie={{ title: "Anora", posterUrl: "https://example.com/anora.jpg" }}
        hoverOpenDelay={0}
        showtimesUrl="https://example.com/movies/anora"
        showtimes={[
          {
            startsAt: "2026-08-03T22:30:00Z",
            ticketUrl: "https://tickets.example.com/a",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
        ]}
      />,
    );

    fireEvent.pointerEnter(
      screen.getByRole("link", { name: "Poster for Anora" }),
    );

    expect(await screen.findByText("Cinéma Moderne")).toBeInTheDocument();
  });

  it("suppresses the hover popover while the expanded popover is open", async () => {
    render(
      <MovieCard
        movie={{ title: "Anora" }}
        hoverOpenDelay={0}
        showtimesUrl="https://example.com/movies/anora"
        showtimes={[
          {
            startsAt: "2026-08-03T22:30:00Z",
            ticketUrl: "https://tickets.example.com/a",
            cinema: {
              id: "cinema-moderne",
              name: "Cinéma Moderne",
              link: "https://example.com/cinemas/cinema-moderne",
            },
          },
        ]}
      />,
    );

    screen.getByRole("button", { name: "All showtimes for Anora" }).click();
    fireEvent.pointerEnter(screen.getByRole("link", { name: "Anora" }));

    expect(await screen.findByText("Cinéma Moderne")).toBeInTheDocument();
    expect(screen.getAllByText("Cinéma Moderne")).toHaveLength(1);
  });
});
