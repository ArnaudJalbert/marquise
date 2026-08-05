/**
 * Marquise wordmark: an "M" drawn like a marquee sign on a dark tile,
 * followed by the letterspaced serif wordmark.
 */
export function Logo() {
  return (
    <a className="site-logo" href="#" aria-label="Marquise — accueil">
      <svg
        width="30"
        height="30"
        viewBox="0 0 30 30"
        fill="none"
        aria-hidden="true"
      >
        <rect x="1" y="1" width="28" height="28" rx="7" fill="var(--foreground)" />
        <path
          d="M9 21V9l6 6 6-6v12"
          stroke="var(--background)"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="site-logo-text">MARQUISE</span>
    </a>
  );
}
