import { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  MinimalCatalogue,
  type ActiveCatalogueFilter,
  type ActiveCatalogueSelection,
  type CatalogueState,
  type CatalogueMovie,
} from "marquise-components";
import { cinemas, movies, today } from "./fixtures";
import { HttpMarquiseClient } from "marquise-client";
import { loadAllMovies, loadMovieWeek } from "./api";

const apiMode = import.meta.env.VITE_MARQUISE_DATA_SOURCE === "api";

type TimeFilterValue = Extract<ActiveCatalogueFilter, { type: "time" }>["value"];
const timeFilterValues: readonly TimeFilterValue[] = ["matinee", "evening", "late"];

function isTimeFilterValue(value: string): value is TimeFilterValue {
  return timeFilterValues.some((timeValue) => timeValue === value);
}

/** Parses `cinema` and `time` params like the app: a leading `-` means "is not". */
function readFilters(params: URLSearchParams): ActiveCatalogueFilter[] {
  const filters: ActiveCatalogueFilter[] = [];
  for (const [type, rawValue] of [
    ["cinema", params.get("cinema")],
    ["time", params.get("time")],
  ] as const) {
    if (!rawValue) continue;
    const operator = rawValue.startsWith("-") ? "is_not" : "is";
    const value = operator === "is_not" ? rawValue.slice(1) : rawValue;
    if (!value) continue;
    if (type === "cinema") filters.push({ type, value, operator });
    else if (isTimeFilterValue(value)) filters.push({ type, value, operator });
  }
  return filters;
}

const initial: ActiveCatalogueSelection = {
  start: today,
  end: today,
  title: "",
  filters: [],
};
function readSelection(): ActiveCatalogueSelection {
  const p = new URLSearchParams(location.search);
  return {
    start: p.get("start") ?? today,
    end: p.get("end") ?? today,
    title: p.get("q") ?? "",
    filters: readFilters(p),
  };
}

function Preview({ client }: { client: HttpMarquiseClient }) {
  const [href, setHref] = useState(location.href);
  const [selection, setSelection] = useState(readSelection);
  const [state, setState] = useState<CatalogueState>("ready");
  const [catalogueMovies, setCatalogueMovies] = useState(movies);
  const [catalogueNotice, setCatalogueNotice] = useState("Loading movies…");
  useEffect(() => {
    const controller = new AbortController();
    void loadAllMovies(client, controller.signal)
      .then((loaded) => {
        if (!controller.signal.aborted) {
          setCatalogueMovies(loaded);
          setCatalogueNotice("");
        }
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setCatalogueNotice("Could not load movies. Showing sample movies.");
      });
    return () => controller.abort();
  }, [client]);
  const loadWeek = useCallback(
    (movie: CatalogueMovie, start: string, end: string, signal?: AbortSignal) =>
      loadMovieWeek(client, movie, start, end, signal),
    [client],
  );
  useEffect(() => {
    const pop = () => {
      setHref(location.href);
      setSelection(readSelection());
    };
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);
  const navigate = (next: string) => {
    history.pushState(null, "", next);
    setHref(location.href);
    setSelection(readSelection());
    document.getElementById("minimal-main")?.focus();
    window.scrollTo(0, 0);
  };
  const update = (next: ActiveCatalogueSelection) => {
    setState("ready");
    setSelection(next);
    const p = new URLSearchParams();
    p.set("start", next.start);
    p.set("end", next.end);
    if (next.title) p.set("q", next.title);
    for (const { type, value, operator } of next.filters)
      p.set(type, `${operator === "is_not" ? "-" : ""}${value}`);
    history.replaceState(null, "", `${location.pathname}?${p}`);
    setHref(location.href);
  };
  return (
    <>
      <div className="review-notice">
        Design prototype · Sample screenings ·{" "}
        {apiMode
          ? "Catalogue and date navigation: local API"
          : "Sample API, no backend needed"}{" "}
        · Review date October 30, 2026, Montréal.
        {!apiMode && " Fictional listings and booking links."}
      </div>
      <MinimalCatalogue
        movies={movies}
        catalogueMovies={catalogueMovies}
        catalogueNotice={catalogueNotice}
        screeningLanguages={["VO", "VOA", "VOF", "VOSTF", "VOSTA", "VF"]}
        cinemas={cinemas}
        href={href}
        navigate={navigate}
        selection={selection}
        onSelection={update}
        today={today}
        state={state}
        onRetry={() => setState("ready")}
        onLoadWeek={loadWeek}
      />
      <aside className="review-tools" aria-label="Prototype review controls">
        <label>
          Sample state{" "}
          <select
            value={state}
            onChange={(e) => setState(e.target.value as CatalogueState)}
          >
            {["ready", "initial-loading", "loading-more", "empty", "error"].map(
              (s) => (
                <option key={s}>{s}</option>
              ),
            )}
          </select>
        </label>
        <button
          onClick={() => {
            setState("ready");
            update(initial);
            navigate("/");
          }}
        >
          Reset prototype
        </button>
        <p>
          Sample booking links open example.com. All sample films have posters.
          The sample schedule ranges from one screening to 25 per day across
          seven cinemas and two weeks. This is a local design preview, not a
          production listing.
        </p>
        <details>
          <summary>Current sample selection</summary>
          <pre>{JSON.stringify(selection, null, 2)}</pre>
        </details>
      </aside>
    </>
  );
}
const client = new HttpMarquiseClient({ baseUrl: location.origin });
createRoot(document.getElementById("root")!).render(
  <Preview client={client} />,
);
