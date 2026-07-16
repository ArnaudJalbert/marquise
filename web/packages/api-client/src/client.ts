import type { FetchLike, RequestContext } from "./http";
import { CinemasResource } from "./resources/cinemas";
import { MoviesResource } from "./resources/movies";
import { ScreeningsResource } from "./resources/screenings";

export interface MarquiseApiClientOptions {
  /** Base URL of the Marquise API, e.g. "https://marquise-api.fly.dev". */
  baseUrl: string;
  /** Override the fetch implementation. Defaults to the global `fetch`; primarily useful for tests. */
  fetch?: FetchLike;
}

export class MarquiseApiClient {
  readonly movies: MoviesResource;
  readonly cinemas: CinemasResource;
  readonly screenings: ScreeningsResource;

  constructor(options: MarquiseApiClientOptions) {
    if (!options.baseUrl) {
      throw new Error("MarquiseApiClient requires a baseUrl");
    }

    const ctx: RequestContext = {
      baseUrl: options.baseUrl,
      fetchImpl: options.fetch ?? globalThis.fetch.bind(globalThis),
    };

    this.movies = new MoviesResource(ctx);
    this.cinemas = new CinemasResource(ctx);
    this.screenings = new ScreeningsResource(ctx);
  }
}
