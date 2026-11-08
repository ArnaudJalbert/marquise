import { SlidersHorizontal } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState, type RefObject } from "react";
import { addDays } from "./catalogue-format";
import type { ActiveCatalogueSelection, CatalogueCinema } from "./catalogue-types";
import { MovieSearch } from "./MovieSearch";
import { DayStrip, PeriodStepper, usePeriodView } from "./PeriodPicker";
import { ScreeningFilters } from "./ScreeningFilters";

/** Closes the Filters panel when a press lands outside the bar. */
function useCloseOnOutsidePress(
  bar: RefObject<HTMLElement | null>,
  open: boolean,
  onClose: () => void,
) {
  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: PointerEvent) => {
      if (!bar.current?.contains(event.target as Node)) onClose();
    };
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, [bar, open, onClose]);
}

/** One-row sticky bar: ‹ period ›, mini day strip, search, and Filters (N). */
export function ScreeningsBar({
  selection,
  onSelection,
  cinemas,
  today,
  fixedCinemaId,
}: {
  selection: ActiveCatalogueSelection;
  onSelection: (selection: ActiveCatalogueSelection) => void;
  cinemas: readonly CatalogueCinema[];
  today: string;
  fixedCinemaId?: string;
}) {
  const bar = useRef<HTMLElement>(null);
  const filtersButton = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const [filtersOpen, setFiltersOpen] = useState(false);
  const closeFilters = useCallback(() => setFiltersOpen(false), []);
  useCloseOnOutsidePress(bar, filtersOpen, closeFilters);
  const { range, view } = usePeriodView(selection.start, selection.end, today);
  const setPeriod = (start: string, end: string) => onSelection({ ...selection, start, end });
  const filterCount = selection.filters.length;

  return (
    <section
      ref={bar}
      className="minimal-screenings-bar"
      aria-label="Screening controls"
      onKeyDown={(event) => {
        // An open chip menu handles its own Escape first.
        if (event.key !== "Escape" || !filtersOpen || event.defaultPrevented) return;
        setFiltersOpen(false);
        filtersButton.current?.focus();
      }}
    >
      <div className="minimal-screenings-bar-row">
        <PeriodStepper
          start={selection.start}
          end={selection.end}
          today={today}
          heading="strong"
          onChange={setPeriod}
        />
        <DayStrip
          today={today}
          range={range}
          view={view}
          onChange={(from, to) => setPeriod(addDays(today, from), addDays(today, to))}
        />
        <MovieSearch
          value={selection.title}
          onSearch={(title) => onSelection({ ...selection, title })}
        />
        <button
          ref={filtersButton}
          type="button"
          className="minimal-filters-button"
          aria-label={filterCount ? `Filters (${filterCount} active)` : "Filters"}
          aria-expanded={filtersOpen}
          aria-controls={panelId}
          onClick={() => setFiltersOpen(!filtersOpen)}
        >
          <SlidersHorizontal aria-hidden size={16} />
          Filters
          {filterCount > 0 && <b aria-hidden>{filterCount}</b>}
        </button>
      </div>
      {filtersOpen && (
        <div
          id={panelId}
          role="dialog"
          aria-label="Filters"
          className="minimal-screenings-bar-panel"
        >
          <ScreeningFilters
            filters={selection.filters}
            onChange={(filters) => onSelection({ ...selection, filters })}
            cinemas={cinemas}
            fixedCinemaId={fixedCinemaId}
          />
        </div>
      )}
    </section>
  );
}
