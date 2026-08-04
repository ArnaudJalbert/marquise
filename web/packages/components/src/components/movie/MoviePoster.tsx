import { useEffect, useState } from "react";

import { cn } from "../../lib/utils";

type MoviePosterProps = {
  title: string;
  posterUrl?: string | null;
  href: string;
} & Omit<React.ComponentPropsWithRef<"a">, "href" | "aria-label">;

/** Poster area: title placeholder behind a lazy, low-priority image, with a loading bar while it fetches. The whole poster links to the movie page. */
export function MoviePoster({
  title,
  posterUrl,
  href,
  ref,
  className,
  ...props
}: MoviePosterProps) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setFailed(false);
    setLoaded(false);
  }, [posterUrl]);

  const isLoading = Boolean(posterUrl) && !loaded && !failed;

  return (
    <a
      ref={ref}
      href={href}
      target="_blank"
      rel="noreferrer"
      aria-label={`Poster for ${title}`}
      className={cn("relative block aspect-[2/3] w-full bg-muted", className)}
      {...props}
    >
      <div className="flex h-full w-full items-center justify-center p-4 text-muted-foreground">
        <p className="text-center text-sm">{title}</p>
      </div>
      {posterUrl && !failed ? (
        <img
          key={posterUrl}
          src={posterUrl}
          alt={`Poster for ${title}`}
          loading="lazy"
          decoding="async"
          fetchPriority="low"
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
          className={cn(
            "absolute inset-0 h-full w-full object-cover transition-opacity duration-300",
            loaded ? "opacity-100" : "opacity-0",
          )}
        />
      ) : null}
      {isLoading ? (
        <div
          role="progressbar"
          aria-label={`Loading poster for ${title}`}
          className="absolute inset-x-0 bottom-0 h-0.5 overflow-hidden bg-border"
        >
          <div className="h-full w-1/3 animate-loading-bar bg-foreground" />
        </div>
      ) : null}
    </a>
  );
}
