import { SlidersHorizontal } from "lucide-react";
import type { ComponentProps } from "react";

/** "Filters" button with a badge counting the active filters. */
export function FiltersButton({
  count,
  ...button
}: { count: number } & Omit<ComponentProps<"button">, "children">) {
  return (
    <button
      type="button"
      className="minimal-filters-button"
      aria-label={count ? `Filters (${count} active)` : "Filters"}
      {...button}
    >
      <SlidersHorizontal aria-hidden size={16} />
      <span>Filters</span>
      {count > 0 && <b aria-hidden>{count}</b>}
    </button>
  );
}
