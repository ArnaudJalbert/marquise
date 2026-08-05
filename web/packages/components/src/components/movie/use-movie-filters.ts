import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { MovieCardGridItem } from "./movie-card-grid";
import type { MovieGridClient } from "./movie-grid-client";
import {
  DEFAULT_MOVIE_FILTERS,
  filterMovieGridItems,
  type MovieFilters,
} from "./movie-grid-filter";

/** The distinct filter values present in a date's items. */
export interface MovieFilterOptions {
  cinemas: readonly string[];
  genres: readonly string[];
  languages: readonly string[];
}

function deriveOptions(
  items: readonly MovieCardGridItem[],
): MovieFilterOptions {
  const cinemas = new Set<string>();
  const genres = new Set<string>();
  const languages = new Set<string>();
  for (const item of items) {
    for (const genre of item.movie.genres ?? []) {
      genres.add(genre);
    }
    for (const showtime of item.showtimes ?? []) {
      cinemas.add(showtime.cinema.name);
      if (showtime.language) {
        languages.add(showtime.language);
      }
    }
  }
  return {
    cinemas: [...cinemas].sort(),
    genres: [...genres].sort(),
    languages: [...languages].sort(),
  };
}

export interface UseMovieFiltersResult {
  /** Selectable dates, as "YYYY-MM-DD" strings. */
  dates: readonly string[];
  /** True until the dates and the first selected date's data have loaded. */
  datesLoading: boolean;
  selectedDate: string | null;
  /** True while a date's data is being fetched. */
  isLoading: boolean;
  /** Error message from the last failed load; null while everything is fine. */
  error: string | null;
  /** Re-attempt the last failed load. */
  retry: () => void;
  filters: MovieFilters;
  /** Apply cinema/genre/language/time filters locally — never refetches. */
  updateFilters: (patch: Partial<MovieFilters>) => void;
  /** Select a date. The only action that triggers a client fetch. */
  selectDate: (date: string) => void;
  /** Filter values available on the selected date. */
  options: MovieFilterOptions;
  /** The selected date's items, with every active filter applied locally. */
  items: readonly MovieCardGridItem[];
}

/**
 * Owns the movie grid filter state. Fetches from the client once for the
 * initially selected date and again only when the date changes; cinema, genre,
 * language and time filters are applied locally on the fetched data.
 *
 * The `client` must stay referentially stable across renders (pass a module or
 * state-scoped instance); it is read through a ref so a changing identity does
 * not refetch or re-run effects.
 */
export function useMovieFilters(
  client: MovieGridClient,
  initialDate?: string,
): UseMovieFiltersResult {
  const [dates, setDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [items, setItems] = useState<MovieCardGridItem[]>([]);
  const [filters, setFilters] = useState<MovieFilters>(DEFAULT_MOVIE_FILTERS);
  const [isLoading, setIsLoading] = useState(false);
  const [datesLoading, setDatesLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [datesRetryNonce, setDatesRetryNonce] = useState(0);
  const [fetchRetryNonce, setFetchRetryNonce] = useState(0);
  const requestIdRef = useRef(0);
  const clientRef = useRef(client);
  const datesRef = useRef(dates);

  useEffect(() => {
    clientRef.current = client;
  });
  useEffect(() => {
    datesRef.current = dates;
  }, [dates]);

  useEffect(() => {
    let stale = false;
    setDatesLoading(true);
    setError(null);
    clientRef.current
      .listDates()
      .then((available) => {
        if (stale) {
          return;
        }
        setDates([...available]);
        setSelectedDate((current) => {
          if (current !== null) {
            return current;
          }
          return available.find((date) => date === initialDate) ?? available[0] ?? null;
        });
        if (available.length === 0) {
          setDatesLoading(false);
        }
      })
      .catch(() => {
        if (stale) {
          return;
        }
        setDatesLoading(false);
        setError("Could not load the available dates.");
      });
    return () => {
      stale = true;
    };
  }, [initialDate, datesRetryNonce]);

  useEffect(() => {
    if (selectedDate === null) {
      return;
    }
    let stale = false;
    const requestId = ++requestIdRef.current;
    setIsLoading(true);
    setError(null);
    clientRef.current
      .fetchForDate(selectedDate)
      .then((fetched) => {
        if (stale || requestId !== requestIdRef.current) {
          return;
        }
        setItems([...fetched]);
        const options = deriveOptions(fetched);
        setFilters((current) => ({
          ...current,
          cinemas: current.cinemas.filter((name) => options.cinemas.includes(name)),
          genres: current.genres.filter((genre) => options.genres.includes(genre)),
          languages: current.languages.filter((language) =>
            options.languages.includes(language),
          ),
        }));
        setIsLoading(false);
        setDatesLoading(false);
      })
      .catch(() => {
        if (stale || requestId !== requestIdRef.current) {
          return;
        }
        setIsLoading(false);
        setDatesLoading(false);
        setError("Could not load showtimes for this date.");
      });
    return () => {
      stale = true;
    };
  }, [selectedDate, fetchRetryNonce]);

  const selectDate = useCallback((date: string) => {
    if (datesRef.current.length > 0 && !datesRef.current.includes(date)) {
      return;
    }
    setSelectedDate(date);
  }, []);

  const updateFilters = useCallback((patch: Partial<MovieFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
  }, []);

  const retry = useCallback(() => {
    setDatesRetryNonce((nonce) => nonce + 1);
    setFetchRetryNonce((nonce) => nonce + 1);
  }, []);

  const options = useMemo(() => deriveOptions(items), [items]);

  const filteredItems = useMemo(
    () => filterMovieGridItems(items, filters),
    [items, filters],
  );

  return {
    dates,
    datesLoading,
    selectedDate,
    isLoading,
    error,
    retry,
    filters,
    updateFilters,
    selectDate,
    options,
    items: filteredItems,
  };
}
