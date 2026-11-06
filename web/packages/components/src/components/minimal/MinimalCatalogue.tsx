import { toMontrealIsoDate } from "marquise-client";
import { ArrowRight, ArrowUpRight, X } from "lucide-react";
import { useEffect, useRef, useState, type CSSProperties } from "react";
import type {
  CatalogueCinema,
  CatalogueMovie,
  CatalogueScreening,
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
import {
  addDays,
  relativeDay,
  formatScore,
  timeToHour,
  formatHour,
  decodePathId,
} from "./catalogue-format";
import { MovieSchedule } from "./MovieSchedule";
import { PeriodPicker } from "./PeriodPicker";
import { MovieSearch } from "./MovieSearch";
import { Showtime } from "./Showtime";
import { InfoMenu, SiteFooter, infoPages } from "./SiteInfo";
import marquiseMark from "./marquise-mark.svg";
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

function EndSentinel({
  enabled,
  onReach,
}: {
  enabled: boolean;
  onReach?: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const target = ref.current;
    if (!enabled || !target || !onReach) return;
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) onReach();
    });
    observer.observe(target);
    return () => observer.disconnect();
  }, [enabled, onReach]);
  return <div className="minimal-page-sentinel" ref={ref} aria-hidden="true" />;
}
type UpcomingScreenings = "loading" | "error" | CatalogueScreening[];

/** Upcoming screenings per movie, each loaded at most once while the page lives. */
function useUpcomingScreenings(
  onLoad: MinimalCatalogueProps["onLoadUpcomingScreenings"],
) {
  const [byMovie, setByMovie] = useState<Record<string, UpcomingScreenings>>({});
  const requested = useRef(new Set<string>());
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    const pageController = new AbortController();
    controller.current = pageController;
    return () => pageController.abort();
  }, []);
  const settle = (movieId: string, result: UpcomingScreenings) =>
    setByMovie((current) => ({ ...current, [movieId]: result }));
  return {
    load(movie: CatalogueMovie) {
      const signal = controller.current?.signal;
      if (!onLoad || !signal || requested.current.has(movie.id)) return;
      requested.current.add(movie.id);
      settle(movie.id, "loading");
      onLoad(movie, signal).then(
        (screenings) => settle(movie.id, screenings),
        () => {
          if (!signal.aborted) settle(movie.id, "error");
        },
      );
    },
    movie(movie: CatalogueMovie): CatalogueMovie {
      const result = byMovie[movie.id];
      return Array.isArray(result) ? { ...movie, screenings: result } : movie;
    },
    notice(movieId: string): string | undefined {
      const result = byMovie[movieId];
      if (result === "loading") return "Loading…";
      if (result === "error") return "Couldn't load screenings";
      return undefined;
    },
  };
}

