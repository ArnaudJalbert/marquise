import type { Cinema, CinemaShowtime } from "./cinema";
import type { MovieCardGridItem, MovieGridClient } from "./movie-grid-client";

export interface MockMovieGridClientOptions {
  /** First selectable date as "YYYY-MM-DD"; defaults to today (local time). */
  startDate?: string;
  /** Number of selectable days; defaults to 7. */
  days?: number;
}

interface MockMovie {
  key: string;
  title: string;
  releaseYear: number;
  durationMinutes: number;
  directors: readonly string[];
  genres: readonly string[];
  posterUrl?: string;
}

const CATALOGUE: readonly MockMovie[] = [
  {
    key: "dune",
    title: "Dune: Part Two",
    releaseYear: 2024,
    durationMinutes: 166,
    directors: ["Denis Villeneuve"],
    genres: ["Sci-Fi", "Drama"],
    posterUrl: "https://image.tmdb.org/t/p/original/cgXk2tNYhJZLXdBDO5DidAVzQ82.jpg",
  },
  {
    key: "anora",
    title: "Anora",
    releaseYear: 2024,
    durationMinutes: 139,
    directors: ["Sean Baker"],
    genres: ["Drama", "Comedy"],
  },
  {
    key: "brutalist",
    title: "The Brutalist",
    releaseYear: 2024,
    durationMinutes: 215,
    directors: ["Brady Corbet"],
    genres: ["Drama"],
  },
  {
    key: "nosferatu",
    title: "Nosferatu",
    releaseYear: 2024,
    durationMinutes: 132,
    directors: ["Robert Eggers"],
    genres: ["Horror", "Drama"],
  },
  {
    key: "substance",
    title: "The Substance",
    releaseYear: 2024,
    durationMinutes: 141,
    directors: ["Coralie Fargeat"],
    genres: ["Horror", "Comedy"],
  },
  {
    key: "a-real-pain",
    title: "A Real Pain",
    releaseYear: 2024,
    durationMinutes: 90,
    directors: ["Jesse Eisenberg"],
    genres: ["Comedy", "Drama"],
  },
  {
    key: "challengers",
    title: "Challengers",
    releaseYear: 2024,
    durationMinutes: 131,
    directors: ["Luca Guadagnino"],
    genres: ["Drama", "Romance"],
  },
  {
    key: "kinds-of-kindness",
    title: "Kinds of Kindness",
    releaseYear: 2024,
    durationMinutes: 164,
    directors: ["Yorgos Lanthimos"],
    genres: ["Comedy", "Drama"],
  },
  {
    key: "zone-of-interest",
    title: "The Zone of Interest",
    releaseYear: 2023,
    durationMinutes: 105,
    directors: ["Jonathan Glazer"],
    genres: ["Drama", "History"],
  },
  {
    key: "perfect-days",
    title: "Perfect Days",
    releaseYear: 2023,
    durationMinutes: 123,
    directors: ["Wim Wenders"],
    genres: ["Drama"],
  },
  {
    key: "emilia-perez",
    title: "Emilia Pérez",
    releaseYear: 2024,
    durationMinutes: 132,
    directors: ["Jacques Audiard"],
    genres: ["Musical", "Drama"],
  },
  {
    key: "furiosa",
    title: "Furiosa: A Mad Max Saga",
    releaseYear: 2024,
    durationMinutes: 148,
    directors: ["George Miller"],
    genres: ["Action", "Sci-Fi"],
  },
];

const CINEMA_MODERNE: Cinema = {
  id: "cinema-moderne",
  name: "Cinéma Moderne",
  link: "https://example.com/cinemas/cinema-moderne",
};

const CINEMAS: readonly Cinema[] = [
  CINEMA_MODERNE,
  {
    id: "cine-cq",
    name: "Cinémathèque québécoise",
    link: "https://example.com/cinemas/cine-cq",
  },
  {
    id: "cinema-du-musee",
    name: "Cinéma du Musée",
    link: "https://example.com/cinemas/cinema-du-musee",
  },
  {
    id: "cinema-beaubien",
    name: "Cinéma Beaubien",
    link: "https://example.com/cinemas/cinema-beaubien",
  },
];

