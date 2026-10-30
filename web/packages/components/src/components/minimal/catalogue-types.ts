export interface CatalogueCinema {
  id: string;
  name: string;
  address?: string;
  website?: string;
}
export interface CatalogueScreening {
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
  movies: readonly CatalogueMovie[];
  catalogueMovies?: readonly CatalogueMovie[];
  catalogueNotice?: string;
  cinemas: readonly CatalogueCinema[];
  screeningLanguages: readonly string[];
  selection: CatalogueSelection;
  onSelection: (selection: CatalogueSelection) => void;
  href: string;
  navigate: (href: string) => void;
  today: string;
  tomorrow: string;
  weekend: readonly [string, string];
  state?: CatalogueState;
  onRetry: () => void;
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
