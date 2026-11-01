import { useEffect, useRef, useState, type ReactNode } from "react";
import tmdbLogo from "./tmdb-logo.svg";

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
      <Draft>Draft copy for review. Wording is not approved for publication.</Draft>
      <p>
        Marquise is a free, non-commercial personal project that brings
        Montréal showtimes together. Browse films, screenings, and cinemas,
        then book directly with the cinema or ticket provider.
      </p>
      <h2>Coverage</h2>
      <p>
        Marquise lists screenings from a selection of Montréal cinemas. Some
        cinemas are not covered yet, and a covered cinema may publish only part
        of its programme in advance.
      </p>
      <h2>Where the information comes from</h2>
      <p>
        Showtimes come from Cineplex and the other cinemas listed on the{" "}
        <a href="/cinemas">Cinemas page</a>. Film details, posters, and scores
        come from The Movie Database (TMDB) and cinema sources.
      </p>
      <h2>Independent project</h2>
      <p>
        Marquise is not officially affiliated with Cineplex, TMDB, or any
        cinema, ticket provider, or other source website referenced here.
        Names and links identify sources and booking destinations, not
        partnerships or endorsements.
      </p>
      <h2>Credits</h2>
      <p>
        This website uses TMDB and the TMDB APIs but is not endorsed,
        certified, or otherwise approved by TMDB.
      </p>
      <p>
        <a className="minimal-tmdb-credit" href="https://www.themoviedb.org">
          <img
            className="minimal-tmdb-logo"
            src={tmdbLogo}
            alt="The Movie Database (TMDB)"
            width="100"
            height="13"
          />
        </a>
      </p>
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

function Terms() {
  return (
    <>
      <h1>Terms of use</h1>
      <Draft>
        Draft for review. These terms have not been approved for publication.
      </Draft>
      <h2>Using Marquise</h2>
      <p>
        Marquise is a free, non-commercial personal guide to Montréal showtimes.
        Listings may be incomplete, incorrect, or out of date. Confirm details
        with the cinema before booking or travelling.
      </p>
      <h2>Bookings and payments</h2>
      <p>
        Marquise does not sell tickets or handle payments. Bookings,
        cancellations, refunds, and admission conditions are handled by the
        cinema or ticket provider. Contact them directly about those matters.
      </p>
      <h2>Independent project and third-party content</h2>
      <p>
        Marquise is not officially affiliated with Cineplex, TMDB, or any
        cinema, ticket provider, or other source website referenced here.
        Names and links do not imply partnerships or endorsements.
      </p>
      <p>
        Film data and images remain subject to the rights of their respective
        owners. Display on Marquise does not grant permission to reuse
        third-party material.
      </p>
      <h2>Public API</h2>
      <p>
        The public API is intended for independent applications as well as
        Marquise. API availability does not grant additional rights to
        third-party data, descriptions, or images. Check the applicable
        source terms and attribution requirements before reusing content.
        See the <a href="/about">source credits</a>.
      </p>
      <h2>Availability and your rights</h2>
      <p>
        The website and API are provided as available, without a guarantee of
        accuracy or uninterrupted service. The API may change or be
        rate-limited. Nothing in these terms excludes rights or remedies that
        applicable law does not allow us to exclude.
      </p>
      <h2>Contact and changes</h2>
      <p>
        Questions: <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
        These terms may change.
      </p>
      <p>Draft prepared November 1, 2026.</p>
    </>
  );
}

function Privacy() {
  return (
    <>
      <h1>Privacy</h1>
      <Draft>
        Draft for review. This policy has not been approved for publication.
      </Draft>
      <h2>Browsing Marquise</h2>
      <p>
        Public browsing does not require an account. The Marquise application
        has no advertising or analytics and does not set cookies or save
        preferences in browser storage.
      </p>
      <h2>Requests and hosting</h2>
      <p>
        Web servers and our hosting provider, Fly.io, process connection and
        request information to deliver, protect, and troubleshoot the service.
        Server logs can include client addresses, requested paths and query
        strings, response status, timestamps, referrers, and browser information.
      </p>
      <p>
        The API also records request identifiers and response times. Its
        separate request-completion log does not include explicit IP-address
        or query-string fields. In-memory counters use the client address
        available to the API to limit excessive requests.
      </p>
      <p>
        Service providers may process information outside Québec. See{" "}
        <a href="https://fly.io/legal/privacy-policy/">Fly.io&apos;s privacy statement</a>.
      </p>
      <h2>External images and links</h2>
      <p>
        Posters load from TMDB and some cinemas&apos; image servers. Those
        services receive your IP address and technical request information
        when your browser loads their images. Their privacy practices apply
        to those requests. Booking links take you to cinema or ticket-provider
        websites, where their privacy policies apply.
      </p>
      <h2>Authorized editors</h2>
      <p>
        Authorized editing uses authenticated accounts separately from public
        browsing. Account identifiers and a history of changes support access
        control, traceability, and reliable handling of editing requests.
      </p>
      <h2>Email</h2>
      <p>
        If you email <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>,
        your address and message are used to respond to your request and
        address reported problems. The contact address forwards to Arnaud
        Jalbert&apos;s personal inbox. The services forwarding, delivering,
        and storing the message also process it. Please do not send sensitive
        information that is unnecessary for your request.
      </p>
      <h2>Privacy questions and requests</h2>
      <p>
        Arnaud Jalbert is responsible for the protection of personal
        information for Marquise. Contact him at{" "}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a> for privacy
        questions, complaints, or requests to access, correct, or delete
        personal information, or to withdraw consent where applicable.
        Requests are handled subject to applicable rights and retention
        obligations.
      </p>
      <p>Draft prepared November 1, 2026.</p>
    </>
  );
}

/** Information pages by path; titles feed the document title. */
export const infoPages: Record<string, { title: string; body: () => ReactNode }> = {
  "/about": { title: "About", body: About },
  "/contact": { title: "Contact", body: Contact },
  "/terms": {
    title: "Terms",
    body: Terms,
  },
  "/privacy": {
    title: "Privacy",
    body: Privacy,
  },
};
