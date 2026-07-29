import { PosterImage } from './PosterImage';
import type { PosterMovie } from './types';
import './PosterCaptionCard.css';

export interface PosterCaptionCardProps {
  movie: PosterMovie;
  onSelect?: (movieId: string) => void;
}

/** PW-01 "Caption grid" item — poster + centered serif title, no metadata. */
export function PosterCaptionCard({ movie, onSelect }: PosterCaptionCardProps) {
  return (
    <div
      className="poster-caption-card"
      role="button"
      tabIndex={onSelect ? 0 : undefined}
      aria-label={movie.title}
      onClick={() => onSelect?.(movie.movieId)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect?.(movie.movieId); } }}
    >
      <PosterImage src={movie.poster} alt={movie.title} />
      <div className="poster-caption-card__title">{movie.title}</div>
    </div>
  );
}
