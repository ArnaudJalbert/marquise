import { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  MinimalCatalogue,
  type CatalogueSelection,
  type CatalogueState,
  type CatalogueMovie,
} from "marquise-components";
import { cinemas, movies, today, tomorrow, weekend } from "./fixtures";
import { HttpMarquiseClient } from "marquise-client";
import { loadAllMovies, loadMovieWeek } from "./api";

const initial: CatalogueSelection = {
  start: today,
  end: today,
  title: "",
  cinemas: [],
  languages: [],
  from: "",
  to: "",
};
function readSelection(): CatalogueSelection {
  const p = new URLSearchParams(location.search);
  return {
    start: p.get("start") ?? today,
    end: p.get("end") ?? today,
    title: p.get("title") ?? "",
    cinemas: p.getAll("cinema"),
    languages: p.getAll("language"),
    from: p.get("from") ?? "",
    to: p.get("to") ?? "",
  };
}

function Preview({ client }: { client: HttpMarquiseClient }) {
  const [href, setHref] = useState(location.href);
  const [selection, setSelection] = useState(readSelection);
  const [state, setState] = useState<CatalogueState>("ready");
  const [catalogueMovies, setCatalogueMovies] = useState(movies);
  const [catalogueNotice, setCatalogueNotice] = useState(
    "Loading movies from the local API…",
  );
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
          setCatalogueNotice("Local API unavailable. Showing sample movies.");
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
  const update = (next: CatalogueSelection) => {
    setState("ready");
    setSelection(next);
    const p = new URLSearchParams();
    for (const key of ["start", "end", "title", "from", "to"] as const)
      if (next[key]) p.set(key, next[key]);
    next.cinemas.forEach((c) => p.append("cinema", c));
    next.languages.forEach((l) => p.append("language", l));
    history.replaceState(null, "", `${location.pathname}?${p}`);
    setHref(location.href);
  };
  return (
    <>
      <div className="review-notice">
        Design prototype · Sample screenings · Review date October 30, 2026,
        Montréal. Movies and date navigation try the local API; failures retain
        labeled samples.
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
        tomorrow={tomorrow}
        weekend={weekend}
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
