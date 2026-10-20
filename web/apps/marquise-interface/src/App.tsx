import { useCallback, useEffect, useState } from "react";
import { MarquiseExperience } from "marquise-components";
import type { DiscoveryClient, MovieDetailClient } from "marquise-client";
import { createMarquiseClient } from "./api-client";

export interface AppProps {
  discoveryClient?: DiscoveryClient;
  movieDetailClient?: MovieDetailClient;
}
/** Composition root only. The shared package owns the interface. */
export function App({ discoveryClient, movieDetailClient }: AppProps) {
  const [defaultClient] = useState(() => createMarquiseClient());
  const [href, setHref] = useState(window.location.href);
  const [now, setNow] = useState(() => new Date().toISOString());
  useEffect(() => {
    const onPopState = () => setHref(window.location.href);
    window.addEventListener("popstate", onPopState);
    const timer = window.setInterval(
      () => setNow(new Date().toISOString()),
      60_000,
    );
    return () => {
      window.removeEventListener("popstate", onPopState);
      window.clearInterval(timer);
    };
  }, []);
  const navigate = useCallback((next: string) => {
    const target = new URL(next, window.location.origin);
    if (target.href === window.location.href) return;
    history.pushState(null, "", target);
    setHref(target.href);
    document.getElementById("main-content")?.focus({ preventScroll: true });
    if (!target.hash) window.scrollTo({ top: 0, behavior: "instant" });
  }, []);
  return (
    <MarquiseExperience
      href={href}
      client={discoveryClient ?? defaultClient}
      movieDetailClient={movieDetailClient ?? defaultClient}
      navigate={navigate}
      currentTime={now}
      demo={
        !discoveryClient && import.meta.env.VITE_MARQUISE_DATA_SOURCE !== "api"
      }
    />
  );
}
