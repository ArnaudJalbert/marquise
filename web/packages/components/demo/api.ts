import type { CatalogueMovie } from "marquise-components";
import {
  HttpMarquiseClient,
  posterRenditionUrl,
  toMontrealIsoDate,
  type Page,
} from "marquise-client";

async function readPages<T>(
  fetchPage: (page: number) => Promise<Page<T>>,
): Promise<T[]> {
  const first = await fetchPage(1);
  const items = [...first.items];
  for (let page = 2; page <= first.pages; page += 1) {
    items.push(...(await fetchPage(page)).items);
  }
  return items;
}

export async function loadAllMovies(
  client: HttpMarquiseClient,
  signal: AbortSignal,
): Promise<CatalogueMovie[]> {
  // shortcut: local prototype search loads the catalogue; #336 requires bounded production paging.
  const items = await readPages((page) => client.fetchMoviePage(page, signal));
  return items.map((item) => ({
    id: item.id,
    title: item.title,
    poster: posterRenditionUrl(item.poster_url) ?? undefined,
    year: item.release_year ?? undefined,
    director: item.directors?.join(", ") ?? undefined,
    runtime: item.duration_minutes ?? undefined,
    tmdbRating: item.tmdb_rating,
    tmdbVoteCount: item.tmdb_vote_count,
    synopsis: item.description ?? undefined,
    screenings: [],
  }));
}

export async function loadMovieWeek(
  client: HttpMarquiseClient,
  movie: CatalogueMovie,
  start: string,
  end: string,
  signal?: AbortSignal,
) {
  const items = await readPages((page) =>
    client.fetchScreeningRangePage(movie.id, start, end, page, signal),
  );
  const timeFormatter = new Intl.DateTimeFormat("en-GB", {
    timeZone: "America/Toronto",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
  return {
    screenings: items.map((item) => ({
      cinemaId: item.cinema_id,
      cinemaName: item.cinema_name,
      date: toMontrealIsoDate(new Date(item.showtime)),
      time: timeFormatter.format(new Date(item.showtime)),
      language: item.language ?? undefined,
      bookingUrl: item.ticket_url ?? undefined,
    })),
    cinemas: [
      ...new Map(
        items.map((item) => [
          item.cinema_id,
          { id: item.cinema_id, name: item.cinema_name },
        ]),
      ).values(),
    ],
  };
}
