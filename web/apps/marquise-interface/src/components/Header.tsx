import { Logo } from "./Logo";

const NAV_SECTIONS = [
  { label: "À l'affiche", active: true },
  { label: "Cinémas", active: false },
  { label: "Films", active: false },
  { label: "À propos", active: false },
];

/** Sticky site header: logo on the left, section links on the right. */
export function Header() {
  return (
    <header className="site-header">
      <Logo />
      <nav className="site-nav" aria-label="Sections du site">
        {NAV_SECTIONS.map((section) => (
          <a
            key={section.label}
            href="#"
            aria-current={section.active ? "page" : undefined}
          >
            {section.label}
          </a>
        ))}
      </nav>
    </header>
  );
}
