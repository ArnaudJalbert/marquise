import { useEffect, useRef, useState } from "react";
import type {
  ActiveCatalogueSelection,
  CatalogueCinema,
  MinimalCatalogueProps,
} from "./catalogue-types";
import { PeriodPicker } from "./PeriodPicker";
import { ScreeningFilters } from "./ScreeningFilters";

export type CountMovies = NonNullable<MinimalCatalogueProps["onCountMovies"]>;

/** How many movies match the selection, or undefined until counted. */
function useMovieCount(selection: ActiveCatalogueSelection, onCountMovies?: CountMovies) {
  const key = JSON.stringify(selection);
  const [counted, setCounted] = useState<{ key: string; count: number }>();
  const latest = useRef(selection);
  latest.current = selection;
  useEffect(() => {
    if (!onCountMovies) return;
    const controller = new AbortController();
    // A failed count only drops the number from the apply button.
    onCountMovies(latest.current, controller.signal).then(
      (count) => setCounted({ key, count }),
      () => {},
    );
    return () => controller.abort();
  }, [key, onCountMovies]);
  return counted?.key === key ? counted.count : undefined;
}

function getApplyLabel(count: number | undefined): string {
  if (count === undefined) return "Show movies";
  return `Show ${count} ${count === 1 ? "movie" : "movies"}`;
}

/** Bottom sheet editing a draft of the period and filters; applies on "Show N movies". */
export function ScreeningSheet({
  selection,
  onApply,
  onCancel,
  onCountMovies,
  cinemas,
  today,
  fixedCinemaId,
}: {
  selection: ActiveCatalogueSelection;
  onApply: (selection: ActiveCatalogueSelection) => void;
  onCancel: () => void;
  onCountMovies?: CountMovies;
  cinemas: readonly CatalogueCinema[];
  today: string;
  fixedCinemaId?: string;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [draft, setDraft] = useState(selection);
  const count = useMovieCount(draft, onCountMovies);
  useEffect(() => dialog.current?.showModal(), []);

  return (
    <dialog
      ref={dialog}
      className="minimal-sheet"
      aria-label="Dates and filters"
      onCancel={(event) => {
        // Escape cancels the draft; the parent unmounts the sheet.
        event.preventDefault();
        onCancel();
      }}
      onClick={(event) => {
        // A tap on the backdrop targets the dialog itself, never its body.
        if (event.target === event.currentTarget) onCancel();
      }}
    >
      <div className="minimal-sheet-body">
        <PeriodPicker
          start={draft.start}
          end={draft.end}
          today={today}
          heading="h2"
          onChange={(start, end) => setDraft({ ...draft, start, end })}
        />
        <ScreeningFilters
          filters={draft.filters}
          onChange={(filters) => setDraft({ ...draft, filters })}
          cinemas={cinemas}
          fixedCinemaId={fixedCinemaId}
        />
        <button type="button" className="minimal-sheet-apply" onClick={() => onApply(draft)}>
          {getApplyLabel(count)}
        </button>
      </div>
    </dialog>
  );
}
