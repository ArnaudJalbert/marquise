import "./index.css";

export { MovieCard } from "./components/movie/MovieCard";
export { MovieCardGrid } from "./components/movie/MovieCardGrid";
export {
  CinemaShowtimeGroups,
  groupByCinema,
} from "./components/movie/CinemaShowtimes";
export type { Cinema, CinemaShowtime, CinemaShowtimeGroup } from "./components/movie/cinema";
export type { MovieCardData } from "./components/movie/movie";
export type { MovieCardProps } from "./components/movie/movie-card";
export type { MovieCardGridItem, MovieCardGridProps } from "./components/movie/movie-card-grid";
export { Badge, badgeVariants } from "./components/ui/badge";
export { Button, buttonVariants } from "./components/ui/button";
export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
} from "./components/ui/card";
export { Separator } from "./components/ui/separator";
export { cn } from "./lib/utils";
