import { useCallback, useEffect, useRef, useState } from "react";
import {
  Button,
  MovieDetailPage,
  MovieGridController,
  type MovieCardData,
  type MovieDetailClient,
  type MovieFilters,
  type MovieGridClient,
} from "marquise-components";
import { MovieNotFoundError } from "marquise-client";

import { createMovieDetailClient, createMovieGridClient } from "./api-client";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";
import {
  movieDateFromUrl,
  movieUrl,
  parseListingsUrl,
  parseRoute,
  serializeListingsUrl,
  type ListingsUrlState,
} from "./url-state";

const defaultMovieGridClient = createMovieGridClient();
const defaultMovieDetailClient = createMovieDetailClient();
const LISTINGS_TITLE = "Marquise — Montréal movie showtimes";

type LocationSnapshot = {
  href: string;
  restoreKey: number;
};

type MovieCacheEntry = MovieCardData | Promise<MovieCardData>;

export interface AppProps {
  /** Optional client overrides used by tests and embedded builds. */
  movieGridClient?: MovieGridClient;
  movieDetailClient?: MovieDetailClient;
}

function MovieRoute({
  movieId,
  initialDate,
  client,
  loadMovie,
  onBack,
  onDateChange,
}: {
  movieId: string;
  initialDate?: string;
  client: MovieDetailClient;
  loadMovie: (movieId: string, refresh?: boolean) => Promise<MovieCardData>;
  onBack: () => void;
  onDateChange: (date: string) => void;
}) {
  const [movie, setMovie] = useState<MovieCardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);

  useEffect(() => {
    let stale = false;
    setLoading(true);
    setError(null);
    loadMovie(movieId, retryNonce > 0)
      .then((loaded) => {
        if (stale) return;
        setMovie(loaded);
        setLoading(false);
        document.title = `${loaded.title} — Marquise`;
      })
      .catch((caught: unknown) => {
        if (stale) return;
        setMovie(null);
        setLoading(false);
        const notFound = caught instanceof MovieNotFoundError;
        setError(notFound ? "Movie not found." : "Could not load this movie.");
        document.title = notFound
          ? "Movie not found — Marquise"
          : "Movie unavailable — Marquise";
      });
    return () => {
      stale = true;
    };
  }, [loadMovie, movieId, retryNonce]);

  if (loading) {
    return (
      <div className="flex min-h-48 flex-col items-center justify-center gap-4" role="status">
        <div className="h-1 w-full max-w-xs overflow-hidden rounded-full bg-muted">
          <div className="animate-loading-bar h-full w-1/3 rounded-full bg-foreground" />
        </div>
        <span className="text-sm text-muted-foreground">Loading movie…</span>
      </div>
    );
  }

  if (error !== null || movie === null) {
    return (
      <div className="flex min-h-48 flex-col items-center justify-center gap-3" role="alert">
        <span className="text-sm text-muted-foreground">
          {error ?? "Movie not found."}
        </span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setRetryNonce((value) => value + 1)}>
            Retry
          </Button>
          <Button variant="ghost" size="sm" onClick={onBack}>
            Back to listings
          </Button>
        </div>
      </div>
    );
  }

  return (
    <MovieDetailPage
      className="h-full w-full overflow-y-auto"
      movie={movie}
      client={client}
      initialDate={initialDate}
      currentTime={new Date().toISOString()}
      onDateChange={(date) => onDateChange(date)}
      onBack={onBack}
    />
  );
}

