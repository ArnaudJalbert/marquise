import { SlidersHorizontal } from "lucide-react";
import { Button } from "marquise-components";

import { Logo } from "./Logo";

const NAV_SECTIONS = [
  { label: "Screenings", href: "/" },
];

export interface HeaderProps {
  /** Whether the filter panel is currently visible. */
  filtersOpen: boolean;
  /** Invoked when the Filters toggle is clicked. */
  onToggleFilters: () => void;
  /** Whether the listings-only filter action is visible. */
  showFilters?: boolean;
  /** Whether the listings section is the current route. */
  listingsActive?: boolean;
}

/** Sticky site header: logo on the left, filters toggle and sections on the right. */
export function Header({
  filtersOpen,
  onToggleFilters,
  showFilters = true,
  listingsActive = true,
}: HeaderProps) {
  return (
    <header className="site-header">
      <Logo />
      <div className="site-header-actions">
        <nav className="site-nav" aria-label="Site sections">
          {NAV_SECTIONS.map((section) => (
            <a
              key={section.label}
              href={section.href}
              aria-current={
                listingsActive && section.label === "Now Showing"
                  ? "page"
                  : undefined
              }
            >
              {section.label}
            </a>
          ))}
        </nav>
        {showFilters ? (
          <Button
            variant="outline"
            size="sm"
            onClick={onToggleFilters}
            aria-expanded={filtersOpen}
          >
            <SlidersHorizontal aria-hidden />
            Filters
          </Button>
        ) : null}
      </div>
    </header>
  );
}
