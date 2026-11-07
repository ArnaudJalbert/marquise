import type { ReactNode } from "react";
export interface CatalogueCinema {
  id: string;
  name: string;
  address?: string;
  website?: string;
}
export interface CatalogueScreening {
  showtime: string;
  cinemaId: string;
  date: string;
  time: string;
  language?: string;
  bookingUrl?: string;
  cinemaName?: string;
}
export interface CatalogueMovie {
  id: string;
  title: string;
  poster?: string;
  year?: number;
  director?: string;
  runtime?: number;
  tmdbRating?: number | null;
  tmdbVoteCount?: number | null;
  synopsis?: string;
  screenings: readonly CatalogueScreening[];
}
export type CatalogueState =
  | "ready"
  | "initial-loading"
  | "loading-more"
  | "empty"
  | "error";
export interface CatalogueSelection {
  start: string;
  end: string;
  title: string;
  cinemas: string[];
  languages: string[];
  from: string;
  to: string;
}
export interface MinimalCatalogueProps {
  currentTime?: string;
  movies: readonly CatalogueMovie[];
  catalogueMovies?: readonly CatalogueMovie[];
  catalogueNotice?: string;
  /** Server results have already been filtered, ordered and bounded. */
  serverResults?: boolean;
  showScreeningFilters?: boolean;
  catalogueSearch?: string;
  onCatalogueSearch?: (title: string) => void;
  catalogueState?: CatalogueState;
  catalogueHasMore?: boolean;
  onLoadMoreCatalogue?: () => void;
  onCatalogueRetry?: () => void;
  detailNotice?: ReactNode;
  directoryNotice?: ReactNode;
  cinemas: readonly CatalogueCinema[];
  screeningLanguages: readonly string[];
  selection: CatalogueSelection;
  onSelection: (selection: CatalogueSelection) => void;
  href: string;
  navigate: (href: string) => void;
  today: string;
  state?: CatalogueState;
  hasMore?: boolean;
  onLoadMore?: () => void;
  onRetry: () => void;
  /** Loads a movies section card's upcoming screenings when its preview first opens. */
  onLoadUpcomingScreenings?: (
    movie: CatalogueMovie,
    signal: AbortSignal,
  ) => Promise<CatalogueScreening[]>;
  onLoadWeek?: (
    movie: CatalogueMovie,
    start: string,
    end: string,
    signal?: AbortSignal,
  ) => Promise<{
    screenings: CatalogueScreening[];
    cinemas: CatalogueCinema[];
  }>;
}
