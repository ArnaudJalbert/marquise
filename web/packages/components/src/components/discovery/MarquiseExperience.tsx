import { useEffect } from "react";
import {
  toMontrealIsoDate,
  type DiscoveryClient,
  type MovieDetailClient,
} from "marquise-client";
import { screeningQuery } from "./discovery-state";
import { DiscoveryPage } from "./DiscoveryPage";
import { FilmPage } from "./FilmPage";
import { CinemaDirectory } from "./CinemaDirectory";

export interface MarquiseExperienceProps {
  href: string;
  client: DiscoveryClient;
  movieDetailClient: MovieDetailClient;
  navigate: (href: string) => void;
  currentTime?: string;
  demo?: boolean;
}
/** Shared interface; the delivery app supplies routing and an injected client. */
export function MarquiseExperience({
  href,
  client,
  movieDetailClient,
  navigate,
  currentTime = new Date().toISOString(),
  demo,
}: MarquiseExperienceProps) {
  const url = new URL(href, "https://marquise.invalid");
  const legacyListings =
    url.pathname === "/" &&
    ["date", "cinema", "movie", "language", "from", "to"].some((key) =>
      url.searchParams.has(key),
    );
  const daily = url.pathname === "/screenings" || legacyListings;
  const query = screeningQuery(url, toMontrealIsoDate(new Date(currentTime)));
  const match = /^\/movies\/([^/]+)\/?$/.exec(url.pathname);
  let id: string | undefined;
  try {
    if (match?.[1]) id = decodeURIComponent(match[1]);
  } catch {
    /* Malformed links become not found. */
  }
  useEffect(() => {
    if (!id)
      document.title = daily
        ? "Daily screenings · Marquise"
        : url.pathname === "/cinemas"
          ? "Cinemas · Marquise"
          : url.pathname === "/"
            ? "Marquise · Go see something"
            : "Page not found · Marquise";
  }, [daily, id, url.pathname]);
  return (
    <div
      className="marquise-site"
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
        const anchor = (event.target as Element).closest("a");
        if (
          !anchor ||
          anchor.target ||
          anchor.hasAttribute("download") ||
          anchor.getAttribute("href")?.startsWith("#")
        )
          return;
        const target = new URL(anchor.href);
        if (target.origin !== window.location.origin) return;
        event.preventDefault();
        navigate(`${target.pathname}${target.search}${target.hash}`);
      }}
    >
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="discovery-nav">
        <a href="/" className="discovery-logo" aria-label="Marquise home">
          <span className="logo-mark" aria-hidden>
            <i />
            <i />
            <i />
          </span>
          marquise<span className="logo-period">.</span>
        </a>
        <nav aria-label="Main navigation">
          <a
            href="/"
            aria-current={url.pathname === "/" && !daily ? "page" : undefined}
          >
            Discover
          </a>
          <a href="/screenings" aria-current={daily ? "page" : undefined}>
            Daily screenings
          </a>
          <a
            href="/cinemas"
            aria-current={url.pathname === "/cinemas" ? "page" : undefined}
          >
            Cinemas
          </a>
        </nav>
        <span className="nav-city">
          MONTRÉAL <span aria-hidden>↗</span>
        </span>
      </header>
      {demo && (
        <p className="demo-banner">
          Demo mode · Sample films and screening times, not live listings.
        </p>
      )}
      <main id="main-content" className="discovery-main" tabIndex={-1}>
        {url.pathname === "/" || daily ? (
          <DiscoveryPage
            daily={daily}
            query={query}
            client={client}
            navigate={navigate}
            currentTime={currentTime}
          />
        ) : url.pathname === "/cinemas" ? (
          <CinemaDirectory
            url={url}
            today={toMontrealIsoDate(new Date(currentTime))}
            client={client}
            navigate={navigate}
          />
        ) : id ? (
          <FilmPage
            key={id}
            id={id}
            query={query}
            client={client}
            details={movieDetailClient}
            navigate={navigate}
            currentTime={currentTime}
          />
        ) : (
          <div className="request-state">
            <h1>Wrong screening room.</h1>
            <p>This page doesn't exist.</p>
            <a href="/">Back to discovery →</a>
          </div>
        )}
      </main>
      <footer className="discovery-footer">
        <a className="footer-wordmark" href="/">
          marquise.
        </a>
        <p>Made for going to the movies in Montréal.</p>
        <a href="/screenings">Go see something →</a>
      </footer>
    </div>
  );
}
