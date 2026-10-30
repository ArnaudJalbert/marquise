import { useRef, useState } from "react";
import "./minimal.css";

export interface CatalogueCinema {
  id: string;
  name: string;
  address?: string;
  website?: string;
}
export interface CatalogueScreening {
  cinemaId: string;
  date: string;
  time: string;
  language: string;
  bookingUrl?: string;
}
export interface CatalogueMovie {
  id: string;
  title: string;
  poster?: string;
  year?: number;
  director?: string;
  runtime?: number;
  synopsis?: string;
  screenings: readonly CatalogueScreening[];
}
export type CatalogueState =
  | "ready"
  | "initial-loading"
  | "loading-more"
  | "empty"
  | "error";
export interface CatalogueSelection {
  start: string;
  end: string;
  title: string;
  cinemas: string[];
  languages: string[];
  from: string;
  to: string;
}
export interface MinimalCatalogueProps {
  movies: readonly CatalogueMovie[];
  cinemas: readonly CatalogueCinema[];
  screeningLanguages: readonly string[];
  selection: CatalogueSelection;
  onSelection: (selection: CatalogueSelection) => void;
  href: string;
  navigate: (href: string) => void;
  today: string;
  tomorrow: string;
  weekend: readonly [string, string];
  state?: CatalogueState;
  onRetry: () => void;
}