const LANGUAGES: readonly string[] = ["VOSTF", "VF", "VO"];
const DEFAULT_LANGUAGE = "VOSTF";

const TIMES: readonly string[] = [
  "11:15",
  "13:45",
  "16:30",
  "18:45",
  "20:15",
  "22:00",
];

/**
 * A {@link MovieGridClient} that serves deterministic demo data, so the UI is
 * usable with zero backend. The same date always yields the same items —
 * every date is seeded from its "YYYY-MM-DD" string — across calls and
 * client instances.
 */
export class MockMovieGridClient implements MovieGridClient {
  private readonly dates: readonly string[];
  private readonly offsetSuffix: string;

  constructor(options: MockMovieGridClientOptions = {}) {
    const startDate = options.startDate ?? toDateString(new Date());
    this.dates = Array.from({ length: options.days ?? 7 }, (_, index) =>
      addDays(startDate, index),
    );
    this.offsetSuffix = localOffsetSuffix(new Date());
  }

  async listDates(): Promise<readonly string[]> {
    return this.dates;
  }

  async fetchForDate(date: string): Promise<readonly MovieCardGridItem[]> {
    if (!this.dates.includes(date)) {
      return [];
    }
    const rand = mulberry32(hashString(date));
    const movieCount = 8 + Math.floor(rand() * Math.min(5, CATALOGUE.length));
    const movies = pick(rand, CATALOGUE, movieCount);
    return movies.map((movie) => {
      const showtimeCount = 1 + Math.floor(rand() * 3);
      const cinemas = pick(rand, CINEMAS, showtimeCount);
      const times = pick(rand, TIMES, showtimeCount);
      return {
        key: movie.key,
        movie: {
          title: movie.title,
          posterUrl: movie.posterUrl,
          releaseYear: movie.releaseYear,
          durationMinutes: movie.durationMinutes,
          directors: movie.directors,
          genres: movie.genres,
        },
        showtimesUrl: `https://example.com/movies/${movie.key}`,
        showtimes: times.map((time, index) =>
          this.toShowtime(
            date,
            movie.key,
            time,
            cinemas[index] ?? CINEMA_MODERNE,
            LANGUAGES[Math.floor(rand() * LANGUAGES.length)] ?? DEFAULT_LANGUAGE,
          ),
        ),
      };
    });
  }

  private toShowtime(
    date: string,
    movieKey: string,
    time: string,
    cinema: Cinema,
    language: string,
  ): CinemaShowtime {
    return {
      startsAt: `${date}T${time}:00${this.offsetSuffix}`,
      ticketUrl: `https://example.com/tickets/${movieKey}-${date}-${time}`,
      language,
      cinema,
    };
  }
}

/** Pick `count` distinct items from `items`, in seeded random order. */
function pick<T>(rand: () => number, items: readonly T[], count: number): T[] {
  const pool = [...items];
  const picked: T[] = [];
  while (picked.length < count && pool.length > 0) {
    const item = pool.splice(Math.floor(rand() * pool.length), 1)[0];
    if (item !== undefined) {
      picked.push(item);
    }
  }
  return picked;
}

/** FNV-1a hash of a string, as an unsigned 32-bit integer. */
function hashString(input: string): number {
  let hash = 2166136261;
  for (let index = 0; index < input.length; index++) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

/** Deterministic 32-bit PRNG (mulberry32); same seed, same sequence. */
function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function toDateString(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(date: string, days: number): string {
  const parts = date.split("-").map(Number);
  const value = new Date(
    parts[0] ?? 0,
    (parts[1] ?? 1) - 1,
    (parts[2] ?? 1) + days,
  );
  return toDateString(value);
}

function localOffsetSuffix(date: Date): string {
  const minutes = -date.getTimezoneOffset();
  const sign = minutes >= 0 ? "+" : "-";
  const absolute = Math.abs(minutes);
  const hours = String(Math.floor(absolute / 60)).padStart(2, "0");
  const rest = String(absolute % 60).padStart(2, "0");
  return `${sign}${hours}:${rest}`;
}
