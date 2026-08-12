import {
  HttpMovieDetailClient,
  HttpMovieGridClient,
  MockMovieDetailClient,
  MockMovieGridClient,
  type MovieDetailClient,
  type MovieGridClient,
} from "marquise-client";

export interface MovieGridClientConfig {
  /** "mock" (default) or "api"; overrides `VITE_MARQUISE_DATA_SOURCE`. */
  dataSource?: string;
  /** API base URL; overrides `VITE_MARQUISE_API_BASE_URL`. Empty = same-origin. */
  apiBaseUrl?: string;
}

function resolveDataSource(config: MovieGridClientConfig): string {
  return (
    config.dataSource ??
    import.meta.env.VITE_MARQUISE_DATA_SOURCE ??
    "mock"
  );
}

function resolveApiBaseUrl(config: MovieGridClientConfig): string {
  return (
    config.apiBaseUrl ??
    import.meta.env.VITE_MARQUISE_API_BASE_URL ??
    ""
  );
}

/**
 * Build the movie grid client for the configured data source.
 *
 * - `mock` (default): deterministic demo data, no backend needed.
 * - `api`: the Marquise REST API. Same-origin by default — the Vite dev
 *   server proxies `/v1/*` to `http://localhost:8000` (see vite.config.ts).
 *   Point `VITE_MARQUISE_API_BASE_URL` at a deployed API (e.g.
 *   `https://marquise-api.fly.dev`) in production.
 */
export function createMovieGridClient(
  config: MovieGridClientConfig = {},
): MovieGridClient {
  if (resolveDataSource(config) === "api") {
    return new HttpMovieGridClient({ baseUrl: resolveApiBaseUrl(config) });
  }
  return new MockMovieGridClient();
}

/**
 * Build the movie detail client for the configured data source. The data
 * source and base URL resolve exactly like {@link createMovieGridClient}, so
 * both clients always agree.
 */
export function createMovieDetailClient(
  config: MovieGridClientConfig = {},
): MovieDetailClient {
  if (resolveDataSource(config) === "api") {
    return new HttpMovieDetailClient({ baseUrl: resolveApiBaseUrl(config) });
  }
  return new MockMovieDetailClient();
}
