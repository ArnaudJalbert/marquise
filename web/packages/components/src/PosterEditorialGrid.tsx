import { PosterEditorialCard } from './PosterEditorialCard';
import type { PosterMovie } from './types';
import './PosterEditorialGrid.css';

export interface PosterEditorialGridProps {
  movies: PosterMovie[];
  onSelect?: (movieId: string) => void;
}

/** PW-03 "Editorial grid" container. */
export function PosterEditorialGrid({ movies, onSelect }: PosterEditorialGridProps) {
  return (
    <div className="poster-editorial-grid">
      {movies.map((movie) => (
        <PosterEditorialCard key={movie.id} movie={movie} onSelect={onSelect} />
      ))}
    </div>
  );
}
