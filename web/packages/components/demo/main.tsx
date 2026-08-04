import { StrictMode, useState, type ComponentType } from "react";
import { createRoot } from "react-dom/client";

import {
  CinemaShowtimeGroups,
  groupByCinema,
  MovieCard,
  MovieCardGrid,
  type Cinema,
  type CinemaShowtime,
  type MovieCardGridItem,
} from "../src/index";
import "../src/index.css";

interface DemoEntry {
  id: string;
  label: string;
  Component: ComponentType;
}

const currentTime = "2026-08-03T19:30:00-04:00";

const cinemaModerne: Cinema = {
  id: "cinema-moderne",
  name: "Cinéma Moderne",
  link: "https://example.com/cinemas/cinema-moderne",
};

const cinemaCq: Cinema = {
  id: "cine-cq",
  name: "Cinémathèque québécoise",
  link: "https://example.com/cinemas/cine-cq",
};

const cinemaMusee: Cinema = {
  id: "cinema-du-musee",
  name: "Cinéma du Musée",
  link: "https://example.com/cinemas/cinema-du-musee",
};

const cinemaBeaubien: Cinema = {
  id: "cinema-beaubien",
  name: "Cinéma Beaubien",
  link: "https://example.com/cinemas/cinema-beaubien",
};

function showtime(
  startsAt: string,
  ticketUrl: string,
  cinema: Cinema,
): CinemaShowtime {
  return { startsAt, ticketUrl, cinema };
}

function gridMovie(
  key: string,
  title: string,
  releaseYear: number,
  durationMinutes: number,
  directors: string[],
  cinema: Cinema,
  time: string,
): MovieCardGridItem {
  return {
    key,
    movie: { title, releaseYear, durationMinutes, directors },
    showtimesUrl: `https://example.com/movies/${key}`,
    showtimes: [
      showtime(
        `2026-08-03T${time}:00-04:00`,
        `https://example.com/tickets/${key}`,
        cinema,
      ),
    ],
  };
}

const duneShowtimes: CinemaShowtime[] = (() => {
  const cinemas = [cinemaModerne, cinemaCq, cinemaMusee, cinemaBeaubien];
  const times = ["11:15", "14:00", "16:30", "19:45", "22:00"];
  const list: CinemaShowtime[] = [];
  for (const cinema of cinemas) {
    times.forEach((time, index) => {
      list.push(
        showtime(
          `2026-08-03T${time}:00-04:00`,
          `https://example.com/tickets/dune-${cinema.id}-${index}`,
          cinema,
        ),
      );
    });
  }
  return list;
})();

const showtimes: CinemaShowtime[] = [
  {
    startsAt: "2026-08-03T17:40:00-04:00",
    language: "VOSTF",
    format: "IMAX",
    ticketUrl: "https://example.com/tickets/dune-part-two-imax",
    cinema: {
      id: "cinema-moderne",
      name: "Cinéma Moderne",
      link: "https://example.com/cinemas/cinema-moderne",
    },
  },
  {
    startsAt: "2026-08-03T21:00:00-04:00",
    language: "VF",
    format: "2D",
    ticketUrl: "https://example.com/tickets/dune-part-two-2d",
    cinema: {
      id: "cinema-moderne",
      name: "Cinéma Moderne",
      link: "https://example.com/cinemas/cinema-moderne",
    },
  },
  {
    startsAt: "2026-08-03T15:15:00-04:00",
    language: "VO",
    format: "2D",
    ticketUrl: "https://example.com/tickets/dune-part-two-cq",
    cinema: {
      id: "cine-cq",
      name: "Cinémathèque québécoise",
      link: "https://example.com/cinemas/cine-cq",
    },
  },
  {
    startsAt: "2026-08-03T20:30:00-04:00",
    language: "VO",
    format: "2D",
    ticketUrl: "https://example.com/tickets/dune-part-two-cq-2",
    cinema: {
      id: "cine-cq",
      name: "Cinémathèque québécoise",
      link: "https://example.com/cinemas/cine-cq",
    },
  },
  {
    startsAt: "2026-08-03T18:00:00-04:00",
    language: "VOSTF",
    format: "2D",
    ticketUrl: "https://example.com/tickets/dune-part-two-musee",
    cinema: {
      id: "cinema-du-musee",
      name: "Cinéma du Musée",
      link: "https://example.com/cinemas/cinema-du-musee",
    },
  },
];

function MovieCardDemo() {
  return (
    <>
      <MovieCard
        className="w-full max-w-sm"
        backgroundColor="#f2efe9"
        currentTime={currentTime}
        showtimesUrl="https://example.com/movies/dune-part-two"
        movie={{
          title: "Dune: Part Two",
          posterUrl: "/slow-poster.jpg",
          releaseYear: 2024,
          durationMinutes: 166,
          directors: ["Denis Villeneuve"],
        }}
        showtimes={showtimes}
      />
      <p className="max-w-sm text-center text-xs text-muted-foreground">
        The poster endpoint responds after a 1s delay, so a thin loading bar
        shows at the bottom of the poster while the image is actually loading.
      </p>
    </>
  );
}

