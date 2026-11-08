import type { ActiveCatalogueSelection, CatalogueCinema } from "./catalogue-types";
import { MovieSearch } from "./MovieSearch";
import { PeriodPicker } from "./PeriodPicker";
import { ScreeningFilters } from "./ScreeningFilters";
import { PhoneScreeningControls } from "./PhoneScreeningControls";
import type { CountMovies } from "./ScreeningSheet";
import { ScreeningsBar } from "./ScreeningsBar";
import { PHONE_MEDIA_QUERY, useMediaQuery } from "./use-media-query";
import { useScrolledPast } from "./use-scrolled-past";

export interface ScreeningControlsProps {
  selection: ActiveCatalogueSelection;
  onSelection: (selection: ActiveCatalogueSelection) => void;
  /** Counts the movies a draft selection would show, for the phone sheet. */
  onCountMovies?: CountMovies;
  cinemas: readonly CatalogueCinema[];
  today: string;
  fixedCinemaId?: string;
  heading?: "h1" | "h2";
}

/**
 * The screenings period, search, and filter chips, collapsing into a sticky bar on scroll.
 * Phones get a sticky period bar and a bottom sheet instead.
 */
export function ScreeningControls(props: ScreeningControlsProps) {
  const isPhone = useMediaQuery(PHONE_MEDIA_QUERY);
  return isPhone ? <PhoneScreeningControls {...props} /> : <WideScreeningControls {...props} />;
}

function WideScreeningControls({
  selection,
  onSelection,
  cinemas,
  today,
  fixedCinemaId,
  heading,
}: ScreeningControlsProps) {
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
