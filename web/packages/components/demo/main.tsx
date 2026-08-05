import { StrictMode, useState, type ComponentType } from "react";
import { createRoot } from "react-dom/client";

import {
  CinemaShowtimeGroups,
  groupByCinema,
  MovieCard,
  MovieCardGrid,
  MovieDetailPage,
  MovieFilterPanel,
  MovieGridController,
  type Cinema,
  type CinemaShowtime,
  type MovieCardData,
  type MovieCardGridItem,
  type MovieDetailClient,
  type MovieGridClient,
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

const demoDates: string[] = ["2026-08-03", "2026-08-04", "2026-08-05"];

const demoCinemas = [cinemaModerne, cinemaCq, cinemaMusee, cinemaBeaubien];

const demoCinemaNames = demoCinemas.map((cinema) => cinema.name);

const demoGenres = [
  "Sci-Fi",
  "Drama",
  "Comedy",
  "Horror",
  "Action",
  "Romance",
  "Musical",
  "History",
];

const demoLanguages = ["VOSTF", "VF", "VO"];

interface DemoMovie {
  key: string;
  title: string;
  releaseYear: number;
  durationMinutes: number;
  directors: string[];
  genres: string[];
  posterUrl?: string;
}

const demoMovieByKey: Record<string, DemoMovie> = {
  dune: {
    key: "dune",
    title: "Dune: Part Two",
    releaseYear: 2024,
    durationMinutes: 166,
    directors: ["Denis Villeneuve"],
    genres: ["Sci-Fi", "Drama"],
    posterUrl: "/slow-poster.jpg",
  },
  anora: {
    key: "anora",
    title: "Anora",
    releaseYear: 2024,
    durationMinutes: 139,
    directors: ["Sean Baker"],
    genres: ["Drama", "Comedy"],
    posterUrl: "https://image.tmdb.org/t/p/original/cgXk2tNYhJZLXdBDO5DidAVzQ82.jpg",
  },
  brutalist: {
    key: "brutalist",
    title: "The Brutalist",
    releaseYear: 2024,
    durationMinutes: 215,
    directors: ["Brady Corbet"],
    genres: ["Drama"],
  },
  nosferatu: {
    key: "nosferatu",
    title: "Nosferatu",
    releaseYear: 2024,
    durationMinutes: 132,
    directors: ["Robert Eggers"],
    genres: ["Horror", "Drama"],
  },
  substance: {
    key: "substance",
    title: "The Substance",
    releaseYear: 2024,
    durationMinutes: 141,
    directors: ["Coralie Fargeat"],
    genres: ["Horror", "Comedy"],
  },
  "a-real-pain": {
    key: "a-real-pain",
    title: "A Real Pain",
    releaseYear: 2024,
    durationMinutes: 90,
    directors: ["Jesse Eisenberg"],
    genres: ["Comedy", "Drama"],
  },
  challengers: {
    key: "challengers",
    title: "Challengers",
    releaseYear: 2024,
    durationMinutes: 131,
    directors: ["Luca Guadagnino"],
    genres: ["Drama", "Romance"],
  },
  "kinds-of-kindness": {
    key: "kinds-of-kindness",
    title: "Kinds of Kindness",
    releaseYear: 2024,
    durationMinutes: 164,
    directors: ["Yorgos Lanthimos"],
    genres: ["Comedy", "Drama"],
  },
  "zone-of-interest": {
    key: "zone-of-interest",
    title: "The Zone of Interest",
    releaseYear: 2023,
    durationMinutes: 105,
    directors: ["Jonathan Glazer"],
    genres: ["Drama", "History"],
  },
  "perfect-days": {
    key: "perfect-days",
    title: "Perfect Days",
    releaseYear: 2023,
    durationMinutes: 123,
    directors: ["Wim Wenders"],
    genres: ["Drama"],
  },
  "emilia-perez": {
    key: "emilia-perez",
    title: "Emilia Pérez",
    releaseYear: 2024,
    durationMinutes: 132,
    directors: ["Jacques Audiard"],
    genres: ["Musical", "Drama"],
  },
  furiosa: {
    key: "furiosa",
    title: "Furiosa: A Mad Max Saga",
    releaseYear: 2024,
    durationMinutes: 148,
    directors: ["George Miller"],
    genres: ["Action", "Sci-Fi"],
  },
};

const dayMovieKeys: Record<string, string[]> = {
  "2026-08-03": [
    "dune",
    "anora",
    "brutalist",
    "nosferatu",
    "substance",
    "a-real-pain",
    "challengers",
    "kinds-of-kindness",
    "zone-of-interest",
    "perfect-days",
    "emilia-perez",
    "furiosa",
  ],
  "2026-08-04": [
    "dune",
    "anora",
    "brutalist",
    "nosferatu",
    "substance",
    "challengers",
    "perfect-days",
    "furiosa",
  ],
  "2026-08-05": [
    "dune",
    "anora",
    "a-real-pain",
    "kinds-of-kindness",
    "emilia-perez",
    "zone-of-interest",
    "perfect-days",
    "challengers",
    "brutalist",
  ],
};

function showtimeFor(
  date: string,
  time: string,
  cinema: Cinema,
  language: string,
): CinemaShowtime {
  return {
    startsAt: `${date}T${time}:00-04:00`,
    language,
    ticketUrl: `https://example.com/tickets/${date}-${time}`,
    cinema,
  };
}

function buildDay(date: string, dayIndex: number): MovieCardGridItem[] {
  const keys = dayMovieKeys[date] ?? [];
  return keys.map((key, index) => {
    const movie = demoMovieByKey[key];
    if (movie === undefined) {
      throw new Error(`No demo movie for key ${key}`);
    }
    const cinema =
      demoCinemas[(index + dayIndex) % demoCinemas.length] ?? cinemaModerne;
    const language =
      demoLanguages[(index + dayIndex) % demoLanguages.length] ?? "VOSTF";
    const screenings = [{ time: `${16 + ((index * 2) % 8)}:00`, cinema, language }];
    if (index % 3 !== 1) {
      const secondCinema =
        demoCinemas[(index + dayIndex + 1) % demoCinemas.length] ?? cinemaCq;
      const secondLanguage =
        demoLanguages[(index + dayIndex + 1) % demoLanguages.length] ?? "VF";
      screenings.push({
        time: `${Math.min(16 + ((index * 2) % 8) + 3, 23)}:00`,
        cinema: secondCinema,
        language: secondLanguage,
      });
    }
    return {
      key,
      movie: {
        title: movie.title,
        releaseYear: movie.releaseYear,
        durationMinutes: movie.durationMinutes,
        directors: movie.directors,
        genres: movie.genres,
        posterUrl: movie.posterUrl,
      },
      showtimesUrl: `https://example.com/movies/${key}`,
      showtimes: screenings.map((screening) =>
        showtimeFor(date, screening.time, screening.cinema, screening.language),
      ),
    };
  });
}

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

const mockClient: MovieGridClient = {
  async listDates() {
    await delay(150);
    return demoDates;
  },
  async fetchForDate(date) {
    await delay(600);
    const dayIndex = demoDates.indexOf(date);
    return buildDay(date, dayIndex === -1 ? 0 : dayIndex);
  },
};

const detailClient: MovieDetailClient = {
  async listDates(movie) {
    await delay(150);
    return demoDates.filter((date) => {
      const dayIndex = demoDates.indexOf(date);
      return buildDay(date, dayIndex === -1 ? 0 : dayIndex).some(
        (item) => item.movie.title === movie.title,
      );
    });
  },
  async fetchShowtimes(movie, date) {
    await delay(400);
    const dayIndex = demoDates.indexOf(date);
    const item = buildDay(date, dayIndex === -1 ? 0 : dayIndex).find(
      (entry) => entry.movie.title === movie.title,
    );
    return item?.showtimes ?? [];
  },
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

function MovieFilterPanelDemo() {
  const [selectedDate, setSelectedDate] = useState("2026-08-03");
  const [selectedCinemas, setSelectedCinemas] = useState<string[]>([]);
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>([]);
  const [timeRange, setTimeRange] = useState<[number, number]>([0, 24]);

  return (
    <div className="flex w-full max-w-4xl gap-8">
      <MovieFilterPanel
        className="w-full max-w-xs"
        dates={demoDates}
        selectedDate={selectedDate}
        onDateChange={setSelectedDate}
        cinemas={demoCinemaNames}
        selectedCinemas={selectedCinemas}
        onCinemasChange={(next) => setSelectedCinemas([...next])}
        genres={demoGenres}
        selectedGenres={selectedGenres}
        onGenresChange={(next) => setSelectedGenres([...next])}
        languages={demoLanguages}
        selectedLanguages={selectedLanguages}
        onLanguagesChange={(next) => setSelectedLanguages([...next])}
        timeRange={timeRange}
        onTimeRangeChange={(next) => setTimeRange([next[0], next[1]])}
      />
      <div className="min-w-0 flex-1">
        <p className="text-sm text-muted-foreground">
          The panel is fully controlled — the demo owns the state. Used on its
          own it renders no data; wire it to a grid with{" "}
          <code className="font-mono text-xs">MovieGridController</code> or{" "}
          <code className="font-mono text-xs">useMovieFilters</code>.
        </p>
      </div>
    </div>
  );
}

function MovieGridControllerDemo() {
  const [selectedMovie, setSelectedMovie] = useState<MovieCardData | null>(null);

  if (selectedMovie !== null) {
    return (
      <MovieDetailPage
        className="h-full w-full overflow-y-auto"
        movie={selectedMovie}
        client={detailClient}
        currentTime={currentTime}
        onBack={() => setSelectedMovie(null)}
      />
    );
  }

  return (
    <MovieGridController
      className="h-full w-full"
      client={mockClient}
      side="right"
      currentTime={currentTime}
      backgroundColor="#f2efe9"
      pageSize="auto"
      onMovieClick={setSelectedMovie}
    />
  );
}

function MovieDetailPageDemo() {
  const dune = demoMovieByKey["dune"];
  if (dune === undefined) {
    throw new Error("Demo movie not found");
  }
  return (
    <MovieDetailPage
      className="h-full w-full max-w-3xl overflow-y-auto"
      movie={{
        title: dune.title,
        releaseYear: dune.releaseYear,
        durationMinutes: dune.durationMinutes,
        directors: dune.directors,
        genres: dune.genres,
        posterUrl: dune.posterUrl,
      }}
      client={detailClient}
      currentTime={currentTime}
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
  {
    id: "movie-filter-panel",
    label: "MovieFilterPanel",
    Component: MovieFilterPanelDemo,
  },
  {
    id: "movie-grid-controller",
    label: "MovieGridController",
    Component: MovieGridControllerDemo,
  },
  {
    id: "movie-detail-page",
    label: "MovieDetailPage",
    Component: MovieDetailPageDemo,
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
