import { useEffect, useRef, useState } from "react";

function isTypingTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable ||
      ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}

/** Always-visible movie title search, debounced and focused with `/`. */
export function MovieSearch({
  value,
  onSearch,
}: {
  value: string;
  onSearch: (value: string) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  useEffect(() => {
    if (draft === value) return;
    const timer = window.setTimeout(() => onSearch(draft), 250);
    return () => window.clearTimeout(timer);
  }, [draft, onSearch, value]);
  useEffect(() => {
    const focus = (event: KeyboardEvent) => {
      if (
        event.key !== "/" ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey ||
        isTypingTarget(event.target)
      )
        return;
      event.preventDefault();
      input.current?.focus();
    };
    document.addEventListener("keydown", focus);
    return () => document.removeEventListener("keydown", focus);
  }, []);
  return (
    <label className="minimal-movie-search">
      <span className="minimal-visually-hidden">Search movies</span>
      <input
        ref={input}
        type="search"
        value={draft}
        placeholder="Search movies"
        autoComplete="off"
        aria-keyshortcuts="/"
        onChange={(event) => setDraft(event.target.value)}
      />
      {!draft && (
        <kbd className="minimal-movie-search-key" aria-hidden="true">
          /
        </kbd>
      )}
    </label>
  );
}
