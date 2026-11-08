export {
  MinimalCatalogue,
  MinimalMovieCard,
} from "./components/minimal/MinimalCatalogue";
export type {
  ActiveCatalogueFilter,
  ActiveCatalogueSelection,
  CatalogueMovie,
  CatalogueCinema,
  CatalogueScreening,
  CatalogueFilter,
  CatalogueFilterType,
  ActiveCatalogueFilterType,
  CatalogueSelection,
  CatalogueState,
  MinimalCatalogueProps,
} from "./components/minimal/MinimalCatalogue";
import "./index.css";
export { MarquiseExperience } from "./components/discovery/MarquiseExperience";
export { PosterCard, PosterRail } from "./components/discovery/PosterCard";
export {
  screeningQuery,
  screeningsHref,
} from "./components/discovery/discovery-state";

export { MovieCard } from "./components/movie/MovieCard";
export { MovieCardGrid } from "./components/movie/MovieCardGrid";
export { MovieDetailPage } from "./components/movie/MovieDetailPage";
export { MovieFilterPanel } from "./components/movie/MovieFilterPanel";
export { MovieGridController } from "./components/movie/MovieGridController";
export { useMovieFilters } from "./components/movie/use-movie-filters";
export { filterMovieGridItems } from "./components/movie/movie-grid-filter";
export { DateSelector } from "./components/movie/date-selector";
export { formatDateLabel } from "./components/movie/date-selector";
export {
  CinemaShowtimeGroups,
  groupByCinema,
} from "./components/movie/CinemaShowtimes";
export type {
  Cinema,
  CinemaShowtime,
  CinemaShowtimeGroup,
  MovieCardData,
  MovieDetailClient,
  MovieGridClient,
} from "marquise-client";
export type { MovieCardProps } from "./components/movie/movie-card";
export type {
  MovieCardGridItem,
  MovieCardGridProps,
} from "./components/movie/movie-card-grid";
export type { MovieDetailPageProps } from "./components/movie/MovieDetailPage";
export type { MovieFilterPanelProps } from "./components/movie/MovieFilterPanel";
export type { MovieGridControllerProps } from "./components/movie/MovieGridController";
export type { MovieFilters } from "./components/movie/movie-grid-filter";
export type {
  MovieFilterOptions,
  UseMovieFiltersResult,
} from "./components/movie/use-movie-filters";
export { Button, buttonVariants } from "./components/ui/button";
export { Card, CardContent } from "./components/ui/card";
export { cn } from "./lib/utils";

export { MinimalExperience } from "./components/minimal/MinimalExperience";
