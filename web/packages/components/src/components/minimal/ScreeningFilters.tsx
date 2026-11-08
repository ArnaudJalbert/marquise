import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import {
  ACTIVE_CATALOGUE_FILTER_TYPES,
  type ActiveCatalogueFilter,
  type ActiveCatalogueFilterType,
  type CatalogueCinema,
} from "./catalogue-types";
import {
  CATALOGUE_TIME_FILTERS,
  getCatalogueTimeFilter,
} from "./catalogue-time-filters";

function getFilterTypeLabel(type: ActiveCatalogueFilterType): string {
  return `${type.charAt(0).toUpperCase()}${type.slice(1)}`;
}

export function ScreeningFilters({
  filters,
  cinemas,
  fixedCinemaId,
  onChange,
}: {
  filters: readonly ActiveCatalogueFilter[];
  cinemas: readonly CatalogueCinema[];
  fixedCinemaId?: string;
  onChange: (filters: ActiveCatalogueFilter[]) => void;
}) {
  const [pendingFocus, setPendingFocus] = useState<ActiveCatalogueFilterType | "add">();
  const addFilterRef = useRef<HTMLElement>(null);
  const chipButtons = useRef(new Map<ActiveCatalogueFilterType, HTMLButtonElement>());
  useEffect(() => {
    if (!pendingFocus) return;
    if (pendingFocus === "add") addFilterRef.current?.focus();
    else if (filters.some((filter) => filter.type === pendingFocus))
      chipButtons.current.get(pendingFocus)?.focus();
    setPendingFocus(undefined);
  }, [filters, pendingFocus]);

  const availableTypes = ACTIVE_CATALOGUE_FILTER_TYPES.filter(
    (type) =>
      !filters.some((filter) => filter.type === type) &&
      !(fixedCinemaId && type === "cinema") &&
      (type !== "cinema" || cinemas.length > 0),
  );
  const getFilterValueLabel = (filter: ActiveCatalogueFilter) =>
    filter.type === "cinema"
      ? cinemas.find((cinema) => cinema.id === filter.value)?.name ?? "Cinema unavailable"
      : getCatalogueTimeFilter(filter.value).label;
  const update = (next: ActiveCatalogueFilter) =>
    onChange(filters.map((filter) => filter.type === next.type ? next : filter));
  const closeOnEscape = (event: KeyboardEvent<HTMLDetailsElement>) => {
    if (event.key !== "Escape" || !event.currentTarget.open) return;
    // Tells an enclosing panel that this Escape is handled.
    event.preventDefault();
    event.currentTarget.open = false;
    event.currentTarget.querySelector("summary")?.focus();
  };
  const add = (type: ActiveCatalogueFilterType, menu: HTMLDetailsElement | null) => {
    if (type === "cinema") {
      const value = cinemas[0]?.id;
      if (!value) return;
      onChange([...filters, { type, value, operator: "is" }]);
    } else {
      onChange([
        ...filters,
        { type, value: CATALOGUE_TIME_FILTERS[0].value, operator: "is" },
      ]);
    }
    setPendingFocus(type);
    if (menu) menu.open = false;
  };

  return (
    <section className="minimal-filters" aria-label="Movie filters">
      <div className="minimal-filter-row">
        {filters.map((filter) => (
          <div
            className="minimal-filter-chip"
            key={filter.type}
            role="group"
            aria-label={`${filter.type} filter`}
          >
            <span>{getFilterTypeLabel(filter.type)} </span>
            <button
              ref={(button) => {
                if (button) chipButtons.current.set(filter.type, button);
                else chipButtons.current.delete(filter.type);
              }}
              type="button"
              aria-label={`Change ${filter.type} operator from ${filter.operator === "is" ? "is" : "is not"}`}
              onClick={() => update({ ...filter, operator: filter.operator === "is" ? "is_not" : "is" })}
            >
              {filter.operator === "is" ? "is " : "is not "}
            </button>
            <details className="minimal-filter-value" onKeyDown={closeOnEscape}>
              <summary>{getFilterValueLabel(filter)}</summary>
              <div className="minimal-filter-options">
                {(filter.type === "cinema"
                  ? cinemas.map((cinema) => ({
                      label: cinema.name,
                      next: { ...filter, value: cinema.id },
                    }))
                  : CATALOGUE_TIME_FILTERS.map(({ value, label }) => ({
                      label,
                      next: { ...filter, value },
                    }))
                ).map(({ label, next }) => (
                  <button
                    key={next.value}
                    type="button"
                    aria-pressed={filter.value === next.value}
                    onClick={(event) => {
                      update(next);
                      setPendingFocus(filter.type);
                      const details = event.currentTarget.closest("details");
                      if (details) details.open = false;
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </details>
            <button
              type="button"
              className="minimal-filter-remove"
              aria-label={`Remove ${filter.type} filter`}
              onClick={() => {
                onChange(filters.filter((item) => item.type !== filter.type));
                const nextFilter = filters.find((item) => item.type !== filter.type);
                setPendingFocus(nextFilter?.type ?? "add");
              }}
            >
              ×
            </button>
          </div>
        ))}
        {availableTypes.length > 0 && (
          <details className="minimal-add-filter" onKeyDown={closeOnEscape}>
            <summary ref={addFilterRef}>+ Filter</summary>
            <div className="minimal-filter-options">
              {availableTypes.map((type) => (
                <button
                  type="button"
                  key={type}
                  onClick={(event) => add(type, event.currentTarget.closest("details"))}
                >
                  {getFilterTypeLabel(type)}
                </button>
              ))}
            </div>
          </details>
        )}
        {filters.length >= 2 && (
          <button
            className="minimal-clear-filters"
            type="button"
            onClick={() => {
              onChange([]);
              setPendingFocus("add");
            }}
          >
            Clear all
          </button>
        )}
      </div>
    </section>
  );
}
