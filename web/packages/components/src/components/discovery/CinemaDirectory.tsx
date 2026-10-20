import { useCallback } from "react";
import type { DiscoveryClient } from "marquise-client";
import { screeningQuery, screeningsHref } from "./discovery-state";
import { useResource } from "./use-resource";
import { RequestState } from "./RequestState";

export function CinemaDirectory({
  url,
  today,
  client,
  navigate,
}: {
  url: URL;
  today: string;
  client: DiscoveryClient;
  navigate: (href: string) => void;
}) {
  const page = screeningQuery(url, today).page;
  const name = url.searchParams.get("name") ?? "";
  const result = useResource(
    useCallback(
      (signal: AbortSignal) => client.fetchCinemaPage(page, signal, name),
      [client, page, name],
    ),
  );
  const change = (nextName: string, nextPage = 1) =>
    navigate(
      `/cinemas?${new URLSearchParams({ ...(nextName ? { name: nextName } : {}), ...(nextPage > 1 ? { page: String(nextPage) } : {}) })}`,
    );
  return (
    <>
      <header className="listings-intro">
        <p className="eyebrow">THE ROOMS THAT MAKE THE MOVIES</p>
        <h1>Find your favourite seat.</h1>
        <p>
          Montréal's cinemas, big screens and little rituals. Sticky floors not
          guaranteed.
        </p>
      </header>
      <form
        className="cinema-search"
        onSubmit={(event) => {
          event.preventDefault();
          change(String(new FormData(event.currentTarget).get("name") ?? ""));
        }}
        key={name}
      >
        <label>
          Find a cinema
          <input
            type="search"
            name="name"
            placeholder="Search by name"
            defaultValue={name}
          />
        </label>
        <button className="green-button">Find cinemas →</button>
        <a href="/cinemas">Clear</a>
      </form>
      <RequestState {...result} subject="cinemas" />
      {result.data && (
        <>
          {result.data.items.length === 0 && (
            <div className="request-state" role="status">
              <h2>No cinemas found.</h2>
              <p>Try a shorter name, or clear your search.</p>
            </div>
          )}
          <div className="cinema-grid">
            {result.data.items.map((cinema, index) => (
              <article className="cinema-card" key={cinema.id}>
                <span className="cinema-number">
                  CINEMA{" "}
                  {String((page - 1) * result.data!.size + index + 1).padStart(
                    2,
                    "0",
                  )}
                </span>
                <h2>{cinema.name}</h2>
                <address>
                  {[cinema.address, cinema.city].filter(Boolean).join(", ") ||
                    "Address not listed"}
                </address>
                {cinema.website && (
                  <a href={cinema.website} target="_blank" rel="noreferrer">
                    Cinema website ↗
                  </a>
                )}
                <a
                  href={screeningsHref({
                    date: today,
                    page: 1,
                    cinemaId: cinema.id,
                  })}
                >
                  See screenings →
                </a>
              </article>
            ))}
          </div>
          <nav className="screening-pagination" aria-label="Cinema pages">
            <button disabled={page <= 1} onClick={() => change(name, page - 1)}>
              ← Previous
            </button>
            <span>
              Page {page} of {Math.max(1, result.data.pages)} ·{" "}
              {result.data.total} cinemas
            </span>
            <button
              disabled={page >= result.data.pages}
              onClick={() => change(name, page + 1)}
            >
              Next →
            </button>
          </nav>
        </>
      )}
    </>
  );
}
