import { useRef, useState } from "react";
import type { MovieCardGridItem } from "marquise-client";
import { MoviePoster } from "../movie/MoviePoster";
import { CinemaShowtimeGroups, groupByCinema } from "../movie/CinemaShowtimes";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "../ui/hover-card";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";

type PosterCardProps = {
  item: MovieCardGridItem;
  date: string;
  currentTime?: string;
};

function PosterPreview({
  item,
  href,
  currentTime,
  onClose,
}: {
  item: MovieCardGridItem;
  href: string;
  currentTime?: string;
  onClose: () => void;
}) {
  return (
    <>
      <div className="preview-heading">
        <h3>{item.movie.title}</h3>
        <button type="button" aria-label="Close preview" onClick={onClose}>
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
      <p className="preview-note">Screenings on this page · Montréal time</p>
      <CinemaShowtimeGroups
        showLanguage
        groups={groupByCinema(item.showtimes ?? [])}
        currentTime={currentTime}
      />
      <a className="preview-all" href={href}>
        Movie details & all screening pages →
      </a>
    </>
  );
}

/** Deliberate hover previews and explicit touch/keyboard previews are independent. */
export function PosterCard({ item, date, currentTime }: PosterCardProps) {
  const [open, setOpen] = useState(false);
  const [hoverOpen, setHoverOpen] = useState(false);
  const href = `${item.showtimesUrl}?date=${date}`;
  return (
    <HoverCard
      open={hoverOpen && !open}
      onOpenChange={(nextOpen) => setHoverOpen(nextOpen && !open)}
      openDelay={250}
      closeDelay={100}
    >
      {/* The trigger spans the whole card so moving onto the overlapping
          Showtimes strip is not a hover leave. Keyboard focus does not open
          the hover card; the Showtimes button owns that preview instead. */}
      <HoverCardTrigger asChild onFocus={(event) => event.preventDefault()}>
        <article className="poster-card">
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
          <Popover
            open={open}
            onOpenChange={(nextOpen) => {
              setOpen(nextOpen);
              if (nextOpen) setHoverOpen(false);
            }}
          >
            <PopoverTrigger asChild>
              <button
                type="button"
                className="poster-preview-button"
                aria-label={`Showtimes for ${item.movie.title}`}
                aria-expanded={open}
              >
                Showtimes <span aria-hidden>↗</span>
              </button>
            </PopoverTrigger>
            <PopoverContent
              className="poster-preview"
              side="bottom"
              align="start"
              collisionPadding={16}
              role="dialog"
              aria-label={`Showtimes for ${item.movie.title}`}
            >
              <PosterPreview
                item={item}
                href={href}
                currentTime={currentTime}
                onClose={() => setOpen(false)}
              />
            </PopoverContent>
          </Popover>
        </article>
      </HoverCardTrigger>
      <HoverCardContent
        className="poster-preview"
        side="bottom"
        align="start"
        collisionPadding={16}
        role="dialog"
        aria-label={`Showtimes for ${item.movie.title}`}
      >
        <PosterPreview
          item={item}
          href={href}
          currentTime={currentTime}
          onClose={() => setHoverOpen(false)}
        />
      </HoverCardContent>
    </HoverCard>
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
