import {
  montrealDateTime,
  type MovieApi,
  type Page,
  type ScreeningApi,
} from "marquise-client";
import { cinemas, movies } from "./fixtures.ts";

function pageOf<T>(items: T[], query: URLSearchParams): Page<T> {
  const page = Math.max(1, Math.floor(Number(query.get("page")) || 1));
  const size = Math.min(
    100,
    Math.max(1, Math.floor(Number(query.get("size")) || 100)),
  );
  return {
    items: items.slice((page - 1) * size, page * size),
    total: items.length,
    page,
    size,
    pages: Math.ceil(items.length / size),
  };
}

/** The dev/preview server serves the same REST shapes without a backend. */
export function sampleApiResponse(
  url: URL,
): Page<MovieApi> | Page<ScreeningApi> | undefined {
  const query = url.searchParams;
  if (url.pathname === "/v1/movies") {
    const title = query.get("title")?.toLowerCase() ?? "";
    const ids = query.getAll("ids");
    const items: MovieApi[] = movies
      .filter(
        (movie) =>
          movie.title.toLowerCase().includes(title) &&
          (!ids.length || ids.includes(movie.id)),
      )
      .map((movie) => ({
        id: movie.id,
        title: movie.title,
        release_year: movie.year ?? null,
        directors: movie.director ? [movie.director] : null,
        cast: null,
        duration_minutes: movie.runtime ?? null,
        description: movie.synopsis ?? null,
        poster_url: movie.poster ?? null,
        trailer_url: null,
        genres: null,
        original_title: null,
        rating: null,
        tmdb_rating: movie.tmdbRating ?? null,
        tmdb_vote_count: movie.tmdbVoteCount ?? null,
        origin_countries: null,
      }));
    return pageOf(items, query);
  }
  if (url.pathname === "/v1/screenings") {
    const movieId = query.get("movie_id");
    const from = query.get("from");
    const to = query.get("to");
    const items: ScreeningApi[] = movies
      .filter((movie) => !movieId || movie.id === movieId)
      .flatMap((movie) =>
        movie.screenings.map((screening, index) => ({
          id: `${movie.id}-${index}`,
          movie_id: movie.id,
          movie_title: movie.title,
          cinema_id: screening.cinemaId,
          cinema_name:
            cinemas.find((cinema) => cinema.id === screening.cinemaId)?.name ??
            "Cinema",
          showtime: montrealDateTime(screening.date, screening.time),
          ticket_url: screening.bookingUrl ?? null,
          room: null,
          language: screening.language ?? null,
        })),
      )
      .filter(
        (screening) =>
          (!from || Date.parse(screening.showtime) >= Date.parse(from)) &&
          (!to || Date.parse(screening.showtime) <= Date.parse(to)),
      )
      .sort(
        (a, b) =>
          a.showtime.localeCompare(b.showtime) || a.id.localeCompare(b.id),
      );
    return pageOf(items, query);
  }
  return undefined;
}
