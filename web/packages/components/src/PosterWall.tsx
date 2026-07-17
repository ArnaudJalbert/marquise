import { PosterCaptionGrid } from './PosterCaptionGrid';
import { PosterDenseGrid } from './PosterDenseGrid';
import { PosterEditorialGrid } from './PosterEditorialGrid';
import { PosterListingGrid } from './PosterListingGrid';
import type { PosterMovie, PosterWallView } from './types';
import './PosterWall.css';

export interface PosterWallProps {
  view: PosterWallView;
  movies: PosterMovie[];
}

/** Switches between the four approved poster-wall grid layouts, or renders the empty state. */
export function PosterWall({ view, movies }: PosterWallProps) {
  if (movies.length === 0) {
    return <p className="poster-wall__empty">No screenings match these filters.</p>;
  }

  switch (view) {
    case 'PW-01':
      return <PosterCaptionGrid movies={movies} />;
    case 'PW-02':
      return <PosterDenseGrid movies={movies} />;
    case 'PW-03':
      return <PosterEditorialGrid movies={movies} />;
    case 'PW-04':
      return <PosterListingGrid movies={movies} />;
  }
}