function ShowtimesWidgetDemo() {
  return (
    <div className="w-full max-w-sm">
      <CinemaShowtimeGroups
        groups={groupByCinema(showtimes)}
        currentTime={currentTime}
      />
    </div>
  );
}

function MovieCardGridDemo() {
  return (
    <MovieCardGrid
      pageSize="auto"
      className="w-full max-w-4xl"
      backgroundColor="#f2efe9"
      currentTime={currentTime}
      items={[
        {
          key: "dune",
          movie: {
            title: "Dune: Part Two",
            posterUrl: "/slow-poster.jpg",
            releaseYear: 2024,
            durationMinutes: 166,
            directors: ["Denis Villeneuve"],
          },
          showtimesUrl: "https://example.com/movies/dune-part-two",
          showtimes: duneShowtimes,
        },
        {
          key: "anora",
          movie: {
            title: "Anora",
            posterUrl:
              "https://image.tmdb.org/t/p/original/cgXk2tNYhJZLXdBDO5DidAVzQ82.jpg",
            releaseYear: 2024,
            durationMinutes: 139,
            directors: ["Sean Baker"],
          },
          showtimesUrl: "https://example.com/movies/anora",
          showtimes: [
            showtime(
              "2026-08-03T20:30:00-04:00",
              "https://example.com/tickets/anora-moderne",
              cinemaModerne,
            ),
            showtime(
              "2026-08-03T18:15:00-04:00",
              "https://example.com/tickets/anora-cq",
              cinemaCq,
            ),
          ],
        },
        gridMovie(
          "brutalist",
          "The Brutalist",
          2024,
          215,
          ["Brady Corbet"],
          cinemaMusee,
          "19:00",
        ),
        gridMovie(
          "nosferatu",
          "Nosferatu",
          2024,
          132,
          ["Robert Eggers"],
          cinemaCq,
          "21:30",
        ),
        gridMovie(
          "substance",
          "The Substance",
          2024,
          141,
          ["Coralie Fargeat"],
          cinemaModerne,
          "20:00",
        ),
        gridMovie(
          "a-real-pain",
          "A Real Pain",
          2024,
          90,
          ["Jesse Eisenberg"],
          cinemaCq,
          "17:00",
        ),
        gridMovie(
          "challengers",
          "Challengers",
          2024,
          131,
          ["Luca Guadagnino"],
          cinemaMusee,
          "21:00",
        ),
        gridMovie(
          "kinds-of-kindness",
          "Kinds of Kindness",
          2024,
          164,
          ["Yorgos Lanthimos"],
          cinemaBeaubien,
          "19:30",
        ),
        gridMovie(
          "zone-of-interest",
          "The Zone of Interest",
          2023,
          105,
          ["Jonathan Glazer"],
          cinemaModerne,
          "16:45",
        ),
        gridMovie(
          "perfect-days",
          "Perfect Days",
          2023,
          123,
          ["Wim Wenders"],
          cinemaCq,
          "20:15",
        ),
        gridMovie(
          "emilia-perez",
          "Emilia Pérez",
          2024,
          132,
          ["Jacques Audiard"],
          cinemaMusee,
          "18:45",
        ),
        gridMovie(
          "furiosa",
          "Furiosa: A Mad Max Saga",
          2024,
          148,
          ["George Miller"],
          cinemaBeaubien,
          "22:15",
        ),
      ]}
    />
  );
}

const demoEntries: DemoEntry[] = [
  { id: "movie-card", label: "MovieCard", Component: MovieCardDemo },
  {
    id: "showtimes-widget",
    label: "Showtimes widget",
    Component: ShowtimesWidgetDemo,
  },
  {
    id: "movie-card-grid",
    label: "MovieCardGrid",
    Component: MovieCardGridDemo,
  },
];

function App() {
  const firstEntry = demoEntries[0];
  if (firstEntry === undefined) {
    throw new Error("No demo entries configured");
  }

  const [selectedId, setSelectedId] = useState(firstEntry.id);
  const selected = demoEntries.find((entry) => entry.id === selectedId) ?? firstEntry;
  const ActiveComponent = selected.Component;

  return (
    <div className="bg-background flex h-dvh flex-col overflow-hidden p-6">
      <label className="mb-6 flex shrink-0 items-center gap-2 text-sm">
        Component
        <select
          value={selected.id}
          onChange={(event) => setSelectedId(event.target.value)}
          className="rounded-md border bg-background px-2 py-1 text-sm"
        >
          {demoEntries.map((entry) => (
            <option key={entry.id} value={entry.id}>
              {entry.label}
            </option>
          ))}
        </select>
      </label>
      <div className="flex min-h-0 flex-1 items-center justify-center">
        <ActiveComponent />
      </div>
    </div>
  );
}

const root = document.getElementById("root");
if (root === null) {
  throw new Error("Demo root element not found");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
