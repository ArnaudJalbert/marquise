import { PosterImage } from './PosterImage';
import type { PosterMovie } from './types';
import './PosterListingRow.css';

export interface PosterListingRowProps {
  movie: PosterMovie;
}

/** PW-04 "Listing hybrid" row. All showtimes are shown, wrapping onto additional lines as needed. */
export function PosterListingRow({ movie }: PosterListingRowProps) {
  const { screenings } = movie;
  // Only annotate each showtime with its language when this row actually mixes
  // VO/VF — most rows are single-language, where the badge would be noise.
  const hasMixedLangs = new Set(screenings.map((s) => s.lang)).size > 1;

  return (
    <div className="poster-listing-row">
      <div className="poster-listing-row__thumb">
        <PosterImage src={movie.poster} alt={movie.title} />
      </div>
      <div className="poster-listing-row__body">
        <div className="poster-listing-row__title">{movie.title}</div>
        <div className="poster-listing-row__times">
          {screenings.map((s, i) => (
            <span key={`${s.time}-${s.lang}`}>
              {i > 0 && ' · '}
              {s.time}
              {hasMixedLangs && <span className="poster-listing-row__lang"> {s.lang}</span>}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
