import { PosterImage } from './PosterImage';
import { GENRE_PALETTE } from './genrePalette';
import type { PosterMovie } from './types';
import './PosterEditorialCard.css';

export interface PosterEditorialCardProps {
  movie: PosterMovie;
}

/** PW-03 "Editorial grid" item — genre-tinted panel, oversized serif title, mono meta line. */
export function PosterEditorialCard({ movie }: PosterEditorialCardProps) {
  const family = GENRE_PALETTE[movie.genre];
  const metaLine = [movie.director, movie.year, `${movie.runtimeMin} min`].filter(Boolean).join(' · ');

  return (
    <div className={`poster-editorial-card panel-${family}`}>
      <PosterImage src={movie.poster} alt={movie.title} />
      <div className="poster-editorial-card__genre">{movie.genre}</div>
      <div className="poster-editorial-card__title">{movie.title}</div>
      <div className="poster-editorial-card__meta">{metaLine}</div>
    </div>
  );
}
