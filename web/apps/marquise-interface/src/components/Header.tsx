import { Logo } from "./Logo";

/** Sticky site header with primary navigation. */
export function Header() {
  return (
    <header className="site-header">
      <Logo />
      <nav className="site-nav" aria-label="Site sections">
        <a href="/">Screenings</a>
      </nav>
    </header>
  );
}
