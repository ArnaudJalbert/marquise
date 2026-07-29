import { PosterListingRow } from './PosterListingRow';
import type { PosterMovie } from './types';
import './PosterListingGrid.css';

export interface PosterListingGridProps {
  movies: PosterMovie[];
  onSelect?: (movieId: string) => void;
}

/** PW-04 "Listing hybrid" container. */
export function PosterListingGrid({ movies, onSelect }: PosterListingGridProps) {
  return (
    <div className="poster-listing-grid">
      {movies.map((movie) => (
        <PosterListingRow key={movie.id} movie={movie} onSelect={onSelect} />
      ))}
    </div>
  );
}
