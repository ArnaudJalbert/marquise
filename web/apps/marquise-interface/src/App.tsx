import { useCallback, useEffect, useState } from "react";
import { MinimalExperience } from "marquise-components";
import type { BrowseClient } from "marquise-client";
import { createMarquiseClient } from "./api-client";

export interface AppProps {
  client?: BrowseClient;
}

function freshVisitHref(href: string): string {
  const url = new URL(href);
  if (!url.searchParams.has("start") && !url.searchParams.has("end")) return href;
  url.searchParams.delete("start");
  url.searchParams.delete("end");
  return url.href;
}

/** Composition root only. The shared package owns the interface. */
export function App({ client }: AppProps) {
  const [defaultClient] = useState(() => createMarquiseClient());
  const [href, setHref] = useState(() => {
    const fresh = freshVisitHref(window.location.href);
    // Idempotent, so StrictMode's second initializer call is harmless.
    if (fresh !== window.location.href)
      history.replaceState(history.state, "", fresh);
    return fresh;
  });
  const [now, setNow] = useState(() => new Date().toISOString());
  useEffect(() => {
    const onPopState = () => {
      setHref(window.location.href);
      const scrollY =
        typeof history.state?.scrollY === "number" ? history.state.scrollY : 0;
      window.setTimeout(
        () => window.scrollTo({ top: scrollY, behavior: "instant" }),
        0,
      );
    };
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
    const current = new URL(window.location.href);
    const target = new URL(next, window.location.origin);
    if (target.href === window.location.href) return;
    const sameSectionQuery =
      current.pathname === "/" &&
      target.pathname === current.pathname &&
      current.searchParams.get("section") ===
        target.searchParams.get("section");
    history.replaceState(
      { ...history.state, scrollY: window.scrollY },
      "",
      window.location.href,
    );
    history.pushState({ scrollY: 0 }, "", target);
    setHref(target.href);
    if (!sameSectionQuery) {
      document.getElementById("minimal-main")?.focus({ preventScroll: true });
      if (!target.hash) window.scrollTo({ top: 0, behavior: "instant" });
    }
  }, []);
  return (
    <MinimalExperience
      href={href}
      client={client ?? defaultClient}
      navigate={navigate}
      currentTime={now}
    />
  );
}
