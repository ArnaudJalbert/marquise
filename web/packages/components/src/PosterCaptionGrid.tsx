import { PosterCaptionCard } from './PosterCaptionCard';
import type { PosterMovie } from './types';
import './PosterCaptionGrid.css';

export interface PosterCaptionGridProps {
  movies: PosterMovie[];
}

/** PW-01 "Caption grid" container. */
export function PosterCaptionGrid({ movies }: PosterCaptionGridProps) {
  return (
    <div className="poster-caption-grid">
      {movies.map((movie) => (
        <PosterCaptionCard key={movie.id} movie={movie} />
      ))}
    </div>
  );
}
