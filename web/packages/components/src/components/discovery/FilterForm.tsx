import { useCallback, useState } from "react";
import type { DiscoveryClient, ScreeningQuery } from "marquise-client";
import { screeningsHref, screeningValidation } from "./discovery-state";
import { useResource } from "./use-resource";

export function FilterForm({
  query,
  client,
  onApply,
}: {
  query: ScreeningQuery;
  client: DiscoveryClient;
  onApply: (query: ScreeningQuery) => void;
}) {
  const [cinemaId, setCinemaId] = useState(query.cinemaId ?? "");
  const [cinemaPage, setCinemaPage] = useState(1);
  const cinemas = useResource(
    useCallback(
      (signal: AbortSignal) => client.fetchCinemaPage(cinemaPage, signal),
      [client, cinemaPage],
    ),
  );
  const [validation, setValidation] = useState<string>();
  return (
    <form
      className="screening-filters"
      key={JSON.stringify(query)}
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const next = {
          date: String(data.get("date")),
          page: 1,
          size: 48,
          movie: String(data.get("movie") || ""),
          cinemaId: String(data.get("cinema") || ""),
          language: String(data.get("language") || ""),
          fromTime: String(data.get("from") || ""),
          toTime: String(data.get("to") || ""),
        };
        const error = screeningValidation(next);
        setValidation(error);
        if (!error) onApply(next);
      }}
    >
      <div className="filter-primary">
        <label>
          Date
          <input type="date" name="date" required defaultValue={query.date} />
        </label>
        <label className="movie-search">
          Find a film
          <input
            type="search"
            name="movie"
            placeholder="A title, a hunch…"
            defaultValue={query.movie}
          />
        </label>
        <button className="green-button" type="submit">
          Find screenings →
        </button>
      </div>
      <details
        open={Boolean(
          query.cinemaId || query.language || query.fromTime || query.toTime,
        )}
      >
        <summary>
          Narrow it down <span>cinema, language & time</span>
        </summary>
        <div className="filter-secondary">
          <label>
            Cinema
            <select
              name="cinema"
              value={cinemaId}
              onChange={(event) => setCinemaId(event.target.value)}
            >
              <option value="">All cinemas</option>
              {cinemaId &&
                !cinemas.data?.items.some(
                  (cinema) => cinema.id === cinemaId,
                ) && <option value={cinemaId}>Selected cinema</option>}
              {cinemas.data?.items.map((cinema) => (
                <option key={cinema.id} value={cinema.id}>
                  {cinema.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Language code
            <input
              name="language"
              placeholder="e.g. VOF, VOSTF"
              defaultValue={query.language}
            />
          </label>
          <label>
            From
            <input type="time" name="from" defaultValue={query.fromTime} />
          </label>
          <label>
            Until
            <input type="time" name="to" defaultValue={query.toTime} />
          </label>
        </div>
        <p className="filter-hint">
          Times are local to Montréal. Leave fields blank to cast a wider net.
          Use the exact language code from the cinema's listing.
        </p>
        {cinemas.error && (
          <p role="alert">
            Cinema list unavailable.{" "}
            <button type="button" onClick={cinemas.retry}>
              Retry cinemas
            </button>
          </p>
        )}
        {cinemas.data && cinemas.data.pages > 1 && (
          <div className="cinema-pages">
            <button
              type="button"
              disabled={cinemaPage === 1}
              onClick={() => setCinemaPage((p) => p - 1)}
            >
              Previous cinemas
            </button>
            <button
              type="button"
              disabled={cinemaPage >= cinemas.data.pages}
              onClick={() => setCinemaPage((p) => p + 1)}
            >
              More cinemas
            </button>
          </div>
        )}
      </details>
      {validation && (
        <p role="alert" className="filter-validation">
          {validation}
        </p>
      )}
      <a
        className="reset-link"
        href={screeningsHref({ date: query.date, page: 1 })}
      >
        Clear filters
      </a>
    </form>
  );
}
