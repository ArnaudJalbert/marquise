import type { PosterWallView } from './types';
import './PosterWallSkeleton.css';

export interface PosterWallSkeletonProps {
  view: PosterWallView;
  count?: number;
}

const VIEW_GRID_CLASS: Record<PosterWallView, string> = {
  'PW-01': 'poster-wall-skeleton--pw01',
  'PW-02': 'poster-wall-skeleton--pw02',
  'PW-03': 'poster-wall-skeleton--pw03',
  'PW-04': 'poster-wall-skeleton--pw04',
};

/**
 * Loading placeholder shown while movies are being fetched. Reuses each
 * view's exact grid formula so the layout doesn't jump once real data
 * arrives — a skeleton grid rather than a spinner, per the design spec's
 * own guidance ("preserves layout stability while data streams in").
 */
export function PosterWallSkeleton({ view, count = 8 }: PosterWallSkeletonProps) {
  const items = Array.from({ length: count });

  if (view === 'PW-04') {
    return (
      <div className={`poster-wall-skeleton ${VIEW_GRID_CLASS['PW-04']}`}>
        {items.map((_, i) => (
          <div key={i} className="poster-wall-skeleton__row">
            <div className="poster-wall-skeleton__thumb poster-wall-skeleton__pulse" />
            <div className="poster-wall-skeleton__row-lines">
              <div className="poster-wall-skeleton__bar poster-wall-skeleton__pulse" style={{ width: '70%' }} />
              <div className="poster-wall-skeleton__bar poster-wall-skeleton__bar--sm poster-wall-skeleton__pulse" style={{ width: '45%' }} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={`poster-wall-skeleton ${VIEW_GRID_CLASS[view]}`}>
      {items.map((_, i) => (
        <div key={i} className="poster-wall-skeleton__item">
          <div className="poster-wall-skeleton__poster poster-wall-skeleton__pulse" />
          {view !== 'PW-02' && <div className="poster-wall-skeleton__bar poster-wall-skeleton__pulse" style={{ width: '80%' }} />}
          {view === 'PW-03' && (
            <div className="poster-wall-skeleton__bar poster-wall-skeleton__bar--sm poster-wall-skeleton__pulse" style={{ width: '50%' }} />
          )}
        </div>
      ))}
    </div>
  );
}
