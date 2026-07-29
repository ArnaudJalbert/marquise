import { PosterImage } from './PosterImage';
import { paletteFamily } from './genrePalette';
import type { PosterMovie } from './types';
import './PosterEditorialCard.css';

export interface PosterEditorialCardProps {
  movie: PosterMovie;
  onSelect?: (movieId: string) => void;
}

/** PW-03 "Editorial grid" item — genre-tinted panel, oversized serif title, mono meta line. */
export function PosterEditorialCard({ movie, onSelect }: PosterEditorialCardProps) {
  const family = paletteFamily(movie.genre);
  const metaLine = [movie.director, movie.year, `${movie.runtimeMin} min`].filter(Boolean).join(' · ');

  return (
    <div
      className={`poster-editorial-card panel-${family}`}
      role="button"
      tabIndex={onSelect ? 0 : undefined}
      aria-label={movie.title}
      onClick={() => onSelect?.(movie.movieId)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect?.(movie.movieId); } }}
    >
      <PosterImage src={movie.poster} alt={movie.title} />
      <div className="poster-editorial-card__genre">{movie.genre}</div>
      <div className="poster-editorial-card__title">{movie.title}</div>
      <div className="poster-editorial-card__meta">{metaLine}</div>
    </div>
  );
}
