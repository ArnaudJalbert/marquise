import type { ActiveCatalogueSelection, CatalogueCinema } from "./catalogue-types";
import { MovieSearch } from "./MovieSearch";
import { PeriodPicker } from "./PeriodPicker";
import { ScreeningFilters } from "./ScreeningFilters";

/** The screenings period, search, and filter chips above the results. */
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
  return (
    <div className="minimal-screening-header">
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
  );
}
