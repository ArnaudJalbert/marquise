import { useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Popover } from './Popover';
import './MultiSelectPopover.css';

export interface MultiSelectPopoverProps {
  label: string;
  icon: LucideIcon;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
  searchable?: boolean;
}

/** Icon-button popover with a checkbox list, used for cinema/language/genre filters. */
export function MultiSelectPopover({ label, icon: Icon, options, selected, onChange, searchable }: MultiSelectPopoverProps) {
  const [search, setSearch] = useState('');
  const hasFilter = selected.length > 0 && selected.length < options.length;
  const allOn = selected.length === options.length;
  const query = search.trim().toLowerCase();
  const visibleOptions = query ? options.filter((o) => o.toLowerCase().includes(query)) : options;

  function toggleOption(option: string) {
    onChange(selected.includes(option) ? selected.filter((o) => o !== option) : [...selected, option]);
  }

  function toggleAll() {
    onChange(allOn ? [] : options);
  }

  return (
    <Popover
      trigger={(open, toggle) => (
        <button
          type="button"
          className={`multi-select-popover__trigger ${open ? 'multi-select-popover__trigger--open' : ''}`}
          onClick={toggle}
          aria-label={label}
        >
          <Icon className="multi-select-popover__icon" aria-hidden="true" />
          {hasFilter && <span className="multi-select-popover__badge" />}
        </button>
      )}
    >
      <div className="multi-select-popover__panel">
        <div className="multi-select-popover__header">
          <span className="multi-select-popover__label">{label}</span>
          <button type="button" className="multi-select-popover__toggle-all" onClick={toggleAll}>
            {allOn ? 'Unselect all' : 'Select all'}
          </button>
        </div>
        {searchable && (
          <input
            className="multi-select-popover__search"
            placeholder={`Search ${label.toLowerCase()}…`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        )}
        <div className="multi-select-popover__options">
          {visibleOptions.map((option) => (
            <label key={option} className="multi-select-popover__option">
              <input type="checkbox" checked={selected.includes(option)} onChange={() => toggleOption(option)} />
              {option}
            </label>
          ))}
          {visibleOptions.length === 0 && (
            <span className="multi-select-popover__no-match">No {label.toLowerCase()} match</span>
          )}
        </div>
      </div>
    </Popover>
  );
}
