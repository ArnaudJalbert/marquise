import { useCallback, useMemo, useRef, useState } from "react";
import {
  MovieNotFoundError,
  posterRenditionUrl,
  toMontrealIsoDate,
  type BrowseClient,
  type HourFilter,
  type MovieApi,
  type ScreeningApi,
} from "marquise-client";
import { useResource } from "../discovery/use-resource";
import { usePageResource } from "../discovery/use-page-resource";
import { MinimalCatalogue } from "./MinimalCatalogue";
import { addDays, decodePathId, timeToHour } from "./catalogue-format";
import type {
  CatalogueMovie,
  CatalogueScreening,
  CatalogueSelection,
  CatalogueState,
  MinimalCatalogueProps,
} from "./catalogue-types";

const timeFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: "America/Toronto",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function screeningData(item: ScreeningApi): CatalogueScreening {
  return {
    cinemaId: item.cinema_id,
    cinemaName: item.cinema_name,
    date: toMontrealIsoDate(new Date(item.showtime)),
    time: timeFormatter.format(new Date(item.showtime)),
    language: item.language ?? undefined,
    bookingUrl: item.ticket_url ?? undefined,
  };
}

function movieData(item: MovieApi): CatalogueMovie {
  return {
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
  };
}

function resourceState(resource: {
  loading: boolean;
  loadingMore: boolean;
  error?: Error;
}): CatalogueState {
  if (resource.loadingMore) return "loading-more";
  if (resource.loading) return "initial-loading";
  if (resource.error) return "error";
  return "ready";
}

const screeningLanguages = ["VO", "VOA", "VOF", "VOSTF", "VOSTA", "VF"];

function parseSelection(url: URL, today: string): CatalogueSelection {
  const params = url.searchParams;
  const start = params.get("start") ?? today;
  const end = params.get("end") ?? start;
  const fromHour = timeToHour(params.get("from") ?? "", 0);
  const toHour = timeToHour(params.get("to") ?? "", 24);
  return {
    start,
    end,
    title: params.get("title") ?? "",
    cinemas: params.getAll("cinema"),
    languages: params.getAll("language"),
    from: fromHour > 0 ? `${String(fromHour).padStart(2, "0")}:00` : "",
    to: toHour < 24 ? `${String(toHour).padStart(2, "0")}:00` : "",
  };
}

function listingHref(href: string, selection: CatalogueSelection): string {
  const url = new URL(href, "http://marquise.invalid");
  const params = url.searchParams;
  for (const key of ["start", "end", "title", "cinema", "language", "from", "to", "page"])
    params.delete(key);
  params.set("start", selection.start);
  params.set("end", selection.end);
  if (selection.title.trim()) params.set("title", selection.title.trim());
  selection.cinemas.forEach((id) => params.append("cinema", id));
  selection.languages.forEach((language) => params.append("language", language));
  if (selection.from) params.set("from", selection.from);
  if (selection.to) params.set("to", selection.to);
  return `${url.pathname}${url.search}${url.hash}`;
}

// shortcut: maps the inclusive hour slider to one half-open range; drop with the slider (#433).
function sliderHours(from: string, to: string): HourFilter | undefined {
  const start = Math.min(from ? timeToHour(from, 0) : 0, 23);
  const end = to ? timeToHour(to, 24) : 24;
  return start === 0 && end === 24
    ? undefined
    : {
        operator: "is",
        ranges: [{ start, end: Math.max(end, start + 1) }],
      };
}

function weekendDates(today: string): [string, string] {
  const weekday = new Date(`${today}T12:00:00Z`).getUTCDay();
  const saturday = addDays(today, weekday === 0 ? -1 : (6 - weekday) % 7);
  return [saturday, addDays(saturday, 1)];
}

