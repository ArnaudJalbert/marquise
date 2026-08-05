import {
  HttpMovieGridClient,
  MockMovieGridClient,
  type MovieGridClient,
} from "marquise-client";

export interface MovieGridClientConfig {
  /** "mock" (default) or "api"; overrides `VITE_MARQUISE_DATA_SOURCE`. */
  dataSource?: string;
  /** API base URL; overrides `VITE_MARQUISE_API_BASE_URL`. Empty = same-origin. */
  apiBaseUrl?: string;
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
  const dataSource =
    config.dataSource ??
    import.meta.env.VITE_MARQUISE_DATA_SOURCE ??
    "mock";
  if (dataSource === "api") {
    const apiBaseUrl =
      config.apiBaseUrl ??
      import.meta.env.VITE_MARQUISE_API_BASE_URL ??
      "";
    return new HttpMovieGridClient({ baseUrl: apiBaseUrl });
  }
  return new MockMovieGridClient();
}
