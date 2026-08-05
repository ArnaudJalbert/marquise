import { useEffect, useState } from "react";

import { cn } from "../../lib/utils";

type MoviePosterProps = {
  title: string;
  posterUrl?: string | null;
  /** When set, the poster links to this URL in a new tab. */
  href?: string;
  /** When set (and no href), the poster becomes a button calling this on click. */
  onClick?: () => void;
  className?: string;
  ref?: React.Ref<HTMLElement>;
} & Omit<React.HTMLAttributes<HTMLElement>, "onClick" | "className">;

/**
 * Poster area: title placeholder behind a lazy, low-priority image, with a
 * loading bar while it fetches. Renders as a link when `href` is given, as a
 * button when only `onClick` is given, and as a plain block otherwise. Extra
 * HTML props (e.g. pointer handlers from a hover-card trigger) are forwarded.
 */
export function MoviePoster({
  title,
  posterUrl,
  href,
  onClick,
  ref,
  className,
  ...rest
}: MoviePosterProps) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setFailed(false);
    setLoaded(false);
  }, [posterUrl]);

  const isLoading = Boolean(posterUrl) && !loaded && !failed;

  const content = (
    <>
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
    </>
  );

  const baseClass = "relative block aspect-[2/3] w-full bg-muted";

  if (href !== undefined) {
    return (
      <a
        {...rest}
        ref={ref as React.Ref<HTMLAnchorElement>}
        href={href}
        target="_blank"
        rel="noreferrer"
        aria-label={`Poster for ${title}`}
        onClick={onClick}
        className={cn(baseClass, className)}
      >
        {content}
      </a>
    );
  }

  if (onClick !== undefined) {
    return (
      <button
        {...rest}
        ref={ref as React.Ref<HTMLButtonElement>}
        type="button"
        aria-label={`Poster for ${title}`}
        onClick={onClick}
        className={cn(baseClass, "cursor-pointer text-left", className)}
      >
        {content}
      </button>
    );
  }

  return (
    <div {...rest} ref={ref as React.Ref<HTMLDivElement>} className={cn(baseClass, className)}>
      {content}
    </div>
  );
}
