import { Clapperboard, Clock, Drama, Languages, Search } from 'lucide-react';
import { MultiSelectPopover } from './MultiSelectPopover';
import { ViewSwitcherPopover } from './ViewSwitcherPopover';
import { DatePickerPopover } from './DatePickerPopover';
import { DualRangeSlider } from './DualRangeSlider';
import { CINEMAS, LANGUAGES, GENRES } from './fixtures/filterOptions';
import type { PosterMovie, PosterWallFilters, PosterWallView } from './types';
import './FilterBar.css';

export interface FilterBarProps {
  movies: PosterMovie[];
  filters: PosterWallFilters;
  onFiltersChange: (next: PosterWallFilters) => void;
  view: PosterWallView;
  onViewChange: (view: PosterWallView) => void;
}

function formatHour(hour: number): string {
  if (hour === 24 || hour === 0) return 'Midnight';
  const period = hour < 12 ? 'AM' : 'PM';
  const hour12 = hour % 12 === 0 ? 12 : hour % 12;
  return `${hour12}:00 ${period}`;
}

/** Pure summary of the currently active filters, shown as the status line. */
export function describeActiveFilters(filters: PosterWallFilters): string {
  const parts = [
    `${filters.cinemas.length === 0 ? CINEMAS.length : filters.cinemas.length}/${CINEMAS.length} cinemas`,
    `${filters.langs.length === 0 ? LANGUAGES.length : filters.langs.length}/${LANGUAGES.length} languages`,
    `${filters.genres.length === 0 ? GENRES.length : filters.genres.length}/${GENRES.length} genres`,
    `${filters.dates.length} date${filters.dates.length === 1 ? '' : 's'} selected`,
    `${formatHour(filters.timeRange[0])}–${formatHour(filters.timeRange[1])}`,
  ];
  if (filters.search) parts.push(`searching "${filters.search}"`);
  return parts.join(' · ');
}

/** Full poster-wall toolbar: search, cinema/language/genre filters, view switcher, date picker, time-range slider. */
export function FilterBar({ filters, onFiltersChange, view, onViewChange }: FilterBarProps) {
  function patch(next: Partial<PosterWallFilters>) {
    onFiltersChange({ ...filters, ...next });
  }

  return (
    <div className="filter-bar">
      <div className="filter-bar__row filter-bar__row--search">
        <Search className="filter-bar__search-icon" aria-hidden="true" />
        <input
          className="filter-bar__search-input"
          placeholder="Search movies, directors, cinemas…"
          value={filters.search}
          onChange={(e) => patch({ search: e.target.value })}
        />
        <MultiSelectPopover
          label="Cinemas"
          icon={Clapperboard}
          options={CINEMAS}
          selected={filters.cinemas}
          onChange={(cinemas) => patch({ cinemas })}
          searchable
        />
        <MultiSelectPopover
          label="Language"
          icon={Languages}
          options={LANGUAGES}
          selected={filters.langs}
          onChange={(langs) => patch({ langs: langs as PosterWallFilters['langs'] })}
        />
        <MultiSelectPopover
          label="Genre"
          icon={Drama}
          options={GENRES}
          selected={filters.genres}
          onChange={(genres) => patch({ genres: genres as PosterWallFilters['genres'] })}
        />
        <div className="filter-bar__divider" />
        <ViewSwitcherPopover value={view} onChange={onViewChange} />
      </div>
      <div className="filter-bar__row filter-bar__row--sunken">
        <DatePickerPopover
          mode={filters.dateMode}
          onModeChange={(dateMode) => patch({ dateMode })}
          selected={filters.dates}
          onChange={(dates) => patch({ dates })}
        />
        <div className="filter-bar__divider" />
        <Clock className="filter-bar__clock-icon" aria-hidden="true" />
        <DualRangeSlider
          min={8}
          max={24}
          value={filters.timeRange}
          onChange={(timeRange) => patch({ timeRange })}
          formatLabel={([start, end]) => `${formatHour(start)} – ${formatHour(end)}`}
        />
      </div>
      <div className="filter-bar__status">{describeActiveFilters(filters)}</div>
    </div>
  );
}
