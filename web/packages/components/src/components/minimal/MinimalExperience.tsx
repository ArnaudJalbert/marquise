import { useCallback, useState } from "react";
import {
  MovieNotFoundError,
  posterRenditionUrl,
  toMontrealIsoDate,
  type BrowseClient,
  type MovieApi,
  type ScreeningApi,
} from "marquise-client";
import { useResource } from "../discovery/use-resource";
import { MinimalCatalogue } from "./MinimalCatalogue";
import { addDays, decodePathId } from "./catalogue-format";
import type {
  CatalogueMovie,
  CatalogueScreening,
  CatalogueState,
  MinimalCatalogueProps,
} from "./catalogue-types";

const timeFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: "America/Montreal",
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
    synopsis: item.description ?? undefined,
    screenings: [],
  };
}

function resourceState(resource: {
  loading: boolean;
  error?: Error;
}): CatalogueState {
  return resource.loading
    ? "initial-loading"
    : resource.error
      ? "error"
      : "ready";
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
  const isScreenings = isListing && !isCatalogue;
  const movieId = /^\/movies\/([^/]+)$/.exec(url.pathname)?.[1];
  const decodedId = movieId ? decodePathId(movieId) : undefined;
  const [search, setSearch] = useState("");

  const screenings = useResource(
    useCallback(
      (signal: AbortSignal) =>
        client.fetchScreeningMoviesPage(
          { start: today, end: today, page: 1 },
          signal,
        ),
      [client, today],
    ),
    isScreenings,
  );
  const catalogue = useResource(
    useCallback(
      (signal: AbortSignal) =>
        client.fetchMoviePage(1, signal, search.trim() || undefined, 24),
      [client, search],
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
        screenings: items.map(screeningData),
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
  const movies = (screenings.data?.items ?? []).map((item) => ({
    ...movieData(item),
    screenings: item.screenings.map(screeningData),
  }));
  const catalogueMovies = decodedId
    ? detail.data
      ? [detail.data]
      : []
    : (catalogue.data?.items ?? []).map(movieData);
  const cinemas = [
    ...new Map(
      movies.flatMap((movie) =>
        movie.screenings.map(
          (item) =>
            [
              item.cinemaId,
              {
                id: item.cinemaId,
                name: item.cinemaName ?? "Cinema unavailable",
              },
            ] as const,
        ),
      ),
    ).values(),
  ];

  return (
    <MinimalCatalogue
      movies={decodedId ? [] : movies}
      catalogueMovies={catalogueMovies}
      serverResults
      showScreeningFilters={false}
      catalogueSearch={search}
      onCatalogueSearch={setSearch}
      catalogueState={resourceState(catalogue)}
      onCatalogueRetry={catalogue.retry}
      cinemas={url.pathname.startsWith("/cinemas") ? [] : cinemas}
      screeningLanguages={[]}
      selection={{
        start: today,
        end: today,
        title: "",
        cinemas: [],
        languages: [],
        from: "",
        to: "",
      }}
      onSelection={() => {}}
      href={href}
      navigate={navigate}
      today={today}
      tomorrow={addDays(today, 1)}
      weekend={[today, today]}
      state={resourceState(screenings)}
      onRetry={screenings.retry}
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
      directoryNotice={<p>Cinema browsing is coming soon.</p>}
    />
  );
}
