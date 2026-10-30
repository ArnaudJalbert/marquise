import { useRef, useState, type CSSProperties } from "react";
import type {
  CatalogueCinema,
  CatalogueMovie,
  CatalogueSelection,
  MinimalCatalogueProps,
} from "./catalogue-types";
export type {
  CatalogueCinema,
  CatalogueMovie,
  CatalogueScreening,
  CatalogueSelection,
  CatalogueState,
  MinimalCatalogueProps,
} from "./catalogue-types";
import { timeToHour, formatHour } from "./catalogue-format";
import { MovieSchedule } from "./MovieSchedule";
import { Showtime } from "./Showtime";
import "./minimal.css";

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
function SectionDescription({ text }: { text: string }) {
  return (
    <details className="minimal-section-description">
      <summary>About this section</summary>
      <p>{text}</p>
    </details>
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
      className={`minimal-card${open ? " is-open" : ""}`}
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
          <button
            className="minimal-preview-close"
            aria-label="Close preview"
            onClick={() => {
              setOpen(false);
              arrow.current?.focus();
            }}
          >
            ×
          </button>
          {preview.length ? (
            [...new Set(preview.map((s) => s.cinemaId))].map((cinema) => (
              <div className="minimal-cinema-showtimes" key={cinema}>
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
  const fromHour = timeToHour(s.from, 0);
  const toHour = Math.max(fromHour, timeToHour(s.to, 24));
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
        <button
          aria-pressed={s.start === today && s.end === today}
          className={
            s.start === today && s.end === today
              ? "minimal-shortcut-active"
              : undefined
          }
          onClick={() => change({ start: today, end: today })}
        >
          Today
        </button>
        <button
          aria-pressed={s.start === tomorrow && s.end === tomorrow}
          className={
            s.start === tomorrow && s.end === tomorrow
              ? "minimal-shortcut-active"
              : undefined
          }
          onClick={() => change({ start: tomorrow, end: tomorrow })}
        >
          Tomorrow
        </button>
        <button
          aria-pressed={s.start === weekend[0] && s.end === weekend[1]}
          className={
            s.start === weekend[0] && s.end === weekend[1]
              ? "minimal-shortcut-active"
              : undefined
          }
          onClick={() => change({ start: weekend[0], end: weekend[1] })}
        >
          This weekend
        </button>
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
              <legend>Daily time</legend>
              <div className="minimal-time-range-control">
                <div className="minimal-time-range-values">
                  <span>From {formatHour(fromHour)}</span>
                  <span>To {formatHour(toHour)}</span>
                </div>
                <div
                  className="minimal-time-range"
                  style={
                    {
                      "--range-start": `${(fromHour / 24) * 100}%`,
                      "--range-end": `${(toHour / 24) * 100}%`,
                    } as CSSProperties
                  }
                >
                  <input
                    type="range"
                    min="0"
                    max="24"
                    step="1"
                    value={fromHour}
                    aria-label="Start time"
                    aria-valuetext={formatHour(fromHour)}
                    onChange={(event) => {
                      const hour = Math.min(Number(event.target.value), toHour);
                      change({
                        from:
                          hour === 0
                            ? ""
                            : `${String(hour).padStart(2, "0")}:00`,
                      });
                    }}
                  />
                  <input
                    type="range"
                    min="0"
                    max="24"
                    step="1"
                    value={toHour}
                    aria-label="End time"
                    aria-valuetext={formatHour(toHour)}
                    onChange={(event) => {
                      const hour = Math.max(
                        Number(event.target.value),
                        fromHour,
                      );
                      change({
                        to:
                          hour === 24
                            ? ""
                            : `${String(hour).padStart(2, "0")}:00`,
                      });
                    }}
                  />
                </div>
                <div className="minimal-time-range-ticks" aria-hidden="true">
                  <span>Midnight</span>
                  <span>6 AM</span>
                  <span>Noon</span>
                  <span>6 PM</span>
                  <span>Midnight</span>
                </div>
              </div>
            </fieldset>
            <div className="minimal-filter-actions">
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
          </div>
        </details>
      </div>
    </section>
  );
}
export function MinimalCatalogue({
  movies,
  catalogueMovies = movies,
  catalogueNotice,
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
  onLoadWeek,
}: MinimalCatalogueProps) {
  const currentUrl = new URL(href, "http://prototype.invalid");
  const path = currentUrl.pathname;
  const activeSection =
    currentUrl.searchParams.get("section") === "movies"
      ? "movies"
      : "screenings";
  const movieId = /^\/movies\/([^/]+)$/.exec(path)?.[1];
  const cinemaId = /^\/cinemas\/([^/]+)$/.exec(path)?.[1];
  const movie =
    catalogueMovies.find((m) => m.id === movieId) ??
    movies.find((m) => m.id === movieId);
  const [movieSearch, setMovieSearch] = useState("");
  const cinema = cinemas.find((c) => c.id === cinemaId);
  const from = selection.from
    ? `${String(timeToHour(selection.from, 0)).padStart(2, "0")}:00`
    : "";
  const to = selection.to
    ? `${String(timeToHour(selection.to, 24)).padStart(2, "0")}:00`
    : "";
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
              (s.language !== undefined &&
                selection.languages.includes(s.language))) &&
            (!from || s.time >= from) &&
            (!to || s.time <= to),
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
  const allMovieMatches = catalogueMovies.filter((item) =>
    item.title.toLowerCase().includes(movieSearch.trim().toLowerCase()),
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
          <a
            href="/?section=screenings"
            aria-current={
              path === "/" && activeSection === "screenings"
                ? "page"
                : undefined
            }
          >
            Screenings
          </a>
          <a
            href="/?section=movies"
            aria-current={
              (path === "/" && activeSection === "movies") || movieId
                ? "page"
                : undefined
            }
          >
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
            <SectionDescription text="Browse Montréal cinemas and open one to see its upcoming showtimes. For example, choose your favorite venue to check what's playing this weekend." />
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
              <a href="/?section=movies">Back to movies</a>
              <div className="minimal-detail">
                <Poster key={movie.id} movie={movie} />
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
              <MovieSchedule
                key={movie.id}
                movie={movie}
                cinemas={cinemas}
                screeningLanguages={screeningLanguages}
                today={today}
                onLoadWeek={onLoadWeek}
              />
            </>
          ) : (
            <h1>Movie not found</h1>
          )
        ) : cinemaId && !cinema ? (
          <h1>Cinema not found</h1>
        ) : (
          <>
            {(cinemaId || activeSection === "screenings") && (
              <>
                <SectionDescription
                  text={
                    cinema
                      ? "Browse upcoming showtimes at this cinema, with filters for date, time, and language. For example, choose Friday evening to see what's on."
                      : "Find movies with showtimes in a date range you choose. For example, set Monday to Friday next week to see what's playing, then filter by cinema or language."
                  }
                />
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
                    Loading screenings…
                    <div className="minimal-grid">
                      {[0, 1, 2].map((i) => (
                        <div
                          key={i}
                          className="minimal-poster minimal-skeleton"
                        />
                      ))}
                    </div>
                  </div>
                ) : (
                  <>
                    {state === "empty" || !matching.length ? (
                      <div className="minimal-state" role="status">
                        <h2>No matching screenings</h2>
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
                          Could not load more movies. Your loaded movies are
                          still here.
                        </p>
                        <button onClick={onRetry}>Retry</button>
                      </div>
                    )}
                  </>
                )}
              </>
            )}
            {!cinemaId && activeSection === "movies" && (
              <section className="minimal-all-movies" aria-label="Movies">
                <SectionDescription text="Search the full movie catalogue, including films with no showtimes on your selected dates. For example, look up a movie you want to see and check whether it will screen soon." />
                {catalogueNotice && <p role="status">{catalogueNotice}</p>}
                <label className="minimal-all-movies-search">
                  <span className="minimal-visually-hidden">Search movies</span>
                  <input
                    type="search"
                    value={movieSearch}
                    placeholder="Search by title"
                    aria-label="Search movies"
                    onChange={(event) => setMovieSearch(event.target.value)}
                  />
                </label>
                {allMovieMatches.length ? (
                  <div className="minimal-library-grid">
                    {allMovieMatches.map((item) => (
                      <article className="minimal-library-card" key={item.id}>
                        <a
                          href={`/movies/${item.id}`}
                          aria-label={`View ${item.title}`}
                        >
                          <Poster movie={item} />
                          <strong>{item.title}</strong>
                          {item.year && <small>{item.year}</small>}
                        </a>
                      </article>
                    ))}
                  </div>
                ) : (
                  <p role="status">No movies found.</p>
                )}
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
