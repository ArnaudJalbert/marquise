import { HttpMarquiseClient } from "marquise-client";

export interface MarquiseClientConfig {
  /** API base URL. Empty uses same-origin requests. */
  apiBaseUrl?: string;
}

/** Build the real production client. API failures remain visible. */
export function createMarquiseClient(
  config: MarquiseClientConfig = {},
): HttpMarquiseClient {
  return new HttpMarquiseClient({
    baseUrl:
      config.apiBaseUrl ?? import.meta.env.VITE_MARQUISE_API_BASE_URL ?? "",
  });
}
