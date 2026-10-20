import {
  HttpMarquiseClient,
  MockMarquiseClient,
  type MovieDetailClient,
  type DiscoveryClient,
  type MovieGridClient,
} from "marquise-client";

export interface MarquiseClientConfig {
  /** "mock" (default) or "api"; overrides `VITE_MARQUISE_DATA_SOURCE`. */
  dataSource?: string;
  /** API base URL; overrides `VITE_MARQUISE_API_BASE_URL`. Empty = same-origin. */
  apiBaseUrl?: string;
}

export type MarquiseClient = DiscoveryClient & MovieGridClient & MovieDetailClient;

/** Build one client shared by discovery, directory and movie detail routes. */
export function createMarquiseClient(
  config: MarquiseClientConfig = {},
): MarquiseClient {
  const dataSource =
    config.dataSource ?? import.meta.env.VITE_MARQUISE_DATA_SOURCE ?? "mock";
  if (dataSource === "api") {
    return new HttpMarquiseClient({
      baseUrl:
        config.apiBaseUrl ?? import.meta.env.VITE_MARQUISE_API_BASE_URL ?? "",
    });
  }
  return new MockMarquiseClient();
}
