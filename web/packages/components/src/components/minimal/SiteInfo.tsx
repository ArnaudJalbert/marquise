import { useEffect, useRef, useState, type ReactNode } from "react";

const API_DOCS_URL = "https://marquise-api.fly.dev/docs";
// Public contact address approved by Arnaud for #402.
const CONTACT_EMAIL = "me@arnaudjalbert.com";

/** One destination list feeds both the header Info menu and the footer. */
const destinations = [
  { label: "About", href: "/about" },
  { label: "API docs", href: API_DOCS_URL, external: "marquise-api.fly.dev" },
  { label: "Contact", href: "/contact" },
  { label: "Terms", href: "/terms" },
  { label: "Privacy", href: "/privacy" },
];

function DestinationLinks({ path }: { path: string }) {
  return (
    <ul>
      {destinations.map((d) => (
        <li key={d.label}>
          {d.external ? (
            <a href={d.href} aria-label={`${d.label} (external site: ${d.external})`}>
              {d.label}
              <span aria-hidden="true" className="minimal-external">
                ↗
              </span>
            </a>
          ) : (
            <a href={d.href} aria-current={path === d.href ? "page" : undefined}>
              {d.label}
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}

/** Header disclosure; remount it per route so navigation closes it. */
export function InfoMenu({ path }: { path: string }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    const outside = (event: Event) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("focusin", outside);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("focusin", outside);
    };
  }, [open]);
  return (
    <div
      className="minimal-info"
      ref={root}
      onKeyDown={(event) => {
        if (event.key === "Escape" && open) {
          setOpen(false);
          button.current?.focus();
        }
      }}
    >
      <button
        ref={button}
        type="button"
        aria-expanded={open}
        aria-controls="minimal-info-panel"
        onClick={() => setOpen(!open)}
      >
        Info<span aria-hidden="true"> ▾</span>
      </button>
      <nav
        id="minimal-info-panel"
        aria-label="Site information"
        hidden={!open}
        // Also closes when the chosen link is the current page.
        onClick={(event) => {
          if ((event.target as Element).closest("a")) setOpen(false);
        }}
      >
        <DestinationLinks path={path} />
      </nav>
    </div>
  );
}

export function SiteFooter({ path }: { path: string }) {
  return (
    <footer className="minimal-footer">
      <span className="minimal-footer-name">Marquise</span>
      <nav aria-label="Footer">
        <DestinationLinks path={path} />
      </nav>
    </footer>
  );
}

function Draft({ children }: { children: ReactNode }) {
  return (
    <p className="minimal-draft" role="note">
      {children}
    </p>
  );
}

function About() {
  return (
    <>
      <h1>About Marquise</h1>
      <Draft>Draft copy for review. Wording is not approved.</Draft>
      <p>
        Marquise gathers upcoming showtimes from Montréal cinemas in one place,
        so you can see what is playing without visiting each cinema's site.
      </p>
      <h2>Coverage</h2>
      <p>
        Marquise lists screenings from a selection of Montréal cinemas. Some
        cinemas are not covered yet, and a covered cinema may publish only part
        of its programme in advance.
      </p>
      <h2>Where the information comes from</h2>
      <p>
        Showtimes are read from each cinema's public website or ticketing pages.
        Film details such as synopses, runtimes, and posters come from film
        databases and cinema listings.
      </p>
      <h2>Credits</h2>
      <p>
        Film metadata and images are provided by The Movie Database (TMDB).
        Marquise uses the TMDB API but is not endorsed or certified by TMDB.
      </p>
      <Draft>
        Unconfirmed attribution. Source credits and logos must be checked
        against each source's usage terms before publication.
      </Draft>
      <h2>Schedule limitations</h2>
      <p>
        Cinemas change schedules, add screenings, and cancel shows. A listing
        can be out of date. Confirm the time, language, and format with the
        cinema before you travel.
      </p>
      <h2>Booking</h2>
      <p>
        Marquise does not sell tickets. Booking links take you to the cinema or
        its ticket provider, which handles payment, seating, exchanges, and
        refunds.
      </p>
    </>
  );
}

function Contact() {
  return (
    <>
      <h1>Contact</h1>
      <Draft>Draft copy for review. Wording is not approved.</Draft>
      <p>Write to Marquise by email:</p>
      <p className="minimal-email">
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
      </p>
      <p>
        The address is plain text, so you can copy it into any email
        application.
      </p>
      <h2>Reporting an incorrect showtime</h2>
      <p>Include enough detail to find the listing:</p>
      <ul>
        <li>the film title</li>
        <li>the cinema</li>
        <li>the date and time shown on Marquise</li>
        <li>the screening language</li>
        <li>what the cinema lists instead, with a link if you have one</li>
      </ul>
      <h2>Booking and refund questions</h2>
      <p>
        Marquise does not sell tickets and cannot change or refund a booking.
        Contact the cinema or the ticket provider you booked with.
      </p>
    </>
  );
}

function Placeholder({ title, topics }: { title: string; topics: string[] }) {
  return (
    <>
      <h1>{title}</h1>
      <Draft>
        <strong>Draft placeholder.</strong> This is not a published policy and
        does not describe Marquise's current practices. Final text needs
        separate drafting and review.
      </Draft>
      {topics.map((topic) => (
        <section key={topic}>
          <h2>{topic}</h2>
          <p className="minimal-placeholder-text">
            Placeholder paragraph showing a readable text width for this
            section. Real content will replace it.
          </p>
        </section>
      ))}
    </>
  );
}

/** Information pages by path; titles feed the document title. */
export const infoPages: Record<string, { title: string; body: () => ReactNode }> = {
  "/about": { title: "About", body: About },
  "/contact": { title: "Contact", body: Contact },
  "/terms": {
    title: "Terms",
    body: () => (
      <Placeholder
        title="Terms of use"
        topics={["Using Marquise", "Listing accuracy", "External links", "Changes to these terms"]}
      />
    ),
  },
  "/privacy": {
    title: "Privacy",
    body: () => (
      <Placeholder
        title="Privacy"
        topics={["Information collected", "How it is used", "Third-party services", "Contact"]}
      />
    ),
  },
};