export function App({
  movieGridClient = defaultMovieGridClient,
  movieDetailClient = defaultMovieDetailClient,
}: AppProps) {
  const [locationSnapshot, setLocationSnapshot] = useState<LocationSnapshot>(() => ({
    href: window.location.href,
    restoreKey: 0,
  }));
  const url = new URL(locationSnapshot.href);
  const route = parseRoute(url.pathname);
  const listingsState = parseListingsUrl(url);
  const listingsStateRef = useRef(listingsState);
  listingsStateRef.current = listingsState;
  const movieCacheRef = useRef<Map<string, MovieCacheEntry>>(new Map());

  useEffect(() => {
    const handlePopState = () => {
      setLocationSnapshot((current) => ({
        href: window.location.href,
        restoreKey: current.restoreKey + 1,
      }));
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (route.kind === "listings") document.title = LISTINGS_TITLE;
  }, [route.kind]);

  const commitUrl = useCallback(
    (nextUrl: URL, mode: "push" | "replace", state: unknown = history.state) => {
      const nextHref = nextUrl.href;
      if (nextHref === window.location.href && mode === "replace") return;
      if (mode === "push") {
        history.pushState(state, "", nextUrl);
      } else {
        history.replaceState(state, "", nextUrl);
      }
      setLocationSnapshot((current) => ({ ...current, href: nextHref }));
    },
    [],
  );

  const updateListings = useCallback(
    (
      update: (current: ListingsUrlState) => ListingsUrlState,
      mode: "push" | "replace",
    ) => {
      const next = update(listingsStateRef.current);
      listingsStateRef.current = next;
      commitUrl(
        serializeListingsUrl(new URL(window.location.href), next),
        mode,
      );
    },
    [commitUrl],
  );

  const loadMovie = useCallback(
    (movieId: string, refresh = false): Promise<MovieCardData> => {
      if (refresh) movieCacheRef.current.delete(movieId);
      const cached = movieCacheRef.current.get(movieId);
      if (cached !== undefined) return Promise.resolve(cached);
      const request = movieDetailClient.fetchMovie(movieId).then(
        (movie) => {
          movieCacheRef.current.set(movieId, movie);
          return movie;
        },
        (error: unknown) => {
          movieCacheRef.current.delete(movieId);
          throw error;
        },
      );
      movieCacheRef.current.set(movieId, request);
      return request;
    },
    [movieDetailClient],
  );

  const openMovie = useCallback(
    (movie: MovieCardData) => {
      if (movie.id === undefined) return;
      movieCacheRef.current.set(movie.id, movie);
      const returnTo = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      commitUrl(movieUrl(movie.id, listingsStateRef.current.date), "push", {
        marquiseReturnTo: returnTo,
      });
    },
    [commitUrl],
  );

  const backToListings = useCallback(() => {
    const state = history.state as { marquiseReturnTo?: unknown } | null;
    if (typeof state?.marquiseReturnTo === "string") {
      history.back();
      return;
    }
    const home = new URL(window.location.origin);
    commitUrl(home, "replace", null);
  }, [commitUrl]);

  const updateMovieDate = useCallback(
    (date: string) => {
      if (parseRoute(window.location.pathname).kind !== "movie") return;
      const next = new URL(window.location.href);
      next.searchParams.set("date", date);
      commitUrl(next, "replace");
    },
    [commitUrl],
  );

  const toggleFilters = useCallback(() => {
    updateListings(
      (current) => ({ ...current, filtersOpen: !current.filtersOpen }),
      "replace",
    );
  }, [updateListings]);

  let content;
  if (route.kind === "movie") {
    content = (
      <MovieRoute
        key={`${route.movieId}-${locationSnapshot.restoreKey}`}
        movieId={route.movieId}
        initialDate={movieDateFromUrl(url)}
        client={movieDetailClient}
        loadMovie={loadMovie}
        onBack={backToListings}
        onDateChange={updateMovieDate}
      />
    );
  } else if (route.kind === "not-found") {
    content = (
      <div className="flex min-h-48 flex-col items-center justify-center gap-3" role="alert">
        <span className="text-sm text-muted-foreground">Page not found.</span>
        <Button variant="outline" size="sm" onClick={backToListings}>
          Go to listings
        </Button>
      </div>
    );
  } else {
    content = (
      <MovieGridController
        key={`listings-${locationSnapshot.restoreKey}`}
        className="h-full w-full"
        client={movieGridClient}
        side="right"
        pageSize="auto"
        currentTime={new Date().toISOString()}
        initialDate={listingsState.date}
        initialFilters={listingsState.filters}
        initialPageIndex={listingsState.pageIndex}
        defaultCardSize={listingsState.cardSize}
        defaultHideDetails={listingsState.hideDetails}
        panelClassName={listingsState.filtersOpen ? undefined : "is-hidden"}
        onSelectedDateChange={(date, reason) =>
          updateListings(
            (current) => ({ ...current, date }),
            reason === "user" ? "push" : "replace",
          )
        }
        onFiltersChange={(filters: MovieFilters) =>
          updateListings((current) => ({ ...current, filters }), "replace")
        }
        onPageIndexChange={(pageIndex, reason) =>
          updateListings(
            (current) => ({ ...current, pageIndex }),
            reason === "user" ? "push" : "replace",
          )
        }
        onCardSizeChange={(cardSize) =>
          updateListings((current) => ({ ...current, cardSize }), "replace")
        }
        onHideDetailsChange={(hideDetails) =>
          updateListings((current) => ({ ...current, hideDetails }), "replace")
        }
        onMovieClick={openMovie}
      />
    );
  }

  return (
    <div className="page-shell">
      <Header
        filtersOpen={listingsState.filtersOpen}
        showFilters={route.kind === "listings"}
        listingsActive={route.kind === "listings"}
        onToggleFilters={toggleFilters}
      />
      <main className="site-main">{content}</main>
      <Footer />
    </div>
  );
}
