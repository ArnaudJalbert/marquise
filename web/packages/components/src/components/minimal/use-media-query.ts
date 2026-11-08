import { useCallback, useSyncExternalStore } from "react";

/** Phone widths, matching the stylesheet's `max-width: 639px` breakpoint. */
export const PHONE_MEDIA_QUERY = "(max-width: 639px)";

/** Whether the viewport currently matches a media query, updating as it changes. */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const list = window.matchMedia(query);
      list.addEventListener("change", onChange);
      return () => list.removeEventListener("change", onChange);
    },
    [query],
  );
  return useSyncExternalStore(subscribe, () => window.matchMedia(query).matches, () => false);
}
