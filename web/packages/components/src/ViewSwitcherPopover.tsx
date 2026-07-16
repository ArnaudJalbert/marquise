import { LayoutGrid } from 'lucide-react';
import { Popover } from './Popover';
import type { PosterWallView } from './types';
import './ViewSwitcherPopover.css';

export interface ViewSwitcherPopoverProps {
  value: PosterWallView;
  onChange: (view: PosterWallView) => void;
}

const VIEW_OPTIONS: { view: PosterWallView; label: string; descriptor: string }[] = [
  { view: 'PW-01', label: 'Caption grid', descriptor: 'poster + title' },
  { view: 'PW-02', label: 'Dense wall', descriptor: 'poster only' },
  { view: 'PW-03', label: 'Editorial grid', descriptor: 'editorial panel' },
  { view: 'PW-04', label: 'Listing hybrid', descriptor: 'listing row' },
];

function ViewGlyph({ view }: { view: PosterWallView }) {
  switch (view) {
    case 'PW-01':
      return (
        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
          <rect x="0" y="0" width="7" height="9" fill="currentColor" />
          <rect x="0" y="11" width="7" height="2" fill="currentColor" />
          <rect x="9" y="0" width="7" height="9" fill="currentColor" />
          <rect x="9" y="11" width="7" height="2" fill="currentColor" />
        </svg>
      );
    case 'PW-02':
      return (
        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
          {[0, 1, 2].map((col) =>
            [0, 1].map((row) => (
              <rect key={`${col}-${row}`} x={col * 5.5} y={row * 8} width="5" height="7" fill="currentColor" />
            )),
          )}
        </svg>
      );
    case 'PW-03':
      return (
        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
          <rect x="0" y="3" width="10" height="13" fill="currentColor" />
          <rect x="12" y="3" width="4" height="3" fill="currentColor" />
          <rect x="12" y="8" width="4" height="2" fill="currentColor" />
        </svg>
      );
    case 'PW-04':
      return (
        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
          <rect x="0" y="1" width="5" height="7" fill="currentColor" />
          <rect x="7" y="3" width="9" height="2" fill="currentColor" />
          <rect x="0" y="10" width="5" height="7" fill="currentColor" />
          <rect x="7" y="12" width="9" height="2" fill="currentColor" />
        </svg>
      );
  }
}

/** Popover listing the four approved poster-wall layouts. */
export function ViewSwitcherPopover({ value, onChange }: ViewSwitcherPopoverProps) {
  return (
    <Popover
      align="end"
      trigger={(_open, toggle) => (
        <button type="button" className="view-switcher-popover__trigger" onClick={toggle} aria-label="Change layout">
          <LayoutGrid className="view-switcher-popover__trigger-icon" aria-hidden="true" />
        </button>
      )}
    >
      <div className="view-switcher-popover__panel">
        {VIEW_OPTIONS.map((option) => (
          <button
            key={option.view}
            type="button"
            className={`view-switcher-popover__option ${value === option.view ? 'view-switcher-popover__option--active' : ''}`}
            onClick={() => onChange(option.view)}
          >
            <span className="view-switcher-popover__glyph">
              <ViewGlyph view={option.view} />
            </span>
            <span className="view-switcher-popover__text">
              <span className="view-switcher-popover__option-label">{option.label}</span>
              <span className="view-switcher-popover__option-code">
                {option.view} · {option.descriptor}
              </span>
            </span>
          </button>
        ))}
      </div>
    </Popover>
  );
}
