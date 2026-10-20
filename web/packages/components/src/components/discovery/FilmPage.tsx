import { useCallback, useEffect } from "react";
import {
  MovieNotFoundError,
  type DiscoveryClient,
  type MovieDetailClient,
  type ScreeningQuery,
} from "marquise-client";
import { MoviePoster } from "../movie/MoviePoster";
import { CinemaShowtimeGroups, groupByCinema } from "../movie/CinemaShowtimes";
import { screeningsHref } from "./discovery-state";
import { useResource } from "./use-resource";
import { RequestState, Pagination } from "./RequestState";

export function FilmPage({
  id,
  query,
  client,
  details,
  navigate,
  currentTime,
}: {
  id: string;
  query: ScreeningQuery;
  client: DiscoveryClient;
  details: MovieDetailClient;
  navigate: (href: string) => void;
  currentTime: string;
}) {
  const movie = useResource(
    useCallback(() => details.fetchMovie(id), [details, id]),
  );
  const screenings = useResource(
    useCallback(
      (signal: AbortSignal) =>
        client.fetchShowtimePage(id, query.date, query.page, signal),
      [client, id, query.date, query.page],
    ),
  );
  useEffect(() => {
    document.title = movie.data
      ? `${movie.data.title} — Marquise`
      : movie.error instanceof MovieNotFoundError
        ? "Movie not found — Marquise"
        : movie.error
          ? "Movie unavailable — Marquise"
          : "Movie screenings · Marquise";
  }, [movie.data, movie.error]);
  const setQuery = (date: string, page = 1) =>
    navigate(
      `/movies/${encodeURIComponent(id)}?date=${date}${page > 1 ? `&page=${page}` : ""}`,
    );
  return (
    <div className="film-page">
      <a
        className="back-link"
        href={screeningsHref({ date: query.date, page: 1 })}
      >
        ← Daily screenings
      </a>
      {movie.error instanceof MovieNotFoundError ? (
        <div className="request-state" role="alert">
          <h1>Movie not found.</h1>
          <p>This film may have left the listings. Try the daily screenings.</p>
        </div>
      ) : (
        <RequestState {...movie} subject="movie" />
      )}
      {movie.data && (
        <header className="film-heading">
          <MoviePoster
            title={movie.data.title}
            posterUrl={movie.data.posterUrl}
            className="film-poster"
          />
          <div>
            <p className="eyebrow">ON THE BIG SCREEN</p>
            <h1>{movie.data.title}</h1>
            <p>
              {[
                movie.data.releaseYear,
                movie.data.durationMinutes
                  ? `${movie.data.durationMinutes} min`
                  : null,
                movie.data.directors?.join(", "),
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
            <p className="film-genres">{movie.data.genres?.join(" / ")}</p>
          </div>
        </header>
      )}
      {movie.data && (
        <section className="film-screenings">
          <div className="section-heading">
            <h2>Find your screening</h2>
            <label>
              Date
              <input
                aria-label="Screening date"
                type="date"
                value={query.date}
                onChange={(event) => {
                  if (event.target.value) setQuery(event.target.value);
                }}
              />
            </label>
          </div>
          <p className="page-context">
            Montréal local time. Tickets open on the cinema's site. Started
            screenings are crossed out.
          </p>
          <RequestState {...screenings} />
          {screenings.data && (
            <>
              <CinemaShowtimeGroups
                showLanguage
                groups={groupByCinema(screenings.data.items)}
                currentTime={currentTime}
              />
              {screenings.data.items.length === 0 && (
                <p role="status">
                  No screenings for this date. Try another day.
                </p>
              )}
              <Pagination
                {...screenings.data}
                onPage={(page) => setQuery(query.date, page)}
              />
            </>
          )}
        </section>
      )}
    </div>
  );
}
