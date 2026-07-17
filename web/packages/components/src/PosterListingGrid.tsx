import { PosterListingRow } from './PosterListingRow';
import type { PosterMovie } from './types';
import './PosterListingGrid.css';

export interface PosterListingGridProps {
  movies: PosterMovie[];
}

/** PW-04 "Listing hybrid" container. */
export function PosterListingGrid({ movies }: PosterListingGridProps) {
  return (
    <div className="poster-listing-grid">
      {movies.map((movie) => (
        <PosterListingRow key={movie.id} movie={movie} />
      ))}
    </div>
  );
}
