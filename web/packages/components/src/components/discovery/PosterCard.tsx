import { useEffect, useRef, useState } from "react";
import type { MovieCardGridItem } from "marquise-client";
import { MoviePoster } from "../movie/MoviePoster";
import { CinemaShowtimeGroups, groupByCinema } from "../movie/CinemaShowtimes";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";

/** Hover previews have the same explicit button for touch and keyboard users. */
export function PosterCard({
  item,
  date,
  currentTime,
}: {
  item: MovieCardGridItem;
  date: string;
  currentTime?: string;
}) {
  const [open, setOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const preview = useRef<HTMLDivElement>(null);
  const hovering = useRef(false);
  useEffect(() => () => clearTimeout(timer.current), []);
  const href = `${item.showtimesUrl}?date=${date}`;
  const leave = () => {
    if (preview.current?.contains(document.activeElement)) return;
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setOpen(false), 180);
  };
  const enter = () => {
    clearTimeout(timer.current);
    if (!open) hovering.current = true;
    setOpen(true);
  };
  return (
    <article
      className="poster-card"
      onPointerEnter={(event) => {
        if (event.pointerType === "mouse") enter();
      }}
      onPointerLeave={(event) => {
        if (event.pointerType === "mouse") leave();
      }}
    >
      <a
        href={href}
        className="poster-link"
        aria-label={`View ${item.movie.title}`}
      >
        <MoviePoster
          title={item.movie.title}
          posterUrl={item.movie.posterUrl}
        />
      </a>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            className="poster-preview-button"
            aria-label={`Showtimes for ${item.movie.title}`}
            aria-expanded={open}
            onPointerDown={() => {
              hovering.current = false;
            }}
            onKeyDown={() => {
              hovering.current = false;
            }}
          >
            Showtimes <span aria-hidden>↗</span>
          </button>
        </PopoverTrigger>
        <PopoverContent
          ref={preview}
          onOpenAutoFocus={(event) => {
            if (hovering.current) event.preventDefault();
          }}
          onCloseAutoFocus={(event) => {
            if (hovering.current) event.preventDefault();
          }}
          onPointerEnter={(event) => {
            if (event.pointerType === "mouse") enter();
          }}
          onPointerLeave={(event) => {
            if (event.pointerType === "mouse") leave();
          }}
          onFocusCapture={() => clearTimeout(timer.current)}
          onBlurCapture={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget)) leave();
          }}
          className="poster-preview"
          side="bottom"
          align="start"
          collisionPadding={16}
          role="dialog"
          aria-label={`Showtimes for ${item.movie.title}`}
        >
          <div className="preview-heading">
            <h3>{item.movie.title}</h3>
            <button
              type="button"
              aria-label="Close preview"
              onClick={() => setOpen(false)}
            >
              ×
            </button>
          </div>
          <p className="preview-meta">
            {[
              item.movie.releaseYear,
              item.movie.durationMinutes
                ? `${item.movie.durationMinutes} min`
                : null,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          <p className="preview-note">
            Screenings on this page · Montréal time
          </p>
          <CinemaShowtimeGroups
            showLanguage
            groups={groupByCinema(item.showtimes ?? [])}
            currentTime={currentTime}
          />
          <a className="preview-all" href={href}>
            Movie details & all screening pages →
          </a>
        </PopoverContent>
      </Popover>
    </article>
  );
}
export function PosterRail({
  title,
  subtitle,
  items,
  date,
  currentTime,
}: {
  title: string;
  subtitle: string;
  items: readonly MovieCardGridItem[];
  date: string;
  currentTime?: string;
}) {
  const rail = useRef<HTMLDivElement>(null);
  const id = `rail-${title.replace(/[^a-zA-Z]/g, "").toLowerCase()}`;
  return (
    <section className="discovery-section" aria-labelledby={`${id}-title`}>
      <div className="section-heading">
        <div>
          <h2 id={`${id}-title`}>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <div className="rail-controls">
          <button
            aria-label={`Scroll ${title} left`}
            aria-controls={id}
            onClick={() =>
              rail.current?.scrollBy({
                left: -600,
                behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
                  .matches
                  ? "auto"
                  : "smooth",
              })
            }
          >
            ←
          </button>
          <button
            aria-label={`Scroll ${title} right`}
            aria-controls={id}
            onClick={() =>
              rail.current?.scrollBy({
                left: 600,
                behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
                  .matches
                  ? "auto"
                  : "smooth",
              })
            }
          >
            →
          </button>
        </div>
      </div>
      <div
        className="poster-rail"
        id={id}
        ref={rail}
        tabIndex={0}
        role="region"
        aria-label={title}
      >
        {items.map((item) => (
          <PosterCard
            key={item.key ?? item.movie.title}
            item={item}
            date={date}
            currentTime={currentTime}
          />
        ))}
      </div>
    </section>
  );
}