export function MinimalMovieCard({
  movie,
  cinemas,
  expanded,
  onExpanded,
  showYear = false,
  previewNotice,
  emptyNotice = "No matching upcoming screenings.",
  currentTime = new Date().toISOString(),
}: {
  currentTime?: string;
  /** Replaces the times while screenings load or after they fail to load. */
  previewNotice?: string;
  emptyNotice?: string;
  expanded?: boolean;
  showYear?: boolean;
  onExpanded?: (open: boolean) => void;
  movie: CatalogueMovie;
  cinemas: readonly CatalogueCinema[];
}) {
  const [localOpen, setLocalOpen] = useState(false);
  const open = expanded ?? localOpen;
  const setOpen = onExpanded ?? setLocalOpen;
  const arrow = useRef<HTMLButtonElement>(null);
  const now = new Date(currentTime);
  const today = toMontrealIsoDate(now);
  const upcoming = movie.screenings
    .filter((s) => new Date(s.showtime).getTime() > now.getTime())
    .slice().sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time));
  const day = upcoming[0]?.date;
  const nextDay = upcoming.find((s) => s.date !== day)?.date;
  const dayScreenings = upcoming.filter((s) => s.date === day);
  const preview = dayScreenings.slice(0, 4);
  const movieHref = `/movies/${encodeURIComponent(movie.id)}`;
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
      <a
        href={`/movies/${encodeURIComponent(movie.id)}`}
        aria-label={`View ${movie.title}`}
      >
        <Poster movie={movie} />
      </a>
      <div className="minimal-caption">
        <a href={`/movies/${encodeURIComponent(movie.id)}`} title={movie.title}>
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
          <ArrowUpRight aria-hidden size={17} />
        </button>
      </div>
      {showYear && movie.year && (
        <small className="minimal-card-year">{movie.year}</small>
      )}
      {open && (
        <section
          className="minimal-preview"
          id={id}
          aria-label={`${movie.title} screenings`}
        >
          <header className="minimal-preview-header">
            <strong>{day && relativeDay(day, today)}</strong>
            <button
              className="minimal-preview-close"
              aria-label="Close preview"
              onClick={() => {
                setOpen(false);
                arrow.current?.focus();
              }}
            >
              <X aria-hidden size={16} />
            </button>
          </header>
          {previewNotice ? <p role="status">{previewNotice}</p> : preview.length ? preview.map((s, i) => (
            <p key={i}>
              <Showtime screening={s} />
              {cinemas.find((c) => c.id === s.cinemaId)?.name ?? s.cinemaName ?? "Cinema unavailable"}
            </p>
          )) : <p>{emptyNotice}</p>}
          <footer className="minimal-preview-footer">
            {dayScreenings.length > 4 && <><a href={movieHref}>+{dayScreenings.length - 4} more</a>{" · "}</>}
            {nextDay && <>Then {relativeDay(nextDay, today)}{" · "}</>}
            <a href={movieHref}>Schedule</a>
          </footer>
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
}: Pick<
  MinimalCatalogueProps,
  "selection" | "onSelection" | "cinemas" | "screeningLanguages"
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
      <div className="minimal-filter-row">
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
  currentTime,
  catalogueNotice,
  serverResults = false,
  showScreeningFilters = true,
  catalogueSearch,
  onCatalogueSearch,
  catalogueState = "ready",
  catalogueHasMore = false,
  onLoadMoreCatalogue,
  onCatalogueRetry,
  detailNotice,
  directoryNotice,
  cinemas,
  screeningLanguages,
  selection,
  onSelection,
  href,
  navigate,
  today,
  state = "ready",
  hasMore = false,
  onLoadMore,
  onRetry,
  onLoadWeek,
  onLoadUpcomingScreenings,
}: MinimalCatalogueProps) {
  const currentUrl = new URL(href, "http://prototype.invalid");
  const path = currentUrl.pathname;
  const activeSection =
    currentUrl.searchParams.get("section") === "movies"
      ? "movies"
      : "screenings";
  const movieId = /^\/movies\/([^/]+)$/.exec(path)?.[1];
  const decodedMovieId = movieId ? decodePathId(movieId) : undefined;
  const cinemaPathId = /^\/cinemas\/([^/]+)\/?$/.exec(path)?.[1];
  const cinemaId = cinemaPathId ? decodePathId(cinemaPathId) : undefined;
  const movie =
    catalogueMovies.find((m) => m.id === decodedMovieId) ??
    movies.find((m) => m.id === decodedMovieId);
  const [movieSearch, setMovieSearch] = useState("");
  const [previewId, setPreviewId] = useState<string | null>(null);
  const upcoming = useUpcomingScreenings(onLoadUpcomingScreenings);
  const cinema = cinemas.find((c) => c.id === cinemaId);
  const infoPath = path.replace(/(.)\/$/, "$1");
  const infoPage = infoPages[infoPath];
  const from = selection.from
    ? `${String(timeToHour(selection.from, 0)).padStart(2, "0")}:00`
    : "";
  const to = selection.to
    ? `${String(timeToHour(selection.to, 24)).padStart(2, "0")}:00`
    : "";
  const invalid =
    selection.start > selection.end ||
    Boolean(selection.from && selection.to && selection.from > selection.to);
  const matching = serverResults
    ? movies
    : movies
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
  const allMovieMatches = serverResults
    ? catalogueMovies
    : catalogueMovies.filter((item) =>
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
      <a
        href="#minimal-main"
        className="minimal-skip"
        onClick={(event) => {
          // Focus only: a hash change would alter the current route's URL.
          event.preventDefault();
          document.getElementById("minimal-main")?.focus();
        }}
      >
        Skip to content
      </a>
      <header className="minimal-nav">
        <a href="/" className="minimal-wordmark">
          <img
            className="minimal-wordmark-mark"
            src={marquiseMark}
            alt=""
            width="34"
            height="15"
          />
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
        <InfoMenu key={infoPath} path={infoPath} />
      </header>
      <main
        id="minimal-main"
        tabIndex={-1}
        className={infoPage ? "minimal-page" : undefined}
      >
        {infoPage ? (
          <>
            <title>{`${infoPage.title} · Marquise`}</title>
            <infoPage.body />
          </>
        ) : path === "/cinemas" || path === "/cinemas/" ? (
          <>
            <h1>Cinemas</h1>
            <SectionDescription text="Browse Montréal cinemas and open one to see its upcoming showtimes. For example, choose your favorite venue to check what's playing this weekend." />
            {directoryNotice}
            <ul className="minimal-directory">
              {cinemas.map((c) => (
                <li key={c.id}>
                  <a href={`/cinemas/${encodeURIComponent(c.id)}`}>{c.name}</a>
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
                      formatScore(movie.tmdbRating),
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
            (detailNotice ?? <h1>Movie not found</h1>)
          )
        ) : cinemaId && !cinema ? (
          directoryNotice ?? <h1>Cinema not found</h1>
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
                {showScreeningFilters ? (
                  <>
                    <PeriodPicker
                      start={selection.start}
                      end={selection.end}
                      today={today}
                      heading={cinema ? "h2" : "h1"}
                      onChange={(start, end) =>
                        onSelection({ ...selection, start, end })
                      }
                    />
                    <div className="minimal-screenings-top">
                      <MovieSearch
                        value={selection.title}
                        onSearch={(title) => onSelection({ ...selection, title })}
                      />
                    </div>
                    <Filters
                      selection={selection}
                      onSelection={onSelection}
                      screeningLanguages={screeningLanguages}
                      cinemas={cinemas}
                      fixed={cinemaId}
                    />
                  </>
                ) : (
                  <p>{today} · Montréal local time</p>
                )}
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
                ) : state === "error" && !matching.length ? (
                  <div className="minimal-state" role="alert">
                    <p>Could not load screenings.</p>
                    <button onClick={onRetry}>Retry</button>
                  </div>
                ) : (
                  <>
                    {(state === "empty" || !matching.length) &&
                    showScreeningFilters &&
                    selection.start === today &&
                    selection.end === today ? (
                      <div className="minimal-state" role="status">
                        <h2>No screenings left today</h2>
                        <button
                          onClick={() => {
                            const tomorrow = addDays(today, 1);
                            onSelection({
                              ...selection,
                              start: tomorrow,
                              end: tomorrow,
                            });
                          }}
                        >
                          See tomorrow
                          <ArrowRight aria-hidden size={16} />
                        </button>
                      </div>
                    ) : state === "empty" || !matching.length ? (
                      <div className="minimal-state" role="status">
                        <h2>No matching screenings</h2>
                        {showScreeningFilters ? (
                          <>
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
                          </>
                        ) : (
                          <p>
                            No upcoming screenings today.{" "}
                            <a href="/?section=movies">Browse movies</a> to
                            see what screens later.
                          </p>
                        )}
                      </div>
                    ) : (
                      <>
                        <div className="minimal-grid">
                          {matching.map((m) => (
                            <MinimalMovieCard
                              key={m.id}
                              movie={m}
                              currentTime={currentTime}
                              cinemas={cinemas}
                              expanded={previewId === m.id}
                              onExpanded={(open) =>
                                setPreviewId(open ? m.id : null)
                              }
                            />
                          ))}
                        </div>
                        <EndSentinel
                          enabled={
                            hasMore &&
                            state !== "loading-more" &&
                            state !== "error"
                          }
                          onReach={onLoadMore}
                        />
                      </>
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
                <SectionDescription text="Every movie with an upcoming screening in Montréal, soonest first. Search by title to check whether a film you want to see is coming up." />
                {catalogueNotice && <p role="status">{catalogueNotice}</p>}
                <label className="minimal-all-movies-search">
                  <span className="minimal-visually-hidden">Search movies</span>
                  <input
                    type="search"
                    value={catalogueSearch ?? movieSearch}
                    placeholder="Search by title"
                    aria-label="Search movies"
                    onChange={(event) =>
                      onCatalogueSearch
                        ? onCatalogueSearch(event.target.value)
                        : setMovieSearch(event.target.value)
                    }
                  />
                </label>
                {catalogueState === "initial-loading" ? (
                  <p role="status">Loading movies…</p>
                ) : catalogueState === "error" && !catalogueMovies.length ? (
                  <div role="alert">
                    <p>Could not load movies.</p>
                    <button onClick={onCatalogueRetry}>Retry</button>
                  </div>
                ) : allMovieMatches.length ? (
                  <>
                    <div className="minimal-library-grid">
                      {allMovieMatches.map((item) => (
                        <MinimalMovieCard
                          key={item.id}
                          movie={upcoming.movie(item)}
                          currentTime={currentTime}
                          cinemas={cinemas}
                          showYear
                          previewNotice={upcoming.notice(item.id)}
                          emptyNotice="No upcoming screenings"
                          expanded={previewId === item.id}
                          onExpanded={(open) => {
                            setPreviewId(open ? item.id : null);
                            if (open) upcoming.load(item);
                          }}
                        />
                      ))}
                    </div>
                    <EndSentinel
                      enabled={
                        catalogueHasMore &&
                        catalogueState !== "loading-more" &&
                        catalogueState !== "error"
                      }
                      onReach={onLoadMoreCatalogue}
                    />
                    {catalogueState === "loading-more" && (
                      <p role="status" className="minimal-state">
                        Loading more movies…
                      </p>
                    )}
                    {catalogueState === "error" && (
                      <div className="minimal-state" role="alert">
                        <p>
                          Could not load more movies. Your loaded movies are
                          still here.
                        </p>
                        <button onClick={onCatalogueRetry}>Retry</button>
                      </div>
                    )}
                  </>
                ) : (
                  <p role="status">No movies found.</p>
                )}
              </section>
            )}
          </>
        )}
      </main>
      <SiteFooter path={infoPath} />
    </div>
  );
}
