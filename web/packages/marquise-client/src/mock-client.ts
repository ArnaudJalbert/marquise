import type {
  DiscoveryClient,
  ScreeningQuery,
  ScreeningPage,
} from "./discovery-client";
import type { CinemaApi, Page } from "./api-types";
import type { Cinema, CinemaShowtime } from "./cinema";
import type { MovieCardData } from "./movie";
import {
  MovieNotFoundError,
  type MovieDetailClient,
} from "./movie-detail-client";
import type { MovieCardGridItem, MovieGridClient } from "./movie-grid-client";
import {
  MONTREAL_TIME_ZONE,
  addDays,
  montrealDateTime,
  toMontrealIsoDate,
} from "./montreal-date";

export interface MockMarquiseClientOptions {
  /** First selectable date as "YYYY-MM-DD"; defaults to today in Montréal. */
  startDate?: string;
  /** Number of selectable days; defaults to 7. */
  days?: number;
}

interface MockMovie {
  key: string;
  title: string;
  releaseYear: number;
  durationMinutes: number;
  tmdbRating: number;
  tmdbVoteCount: number;
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
    tmdbRating: 8.3,
    tmdbVoteCount: 3818,
    directors: ["Denis Villeneuve"],
    genres: ["Sci-Fi", "Drama"],
    posterUrl:
      "https://image.tmdb.org/t/p/original/cgXk2tNYhJZLXdBDO5DidAVzQ82.jpg",
  },
  {
    key: "anora",
    title: "Anora",
    releaseYear: 2024,
    durationMinutes: 139,
    tmdbRating: 7.3,
    tmdbVoteCount: 3197,
    directors: ["Sean Baker"],
    genres: ["Drama", "Comedy"],
  },
  {
    key: "brutalist",
    title: "The Brutalist",
    releaseYear: 2024,
    durationMinutes: 215,
    tmdbRating: 8.1,
    tmdbVoteCount: 4945,
    directors: ["Brady Corbet"],
    genres: ["Drama"],
  },
  {
    key: "nosferatu",
    title: "Nosferatu",
    releaseYear: 2024,
    durationMinutes: 132,
    tmdbRating: 8.3,
    tmdbVoteCount: 3036,
    directors: ["Robert Eggers"],
    genres: ["Horror", "Drama"],
  },
  {
    key: "substance",
    title: "The Substance",
    releaseYear: 2024,
    durationMinutes: 141,
    tmdbRating: 7.5,
    tmdbVoteCount: 3243,
    directors: ["Coralie Fargeat"],
    genres: ["Horror", "Comedy"],
  },
  {
    key: "a-real-pain",
    title: "A Real Pain",
    releaseYear: 2024,
    durationMinutes: 90,
    tmdbRating: 7.5,
    tmdbVoteCount: 2070,
    directors: ["Jesse Eisenberg"],
    genres: ["Comedy", "Drama"],
  },
  {
    key: "challengers",
    title: "Challengers",
    releaseYear: 2024,
    durationMinutes: 131,
    tmdbRating: 8.2,
    tmdbVoteCount: 3013,
    directors: ["Luca Guadagnino"],
    genres: ["Drama", "Romance"],
  },
  {
    key: "kinds-of-kindness",
    title: "Kinds of Kindness",
    releaseYear: 2024,
    durationMinutes: 164,
    tmdbRating: 8.1,
    tmdbVoteCount: 3772,
    directors: ["Yorgos Lanthimos"],
    genres: ["Comedy", "Drama"],
  },
  {
    key: "zone-of-interest",
    title: "The Zone of Interest",
    releaseYear: 2023,
    durationMinutes: 105,
    tmdbRating: 7.3,
    tmdbVoteCount: 2415,
    directors: ["Jonathan Glazer"],
    genres: ["Drama", "History"],
  },
  {
    key: "perfect-days",
    title: "Perfect Days",
    releaseYear: 2023,
    durationMinutes: 123,
    tmdbRating: 7.4,
    tmdbVoteCount: 2829,
    directors: ["Wim Wenders"],
    genres: ["Drama"],
  },
  {
    key: "emilia-perez",
    title: "Emilia Pérez",
    releaseYear: 2024,
    durationMinutes: 132,
    tmdbRating: 8.3,
    tmdbVoteCount: 3036,
    directors: ["Jacques Audiard"],
    genres: ["Musical", "Drama"],
  },
  {
    key: "furiosa",
    title: "Furiosa: A Mad Max Saga",
    releaseYear: 2024,
    durationMinutes: 148,
    tmdbRating: 8.2,
    tmdbVoteCount: 3404,
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

/** Deterministic demo client shared by movie grids and detail pages. */
export class MockMarquiseClient
  implements MovieGridClient, MovieDetailClient, DiscoveryClient
{
  async fetchCinemaPage(
    page: number,
    _signal?: AbortSignal,
    name?: string,
  ): Promise<Page<CinemaApi>> {
    const cinemas = CINEMAS.filter(
      (cinema) =>
        !name || cinema.name.toLowerCase().includes(name.toLowerCase()),
    );
    return {
      items:
        page === 1
          ? cinemas.map((c) => ({
              id: c.id,
              name: c.name,
              address: null,
              city: "Montréal",
              website: c.link,
            }))
          : [],
      page,
      size: 100,
      total: cinemas.length,
      pages: Math.ceil(cinemas.length / 100),
    };
  }
  async fetchScreeningPage(query: ScreeningQuery): Promise<ScreeningPage> {
    const rows = (await this.fetchForDate(query.date))
      .flatMap((item) =>
        (item.showtimes ?? []).map((showtime) => ({ item, showtime })),
      )
      .filter(({ item, showtime }) => {
        const time = new Intl.DateTimeFormat("en-GB", {
          timeZone: MONTREAL_TIME_ZONE,
          hour: "2-digit",
          minute: "2-digit",
          hourCycle: "h23",
        }).format(new Date(showtime.startsAt));
        return (
          (!query.movie ||
            item.movie.title
              .toLowerCase()
              .includes(query.movie.toLowerCase())) &&
          (!query.movieId || query.movieId === item.movie.id) &&
          (!query.cinemaId || query.cinemaId === showtime.cinema.id) &&
          (!query.language || query.language === showtime.language) &&
          (!query.fromTime || time >= query.fromTime) &&
          (!query.toTime || time <= query.toTime)
        );
      });
    const size = query.size ?? 48;
    const visible = rows.slice((query.page - 1) * size, query.page * size);
    const ids = [...new Set(visible.map(({ item }) => item.movie.id))];
    return {
      items: ids.flatMap((id) => {
        const first = visible.find(({ item }) => item.movie.id === id);
        return first
          ? [
              {
                ...first.item,
                showtimes: visible
                  .filter(({ item }) => item.movie.id === id)
                  .map(({ showtime }) => showtime),
              },
            ]
          : [];
      }),
      page: query.page,
      size,
      total: rows.length,
      pages: Math.ceil(rows.length / size),
      screeningCount: visible.length,
    };
  }
  async fetchShowtimePage(
    movieId: string,
    date: string,
    page: number,
  ): Promise<Page<CinemaShowtime>> {
    const result = await this.fetchScreeningPage({ date, movieId, page });
    return {
      ...result,
      items: result.items.flatMap((item) => item.showtimes ?? []),
    };
  }
  private readonly dates: readonly string[];

  constructor(options: MockMarquiseClientOptions = {}) {
    const startDate = options.startDate ?? toMontrealIsoDate(new Date());
    this.dates = Array.from({ length: options.days ?? 7 }, (_, index) =>
      addDays(startDate, index),
    );
  }

  async listDates(): Promise<readonly string[]>;
  async listDates(movie: MovieCardData): Promise<readonly string[]>;
  async listDates(_movie?: MovieCardData): Promise<readonly string[]> {
    return this.dates;
  }

  async fetchForDate(date: string): Promise<readonly MovieCardGridItem[]> {
    return this.dates.includes(date) ? this.itemsForDate(date) : [];
  }

  async fetchMovie(movieId: string): Promise<MovieCardData> {
    const movie = CATALOGUE.find((candidate) => candidate.key === movieId);
    if (movie === undefined) {
      throw new MovieNotFoundError(movieId);
    }
    return {
      id: movie.key,
      title: movie.title,
      posterUrl: movie.posterUrl,
      releaseYear: movie.releaseYear,
      durationMinutes: movie.durationMinutes,
      tmdbRating: movie.tmdbRating,
      tmdbVoteCount: movie.tmdbVoteCount,
      directors: movie.directors,
      genres: movie.genres,
    };
  }

  async fetchShowtimes(
    movie: MovieCardData,
    date: string,
  ): Promise<readonly CinemaShowtime[]> {
    if (!this.dates.includes(date) || movie.id === undefined) {
      return [];
    }
    return (
      this.itemsForDate(date).find((item) => item.movie.id === movie.id)
        ?.showtimes ?? []
    );
  }

  private itemsForDate(date: string): readonly MovieCardGridItem[] {
    const rand = mulberry32(hashString(date));
    const movieCount = 8 + Math.floor(rand() * Math.min(5, CATALOGUE.length));
    return pickDistinct(rand, CATALOGUE, movieCount).map((movie) => ({
      key: movie.key,
      movie: {
        id: movie.key,
        title: movie.title,
        posterUrl: movie.posterUrl,
        releaseYear: movie.releaseYear,
        durationMinutes: movie.durationMinutes,
      tmdbRating: movie.tmdbRating,
      tmdbVoteCount: movie.tmdbVoteCount,
        directors: movie.directors,
        genres: movie.genres,
      },
      showtimesUrl: `/movies/${movie.key}`,
      showtimes: showtimesFor(date, movie.key, rand),
    }));
  }
}

/** Generate a movie's showtimes for a date, consuming the seeded RNG stream. */
function showtimesFor(
  date: string,
  movieKey: string,
  rand: () => number,
): CinemaShowtime[] {
  const showtimeCount = 1 + Math.floor(rand() * 3);
  const cinemas = pickDistinct(rand, CINEMAS, showtimeCount);
  const times = pickDistinct(rand, TIMES, showtimeCount);
  return times.map((time, index) => ({
    startsAt: montrealDateTime(date, time),
    ticketUrl: `https://example.com/tickets/${movieKey}-${date}-${time}`,
    language:
      LANGUAGES[Math.floor(rand() * LANGUAGES.length)] ?? DEFAULT_LANGUAGE,
    cinema: cinemas[index] ?? CINEMA_MODERNE,
  }));
}

/** Pick `count` distinct items from `items`, in seeded random order. */
function pickDistinct<T>(
  rand: () => number,
  items: readonly T[],
  count: number,
): T[] {
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
