import { useEffect, useRef, useState } from "react";
import type { ActiveCatalogueSelection, CatalogueCinema } from "./catalogue-types";
import { MovieSearch } from "./MovieSearch";
import { PeriodPicker } from "./PeriodPicker";
import { ScreeningFilters } from "./ScreeningFilters";
import { ScreeningsBar } from "./ScreeningsBar";

/** Whether the element has scrolled fully above the top of the viewport. */
function useScrolledPast() {
  const target = useRef<HTMLDivElement>(null);
  const [scrolledPast, setScrolledPast] = useState(false);
  useEffect(() => {
    const element = target.current;
    if (!element) return;
    const observer = new IntersectionObserver((entries) => {
      const entry = entries.at(-1);
      if (entry) setScrolledPast(!entry.isIntersecting && entry.boundingClientRect.top < 0);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return { target, scrolledPast };
}

/** The screenings period, search, and filter chips, collapsing into a sticky bar on scroll. */
export function ScreeningControls({
  selection,
  onSelection,
  cinemas,
  today,
  fixedCinemaId,
  heading,
}: {
  selection: ActiveCatalogueSelection;
  onSelection: (selection: ActiveCatalogueSelection) => void;
  cinemas: readonly CatalogueCinema[];
  today: string;
  fixedCinemaId?: string;
  heading?: "h1" | "h2";
}) {
  const header = useScrolledPast();
  return (
    <>
      {header.scrolledPast && (
        <ScreeningsBar
          selection={selection}
          onSelection={onSelection}
          cinemas={cinemas}
          today={today}
          fixedCinemaId={fixedCinemaId}
        />
      )}
      {/* Inert while scrolled away, so `/` and Tab reach the bar instead. */}
      <div
        ref={header.target}
        className="minimal-screening-header"
        inert={header.scrolledPast}
      >
        <PeriodPicker
          start={selection.start}
          end={selection.end}
          today={today}
          heading={heading}
          onChange={(start, end) => onSelection({ ...selection, start, end })}
        />
        <div className="minimal-screenings-top">
          <MovieSearch
            value={selection.title}
            onSearch={(title) => onSelection({ ...selection, title })}
          />
        </div>
        <ScreeningFilters
          filters={selection.filters}
          onChange={(filters) => onSelection({ ...selection, filters })}
          cinemas={cinemas}
          fixedCinemaId={fixedCinemaId}
        />
      </div>
    </>
  );
}
