import { useCallback, useEffect, useRef, useState } from "react";
import { FiltersButton } from "./FiltersButton";
import { MovieSearch } from "./MovieSearch";
import { PeriodStepper } from "./PeriodPicker";
import type { ScreeningControlsProps } from "./ScreeningControls";
import { ScreeningSheet } from "./ScreeningSheet";
import { useScrolledPast } from "./use-scrolled-past";

/** Phone controls: sticky ‹ period ›, a search row that scrolls away, and a bottom sheet. */
export function PhoneScreeningControls({
  selection,
  onSelection,
  onCountMovies,
  cinemas,
  today,
  fixedCinemaId,
  heading,
}: ScreeningControlsProps) {
  const searchRow = useScrolledPast();
  const opener = useRef<HTMLElement | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const openSheet = (button: HTMLElement) => {
    opener.current = button;
    setSheetOpen(true);
  };
  const closeSheet = useCallback(() => setSheetOpen(false), []);
  // Focus returns once the modal sheet is gone and the page is interactive again.
  useEffect(() => {
    if (!sheetOpen) opener.current?.focus();
  }, [sheetOpen]);
  const filtersButton = (
    <FiltersButton
      count={selection.filters.length}
      aria-haspopup="dialog"
      aria-expanded={sheetOpen}
      onClick={(event) => openSheet(event.currentTarget)}
    />
  );

  return (
    <>
      <section className="minimal-phone-bar" aria-label="Screening controls">
        <PeriodStepper
          start={selection.start}
          end={selection.end}
          today={today}
          heading={heading}
          onChange={(start, end) => onSelection({ ...selection, start, end })}
          onOpen={openSheet}
          expanded={sheetOpen}
        />
        {searchRow.scrolledPast && filtersButton}
      </section>
      <div ref={searchRow.target} className="minimal-phone-search">
        <MovieSearch
          value={selection.title}
          onSearch={(title) => onSelection({ ...selection, title })}
        />
        {filtersButton}
      </div>
      {sheetOpen && (
        <ScreeningSheet
          selection={selection}
          onApply={(draft) => {
            closeSheet();
            onSelection(draft);
          }}
          onCancel={closeSheet}
          onCountMovies={onCountMovies}
          cinemas={cinemas}
          today={today}
          fixedCinemaId={fixedCinemaId}
        />
      )}
    </>
  );
}