function Showtime({ screening }: { screening: CatalogueScreening }) {
  return (
    <span className="minimal-time">
      {screening.bookingUrl ? (
        <a
          href={screening.bookingUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          {screening.time}
        </a>
      ) : (
        <span>{screening.time}</span>
      )}{" "}
      <small>{screening.language}</small>
    </span>
  );
}
function Poster({ movie }: { movie: CatalogueMovie }) {
  const [failed, setFailed] = useState(false);
  return movie.poster && !failed ? (
    <img
      className="minimal-poster"
      src={movie.poster}
      alt={movie.title}
      onError={() => setFailed(true)}
    />
  ) : (
    <div
      className="minimal-poster minimal-missing"
      role="img"
      aria-label={`Poster unavailable for ${movie.title}`}
    >
      Poster unavailable
    </div>
  );
}
export function MinimalMovieCard({
  movie,
  cinemas,
}: {
  movie: CatalogueMovie;
  cinemas: readonly CatalogueCinema[];
}) {
  const [open, setOpen] = useState(false);
  const arrow = useRef<HTMLButtonElement>(null);
  const preview = movie.screenings.slice(0, 3);
  const id = `preview-${movie.id}`;
  return (
    <article
      className="minimal-card"
      onPointerEnter={(event) => {
        if (event.pointerType === "mouse") setOpen(true);
      }}
      onPointerLeave={(event) => {
        if (
          event.pointerType === "mouse" &&
          !arrow.current?.closest("article")?.contains(document.activeElement)
        )
          setOpen(false);
      }}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          setOpen(false);
          arrow.current?.focus();
        }
      }}
    >
      <a href={`/movies/${movie.id}`} aria-label={`View ${movie.title}`}>
        <Poster movie={movie} />
      </a>
      <div className="minimal-caption">
        <a href={`/movies/${movie.id}`} title={movie.title}>
          {movie.title}
        </a>
        <button
          ref={arrow}
          type="button"
          aria-label={`Preview ${movie.title}`}
          aria-expanded={open}
          aria-controls={id}
          onClick={() => setOpen(!open)}
        >
          ↗
        </button>
      </div>
      {open && (
        <section
          className="minimal-preview"
          id={id}
          aria-label={`${movie.title} screenings`}
        >
          <div className="minimal-preview-heading">
            <strong>Next screenings</strong>
            <button
              aria-label="Close preview"
              onClick={() => {
                setOpen(false);
                arrow.current?.focus();
              }}
            >
              ×
            </button>
          </div>
          {preview.length ? (
            [...new Set(preview.map((s) => s.cinemaId))].map((cinema) => (
              <div key={cinema}>
                <h3>
                  {cinemas.find((c) => c.id === cinema)?.name ??
                    "Cinema unavailable"}
                </h3>
                {preview
                  .filter((s) => s.cinemaId === cinema)
                  .map((s, i) => (
                    <p key={i}>
                      {s.date} <Showtime screening={s} />
                    </p>
                  ))}
              </div>
            ))
          ) : (
            <p>No matching upcoming screenings.</p>
          )}
          <a href={`/movies/${movie.id}`}>Full schedule</a>
        </section>
      )}
    </article>
  );
}
function Filters({
  selection: s,
  onSelection,
  cinemas,
  screeningLanguages,
  fixed,
  today,
  tomorrow,
  weekend,
}: Pick<
  MinimalCatalogueProps,
  | "selection"
  | "onSelection"
  | "cinemas"
  | "screeningLanguages"
  | "today"
  | "tomorrow"
  | "weekend"
> & { fixed?: string }) {
  const change = (patch: Partial<CatalogueSelection>) =>
    onSelection({ ...s, ...patch });
  const toggle = (key: "cinemas" | "languages", value: string) =>
    change({
      [key]: s[key].includes(value)
        ? s[key].filter((v) => v !== value)
        : [...s[key], value],
    });
  return (
    <section className="minimal-filters" aria-label="Movie filters">
      <div className="minimal-search-dates">
        <label>
          Movie title
          <input
            type="search"
            value={s.title}
            placeholder="Search movies"
            onChange={(e) => change({ title: e.target.value })}
          />
        </label>
        <label>
          Start date
          <input
            type="date"
            value={s.start}
            onChange={(e) => change({ start: e.target.value })}
          />
        </label>
        <label>
          End date
          <input
            type="date"
            value={s.end}
            onChange={(e) => change({ end: e.target.value })}
          />
        </label>
      </div>
      <div className="minimal-shortcuts">
        <button onClick={() => change({ start: today, end: today })}>
          Today
        </button>
        <button onClick={() => change({ start: tomorrow, end: tomorrow })}>
          Tomorrow
        </button>
        <button onClick={() => change({ start: weekend[0], end: weekend[1] })}>
          This weekend
        </button>
      </div>
      <details
        className="minimal-other-filters"
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            event.currentTarget.open = false;
            event.currentTarget.querySelector("summary")?.focus();
          }
        }}
      >
        <summary>
          Filters
          {s.cinemas.length + s.languages.length > 0 || s.from || s.to
            ? " •"
            : ""}
        </summary>
        <div className="minimal-filter-panels">
          {!fixed && (
            <fieldset>
              <legend>Cinemas</legend>
              {cinemas.map((c) => (
                <label key={c.id}>
                  <input
                    type="checkbox"
                    checked={s.cinemas.includes(c.id)}
                    onChange={() => toggle("cinemas", c.id)}
                  />
                  {c.name}
                </label>
              ))}
            </fieldset>
          )}
          <fieldset>
            <legend>Screening language</legend>
            {screeningLanguages.map((l) => (
              <label key={l}>
                <input
                  type="checkbox"
                  checked={s.languages.includes(l)}
                  onChange={() => toggle("languages", l)}
                />
                {l}
              </label>
            ))}
          </fieldset>
          <fieldset>
            <legend>Daily start time</legend>
            <label>
              From
              <input
                type="time"
                value={s.from}
                onChange={(e) => change({ from: e.target.value })}
              />
            </label>
            <label>
              To
              <input
                type="time"
                value={s.to}
                onChange={(e) => change({ to: e.target.value })}
              />
            </label>
          </fieldset>
          <button
            onClick={() =>
              change({
                title: "",
                cinemas: [],
                languages: [],
                from: "",
                to: "",
              })
            }
          >
            Clear filters
          </button>
        </div>
      </details>
    </section>
  );
}
export function MinimalCatalogue({
  movies,
  cinemas,
  screeningLanguages,
  selection,
  onSelection,
  href,
  navigate,
  today,
  tomorrow,
  weekend,
  state = "ready",
  onRetry,
}: MinimalCatalogueProps) {
  const path = new URL(href, "http://prototype.invalid").pathname;
  const movieId = /^\/movies\/([^/]+)$/.exec(path)?.[1];
  const cinemaId = /^\/cinemas\/([^/]+)$/.exec(path)?.[1];
  const movie = movies.find((m) => m.id === movieId);
  const cinema = cinemas.find((c) => c.id === cinemaId);
  const invalid =
    selection.start > selection.end ||
    Boolean(selection.from && selection.to && selection.from > selection.to);
  const matching = movies
    .map((m) => ({
      ...m,
      screenings: m.screenings
        .filter(
          (s) =>
            s.date >= selection.start &&
            s.date <= selection.end &&
            (!cinemaId || s.cinemaId === cinemaId) &&
            (!selection.cinemas.length ||
              cinemaId ||
              selection.cinemas.includes(s.cinemaId)) &&
            (!selection.languages.length ||
              selection.languages.includes(s.language)) &&
            (!selection.from || s.time >= selection.from) &&
            (!selection.to || s.time <= selection.to),
        )
        .sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time)),
    }))
    .filter(
      (m) =>
        m.title.toLowerCase().includes(selection.title.toLowerCase()) &&
        m.screenings.length,
    )
    .sort(
      (a, b) =>
        (
          (a.screenings[0]?.date ?? "") + (a.screenings[0]?.time ?? "")
        ).localeCompare(
          (b.screenings[0]?.date ?? "") + (b.screenings[0]?.time ?? ""),
        ) || a.id.localeCompare(b.id),
    );
  return (
    <div
      className="minimal-site"
      onClick={(event) => {
        if (
          event.defaultPrevented ||
          event.button !== 0 ||
          event.metaKey ||
          event.ctrlKey ||
          event.shiftKey ||
          event.altKey
        )
          return;
        const a = (event.target as Element).closest("a");
        if (a && !a.target && a.getAttribute("href")?.startsWith("/")) {
          event.preventDefault();
          navigate(a.getAttribute("href")!);
        }
      }}
    >
      <a href="#minimal-main" className="minimal-skip">
        Skip to content
      </a>
      <header className="minimal-nav">
        <a href="/" className="minimal-wordmark">
          Marquise
        </a>
        <nav aria-label="Main navigation">
          <a href="/" aria-current={path === "/" ? "page" : undefined}>
            Movies
          </a>
          <a
            href="/cinemas"
            aria-current={path.startsWith("/cinemas") ? "page" : undefined}
          >
            Cinemas
          </a>
        </nav>
      </header>
      <main id="minimal-main" tabIndex={-1}>
        {path === "/cinemas" ? (
          <>
            <h1>Cinemas</h1>
            <ul className="minimal-directory">
              {cinemas.map((c) => (
                <li key={c.id}>
                  <a href={`/cinemas/${c.id}`}>{c.name}</a>
                </li>
              ))}
            </ul>
          </>
        ) : movieId ? (
          movie ? (
            <>
              <a href="/">Back to movies</a>
              <div className="minimal-detail">
                <Poster movie={movie} />
                <div>
                  <h1>{movie.title}</h1>
                  <p>
                    {[
                      movie.year,
                      movie.director,
                      movie.runtime ? `${movie.runtime} min` : undefined,
                    ]
                      .filter(Boolean)
                      .join(" · ") || "Movie metadata unavailable"}
                  </p>
                  <p>{movie.synopsis ?? "Synopsis unavailable."}</p>
                </div>
              </div>
              <h2>Upcoming screenings</h2>
              <p>
                Montréal local time. Complete sample schedule, no listing
                filters.
              </p>
              {[...new Set(movie.screenings.map((s) => s.date))]
                .sort()
                .map((date) => (
                  <section className="minimal-schedule" key={date}>
                    <h3>{date}</h3>
                    {cinemas
                      .filter((c) =>
                        movie.screenings.some(
                          (s) => s.date === date && s.cinemaId === c.id,
                        ),
                      )
                      .map((c) => (
                        <div key={c.id}>
                          <h4>{c.name}</h4>
                          {movie.screenings
                            .filter(
                              (s) => s.date === date && s.cinemaId === c.id,
                            )
                            .map((s, i) => (
                              <Showtime key={i} screening={s} />
                            ))}
                        </div>
                      ))}
                  </section>
                ))}
            </>
          ) : (
            <h1>Movie not found</h1>
          )
        ) : cinemaId && !cinema ? (
          <h1>Cinema not found</h1>
        ) : (
          <>
            {cinema && (
              <header className="minimal-cinema">
                <h1>{cinema.name}</h1>
                <p>{cinema.address ?? "Address unavailable"}</p>
                {cinema.website && (
                  <a
                    href={cinema.website}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Cinema website
                  </a>
                )}
              </header>
            )}
            <Filters
              selection={selection}
              onSelection={onSelection}
              screeningLanguages={screeningLanguages}
              cinemas={cinemas}
              fixed={cinemaId}
              today={today}
              tomorrow={tomorrow}
              weekend={weekend}
            />
            {invalid ? (
              <p role="alert">
                Start must be before end. Choose a valid date and daily time
                range.
              </p>
            ) : state === "initial-loading" ? (
              <div role="status" className="minimal-state">
                Loading movies…
                <div className="minimal-grid">
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="minimal-poster minimal-skeleton" />
                  ))}
                </div>
              </div>
            ) : (
              <>
                {state === "empty" || !matching.length ? (
                  <div className="minimal-state" role="status">
                    <h2>No matching movies</h2>
                    <p>Try another date or clear your filters.</p>
                    <button
                      onClick={() =>
                        onSelection({
                          start: today,
                          end: today,
                          title: "",
                          cinemas: [],
                          languages: [],
                          from: "",
                          to: "",
                        })
                      }
                    >
                      Reset selection
                    </button>
                  </div>
                ) : (
                  <div className="minimal-grid">
                    {matching.map((m) => (
                      <MinimalMovieCard
                        key={m.id}
                        movie={m}
                        cinemas={cinemas}
                      />
                    ))}
                  </div>
                )}
                {state === "loading-more" && (
                  <p role="status" className="minimal-state">
                    Loading more movies…
                  </p>
                )}
                {state === "error" && (
                  <div className="minimal-state" role="alert">
                    <p>
                      Could not load more movies. Your loaded movies are still
                      here.
                    </p>
                    <button onClick={onRetry}>Retry</button>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
