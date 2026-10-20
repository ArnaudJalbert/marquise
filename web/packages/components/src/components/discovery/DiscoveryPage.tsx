import { useCallback } from "react";
import type {
  DiscoveryClient,
  ScreeningPage,
  ScreeningQuery,
} from "marquise-client";
import { PosterCard, PosterRail } from "./PosterCard";
import { screeningsHref, screeningValidation } from "./discovery-state";
import { useResource } from "./use-resource";
import { RequestState, Pagination } from "./RequestState";
import { FilterForm } from "./FilterForm";

export function DiscoveryPage({
  daily,
  query,
  client,
  navigate,
  currentTime,
}: {
  daily: boolean;
  query: ScreeningQuery;
  client: DiscoveryClient;
  navigate: (href: string) => void;
  currentTime: string;
}) {
  const queryKey = JSON.stringify(query);
  const validation = screeningValidation(query);
  const result = useResource(
    useCallback(
      (signal: AbortSignal) =>
        validation
          ? Promise.resolve<ScreeningPage>({
              items: [],
              page: query.page,
              size: 48,
              total: 0,
              pages: 0,
              screeningCount: 0,
            })
          : client.fetchScreeningPage(
              JSON.parse(queryKey) as ScreeningQuery,
              signal,
            ),
      [client, queryKey, validation, query.page],
    ),
  );
  const data = validation ? undefined : result.data;
  const items = data?.items ?? [];
  const genreCounts = new Map<string, number>();
  for (const item of items)
    for (const genre of item.movie.genres ?? [])
      genreCounts.set(genre, (genreCounts.get(genre) ?? 0) + 1);
  const genres = [...genreCounts]
    .filter(([, count]) => count >= 2)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  return (
    <>
      {daily ? (
        <header className="listings-intro">
          <p className="eyebrow">THE CITY'S BIG SCREENS</p>
          <h1>Make a night of it.</h1>
          <p>One date. All kinds of cinema. Find the screening that fits.</p>
        </header>
      ) : (
        <header className="discovery-hero">
          <p className="eyebrow">
            <span className="live-dot" /> MONTRÉAL, MEET YOUR NEXT MOVIE
          </p>
          <h1>
            Less scrolling.
            <br />
            More <em>“that was a good movie.”</em>
          </h1>
          <p>
            Find what's playing around Montréal, pick your screening,
            <br className="desktop-break" /> and give your couch the night off.
          </p>
          <a className="green-button" href={screeningsHref(query)}>
            Find a screening <span aria-hidden>↗</span>
          </a>
          <p className="hero-aside">
            No account. No algorithmic soul-searching. Just the movies.
          </p>
        </header>
      )}
      {daily && (
        <FilterForm
          key={queryKey}
          query={query}
          client={client}
          onApply={(next) => navigate(screeningsHref(next))}
        />
      )}
      {validation ? (
        <p role="alert" className="filter-validation">
          {validation}
        </p>
      ) : (
        <RequestState {...result} />
      )}
      {data && (
        <>
          {items.length === 0 ? (
            <div className="request-state" role="status">
              <h2>No screenings in this frame.</h2>
              <p>
                Try another date or loosen a filter. The city hasn't run out of
                movies.
              </p>
              <a href={screeningsHref({ date: query.date, page: 1 })}>
                Show all screenings for this date →
              </a>
            </div>
          ) : daily ? (
            <section className="discovery-section">
              <div className="section-heading">
                <div>
                  <h2>On the big screen</h2>
                  <p>
                    {data.screeningCount} screenings on this page ·{" "}
                    {items.length} films · {query.date}
                  </p>
                </div>
              </div>
              <div className="daily-poster-grid">
                {items.map((item) => (
                  <PosterCard
                    key={item.key}
                    item={item}
                    date={query.date}
                    currentTime={currentTime}
                  />
                ))}
              </div>
            </section>
          ) : (
            <>
              <PosterRail
                title="Playing around town"
                subtitle={`A slice of ${query.date} · ${data.screeningCount} screenings from page ${data.page}`}
                items={items}
                date={query.date}
                currentTime={currentTime}
              />
              <div className="how-it-works">
                <p>
                  <span>01</span> Follow a poster.
                  <small>Something catch your eye? Trust it.</small>
                </p>
                <p>
                  <span>02</span> Find your seat.
                  <small>
                    Check cinemas and times, then book with the cinema.
                  </small>
                </p>
                <p>
                  <span>03</span> Leave the house.
                  <small>Yes, the popcorn is a valid dinner plan.</small>
                </p>
              </div>
              {genres.map(([genre]) => (
                <PosterRail
                  key={genre}
                  title={`${genre}, anyone?`}
                  subtitle="On this page"
                  items={items.filter((item) =>
                    item.movie.genres?.includes(genre),
                  )}
                  date={query.date}
                  currentTime={currentTime}
                />
              ))}
              <aside className="discovery-callout">
                <div>
                  <p className="eyebrow">PICKY IS A PERFECTLY GOOD PLAN</p>
                  <h2>Your cinema. Your time. Your kind of night.</h2>
                  <p>
                    Want a specific title, language or an early escape? The
                    daily listings do the legwork.
                  </p>
                </div>
                <a href={screeningsHref(query)}>Explore daily screenings →</a>
              </aside>
            </>
          )}
          <p className="page-context">
            Posters group this page’s screenings. A film can appear on more than
            one page.
          </p>
          <Pagination
            {...data}
            onPage={(page) =>
              navigate(
                daily ? screeningsHref({ ...query, page }) : `/?page=${page}`,
              )
            }
          />
        </>
      )}
    </>
  );
}
