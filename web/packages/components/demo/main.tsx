import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  MinimalCatalogue,
  type CatalogueSelection,
  type CatalogueState,
} from "marquise-components";
import { cinemas, movies, today, tomorrow, weekend } from "./fixtures";

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
function Preview() {
  const [href, setHref] = useState(location.href);
  const [selection, setSelection] = useState(readSelection);
  const [state, setState] = useState<CatalogueState>("ready");
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
        Design prototype · Sample data · Fixed review date October 30, 2026,
        Montréal. Not live listings.
      </div>
      <MinimalCatalogue
        movies={movies}
        screeningLanguages={["English", "French", "Japanese"]}
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
          Sample booking links open example.com. Missing artwork and metadata
          are intentional. Pagination and network delays are visual samples, not
          an API implementation.
        </p>
        <details>
          <summary>Current sample selection</summary>
          <pre>{JSON.stringify(selection, null, 2)}</pre>
        </details>
      </aside>
    </>
  );
}
createRoot(document.getElementById("root")!).render(<Preview />);