/** Production composition of the approved UI with injected, bounded API reads. */
export function MinimalExperience({
  client,
  href,
  navigate,
  currentTime,
}: {
  client: BrowseClient;
  href: string;
  navigate: (href: string) => void;
  currentTime: string;
}) {
  const url = new URL(href, "http://marquise.invalid");
  const today = toMontrealIsoDate(new Date(currentTime));
  const isListing = url.pathname === "/";
  const isCatalogue = isListing && url.searchParams.get("section") === "movies";
  const cinemaMatch = /^\/cinemas\/([^/]+)\/?$/.exec(url.pathname);
  const cinemaId = cinemaMatch?.[1]
    ? decodePathId(cinemaMatch[1])
    : undefined;
  const isCinemaDirectory =
    url.pathname === "/cinemas" || url.pathname === "/cinemas/";
  const isCinemaPage = cinemaId !== undefined;
  const isScreenings = (isListing && !isCatalogue) || isCinemaPage;
  const [screeningsHref, setScreeningsHref] = useState(href);
  if (isScreenings && screeningsHref !== href) setScreeningsHref(href);
  // Detail and catalogue URLs must not replace the retained Screenings query.
  const listingUrl = isScreenings
    ? url
    : new URL(screeningsHref, "http://marquise.invalid");
  const selection = parseSelection(listingUrl, today);
  const fixedCinemaPath = /^\/cinemas\/([^/]+)\/?$/.exec(listingUrl.pathname)?.[1];
  const fixedCinemaId = fixedCinemaPath ? decodePathId(fixedCinemaPath) : undefined;
  const clock = useRef(currentTime);
  clock.current = currentTime;
  const movieId = /^\/movies\/([^/]+)$/.exec(url.pathname)?.[1];
  const decodedId = movieId ? decodePathId(movieId) : undefined;
  const [search, setSearch] = useState("");

  const onSelection = useCallback(
    (next: CatalogueSelection) => navigate(listingHref(href, next)),
    [href, navigate],
  );

  const screenings = usePageResource(
    useCallback(
      (page: number, signal: AbortSignal) =>
        client.fetchScreeningMoviesPage(
          {
            start: selection.start,
            end: selection.end,
            page,
            title: selection.title,
            cinemas: fixedCinemaId ? [fixedCinemaId] : selection.cinemas,
            languages: selection.languages,
            hours: sliderHours(selection.from, selection.to),
          },
          signal,
        ),
      [
        client,
        selection.start,
        selection.end,
        selection.title,
        selection.cinemas.join("\0"),
        selection.languages.join("\0"),
        selection.from,
        selection.to,
        fixedCinemaId,
      ],
    ),
    isScreenings &&
      selection.start <= selection.end &&
      (!selection.from || !selection.to || selection.from <= selection.to),
  );
  const cinemaResource = useResource(
    useCallback(async (signal: AbortSignal) => {
      const first = await client.fetchCinemaPage(1, signal);
      const items = [...first.items];
      for (let page = 2; page <= first.pages; page++) {
        if (signal.aborted) throw new DOMException("Aborted", "AbortError");
        items.push(...(await client.fetchCinemaPage(page, signal)).items);
      }
      return items;
    }, [client]),
      isScreenings || isCinemaDirectory,
  );
  const catalogue = usePageResource(
    useCallback(
      (page: number, signal: AbortSignal) =>
        client.fetchScreeningMoviesPage(
          { start: today, page, title: search.trim() || undefined },
          signal,
        ),
      [client, search, today],
    ),
    isCatalogue,
  );
  const detail = useResource(
    useCallback(
      async (signal: AbortSignal) =>
        decodedId
          ? movieData(await client.fetchMovieMetadata(decodedId, signal))
          : undefined,
      [client, decodedId],
    ),
  );
  const loadWeek = useCallback<
    NonNullable<MinimalCatalogueProps["onLoadWeek"]>
  >(
    async (movie, start, end, signal) => {
      const requestTime = Date.parse(clock.current);
      const first = await client.fetchScreeningRangePage(
        movie.id,
        start,
        end,
        1,
        signal,
      );
      const items = [...first.items];
      for (let page = 2; page <= first.pages; page++) {
        if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
        items.push(
          ...(
            await client.fetchScreeningRangePage(
              movie.id,
              start,
              end,
              page,
              signal,
            )
          ).items,
        );
      }
      return {
        screenings: items
          .filter((item) => Date.parse(item.showtime) > requestTime)
          .map(screeningData),
        cinemas: [
          ...new Map(
            items.map((item) => [
              item.cinema_id,
              {
                id: item.cinema_id,
                name: item.cinema_name,
              },
            ]),
          ).values(),
        ],
      };
    },
    [client],
  );
  const movies = useMemo(
    () =>
      screenings.items.map((item) => ({
        ...movieData(item),
        screenings: item.screenings.map(screeningData),
      })),
    [screenings.items],
  );
  const catalogueMovies = useMemo(
    () =>
      decodedId
        ? detail.data
          ? [detail.data]
          : []
        : catalogue.items.map(movieData),
    [catalogue.items, decodedId, detail.data],
  );
  const cinemas = useMemo(
    () =>
      (cinemaResource.data ?? []).map(({ id, name, address, website }) => ({
        id,
        name,
        address: address ?? undefined,
        website: website ?? undefined,
      })),
    [cinemaResource.data],
  );

  return (
    <MinimalCatalogue
      movies={decodedId ? [] : movies}
      catalogueMovies={catalogueMovies}
      serverResults
      catalogueSearch={search}
      onCatalogueSearch={setSearch}
      catalogueState={resourceState(catalogue)}
      catalogueHasMore={catalogue.hasMore}
      onLoadMoreCatalogue={catalogue.loadNext}
      onCatalogueRetry={catalogue.retry}
      cinemas={cinemas}
      screeningLanguages={screeningLanguages}
      selection={selection}
      onSelection={onSelection}
      href={href}
      navigate={navigate}
      today={today}
      tomorrow={addDays(today, 1)}
      weekend={weekendDates(today)}
      state={resourceState(screenings)}
      onRetry={screenings.retry}
      hasMore={screenings.hasMore}
      onLoadMore={screenings.loadNext}
      onLoadWeek={loadWeek}
      detailNotice={
        detail.loading ? (
          <p role="status">Loading movie…</p>
        ) : detail.error instanceof MovieNotFoundError ? (
          <h1>Movie not found</h1>
        ) : (
          <div role="alert">
            <p>Could not load movie.</p>
            <button onClick={detail.retry}>Retry</button>
          </div>
        )
      }
      directoryNotice={
        cinemaResource.loading ? (
          <p role="status">Loading cinemas…</p>
        ) : cinemaResource.error ? (
          <div role="alert">
            <p>Could not load cinemas.</p>
            <button onClick={cinemaResource.retry}>Retry</button>
          </div>
        ) : cinemas.length === 0 ? (
          <p role="status">No cinemas found.</p>
        ) : null
      }
    />
  );
}
