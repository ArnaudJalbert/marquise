import { PosterEditorialCard } from './PosterEditorialCard';
import type { PosterMovie } from './types';
import './PosterEditorialGrid.css';

export interface PosterEditorialGridProps {
  movies: PosterMovie[];
}

/** PW-03 "Editorial grid" container. */
export function PosterEditorialGrid({ movies }: PosterEditorialGridProps) {
  return (
    <div className="poster-editorial-grid">
      {movies.map((movie) => (
        <PosterEditorialCard key={movie.id} movie={movie} />
      ))}
    </div>
  );
}
