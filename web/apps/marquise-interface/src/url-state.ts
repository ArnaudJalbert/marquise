import type { MovieFilters } from "marquise-components";

const CARD_SIZE_MIN = 150;
const CARD_SIZE_MAX = 320;
export const DEFAULT_CARD_SIZE = 200;

const OWNED_LISTING_PARAMS = [
  "date",
  "from",
  "to",
  "cinema",
  "genre",
  "language",
  "card",
  "details",
  "filters",
  "page",
] as const;

export interface ListingsUrlState {
  date?: string;
  filters: Partial<MovieFilters>;
  cardSize: number;
  hideDetails: boolean;
  filtersOpen: boolean;
  pageIndex: number;
}

export type AppRoute =
  | { kind: "listings" }
  | { kind: "movie"; movieId: string }
  | { kind: "not-found" };

function validIsoDate(value: string | null): string | undefined {
  if (value === null || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return undefined;
  const date = new Date(`${value}T12:00:00Z`);
  return Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value
    ? undefined
    : value;
}

function hour(value: string | null): number | undefined {
  if (value === null || !/^\d{1,2}$/.test(value)) return undefined;
  const parsed = Number(value);
  return parsed >= 0 && parsed <= 24 ? parsed : undefined;
}

function positiveInteger(value: string | null): number | undefined {
  if (value === null || !/^\d+$/.test(value)) return undefined;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : undefined;
}

function unique(values: string[]): string[] {
  return [...new Set(values.filter((value) => value !== ""))];
}

export function parseListingsUrl(url: URL): ListingsUrlState {
  const from = hour(url.searchParams.get("from"));
  const to = hour(url.searchParams.get("to"));
  const filters: Partial<MovieFilters> = {
    cinemas: unique(url.searchParams.getAll("cinema")),
    genres: unique(url.searchParams.getAll("genre")),
    languages: unique(url.searchParams.getAll("language")),
  };
  if (from !== undefined && to !== undefined && from <= to) {
    filters.timeRange = [from, to];
  }

  const rawCardSize = positiveInteger(url.searchParams.get("card"));
  const cardSize =
    rawCardSize === undefined
      ? DEFAULT_CARD_SIZE
      : Math.min(CARD_SIZE_MAX, Math.max(CARD_SIZE_MIN, rawCardSize));
  const page = positiveInteger(url.searchParams.get("page"));

  return {
    date: validIsoDate(url.searchParams.get("date")),
    filters,
    cardSize,
    hideDetails: url.searchParams.get("details") === "hidden",
    filtersOpen: url.searchParams.get("filters") === "open",
    pageIndex: (page ?? 1) - 1,
  };
}

export function serializeListingsUrl(
  currentUrl: URL,
  state: ListingsUrlState,
): URL {
  const url = new URL(currentUrl);
  url.pathname = "/";
  for (const parameter of OWNED_LISTING_PARAMS) {
    url.searchParams.delete(parameter);
  }

  if (state.date !== undefined) url.searchParams.set("date", state.date);
  const timeRange = state.filters.timeRange;
  if (timeRange !== undefined) {
    url.searchParams.set("from", String(timeRange[0]));
    url.searchParams.set("to", String(timeRange[1]));
  }
  for (const cinema of state.filters.cinemas ?? []) {
    url.searchParams.append("cinema", cinema);
  }
  for (const genre of state.filters.genres ?? []) {
    url.searchParams.append("genre", genre);
  }
  for (const language of state.filters.languages ?? []) {
    url.searchParams.append("language", language);
  }
  if (state.cardSize !== DEFAULT_CARD_SIZE) {
    url.searchParams.set("card", String(state.cardSize));
  }
  if (state.hideDetails) url.searchParams.set("details", "hidden");
  if (state.filtersOpen) url.searchParams.set("filters", "open");
  if (state.pageIndex > 0) {
    url.searchParams.set("page", String(state.pageIndex + 1));
  }
  return url;
}

export function parseRoute(pathname: string): AppRoute {
  if (pathname === "/" || pathname === "") return { kind: "listings" };
  const match = /^\/movies\/([^/]+)\/?$/.exec(pathname);
  if (match?.[1] !== undefined) {
    try {
      const movieId = decodeURIComponent(match[1]);
      return movieId === ""
        ? { kind: "not-found" }
        : { kind: "movie", movieId };
    } catch {
      return { kind: "not-found" };
    }
  }
  return { kind: "not-found" };
}

export function movieUrl(movieId: string, date?: string): URL {
  const url = new URL(window.location.origin);
  url.pathname = `/movies/${encodeURIComponent(movieId)}`;
  if (date !== undefined) url.searchParams.set("date", date);
  return url;
}

export function movieDateFromUrl(url: URL): string | undefined {
  return validIsoDate(url.searchParams.get("date"));
}
