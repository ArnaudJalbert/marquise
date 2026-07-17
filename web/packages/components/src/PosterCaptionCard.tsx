import { PosterImage } from './PosterImage';
import type { PosterMovie } from './types';
import './PosterCaptionCard.css';

export interface PosterCaptionCardProps {
  movie: PosterMovie;
}

/** PW-01 "Caption grid" item — poster + centered serif title, no metadata. */
export function PosterCaptionCard({ movie }: PosterCaptionCardProps) {
  return (
    <div className="poster-caption-card">
      <PosterImage src={movie.poster} alt={movie.title} />
      <div className="poster-caption-card__title">{movie.title}</div>
    </div>
  );
}
