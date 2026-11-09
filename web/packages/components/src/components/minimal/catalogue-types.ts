import type { ReactNode } from "react";
import type { CatalogueTimeFilterValue } from "./catalogue-time-filters";
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
export interface CatalogueSelection<
  FilterType extends CatalogueFilterType = CatalogueFilterType,
> {
  start: string;
  end: string;
  title: string;
  filters: CatalogueFilter<FilterType>[];
}
export type CatalogueFilterType = "cinema" | "time" | "audio" | "subtitles";
export type ActiveCatalogueFilterType = "cinema" | "time";
export const ACTIVE_CATALOGUE_FILTER_TYPES: readonly ActiveCatalogueFilterType[] = [
  "cinema",
  "time",
];
export type ActiveCatalogueSelection = CatalogueSelection<ActiveCatalogueFilterType>;
export type ActiveCatalogueFilter = CatalogueFilter<ActiveCatalogueFilterType>;
export type CatalogueFilter<FilterType extends CatalogueFilterType = CatalogueFilterType> = {
  [Type in FilterType]: {
    type: Type;
    value: Type extends "time" ? CatalogueTimeFilterValue : string;
    operator: "is" | "is_not";
  };
}[FilterType];
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
  selection: ActiveCatalogueSelection;
  onSelection: (selection: ActiveCatalogueSelection) => void;
  /** Counts the movies a draft selection would show, before it is applied. */
  onCountMovies?: (selection: ActiveCatalogueSelection, signal: AbortSignal) => Promise<number>;
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
