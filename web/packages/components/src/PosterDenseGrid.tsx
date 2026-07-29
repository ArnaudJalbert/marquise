import { PosterImage } from './PosterImage';
import type { PosterMovie } from './types';
import './PosterDenseGrid.css';

export interface PosterDenseGridProps {
  movies: PosterMovie[];
  onSelect?: (movieId: string) => void;
}

/**
 * PW-02 "Dense wall" — poster-only tiles, no visible caption. Title is only
 * discoverable via the native tooltip (`title`) and `aria-label`, per the
 * design system's own rationale for this layout.
 */
export function PosterDenseGrid({ movies, onSelect }: PosterDenseGridProps) {
  return (
    <div className="poster-dense-grid">
      {movies.map((movie) => (
        <div
          key={movie.id}
          className="poster-dense-grid__tile"
          title={movie.title}
          aria-label={movie.title}
          role="button"
          tabIndex={onSelect ? 0 : undefined}
          onClick={() => onSelect?.(movie.movieId)}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect?.(movie.movieId); } }}
        >
          <PosterImage src={movie.poster} alt={movie.title} />
        </div>
      ))}
    </div>
  );
}
