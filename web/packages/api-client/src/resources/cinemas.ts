import { request } from "../http";
import type { RequestContext } from "../http";
import { buildQuery } from "../query";
import type {
  CinemaResponse,
  MovieResponse,
  Page,
  PaginationParams,
  ScreeningResponse,
} from "../types";

export interface ListCinemasParams extends PaginationParams {
  name?: string;
}

export type CinemaScreeningsParams = PaginationParams;

export interface CinemaMoviesParams extends PaginationParams {
  from?: string | Date;
  to?: string | Date;
}

export class CinemasResource {
  constructor(private readonly ctx: RequestContext) {}

  list(params: ListCinemasParams = {}): Promise<Page<CinemaResponse>> {
    return request(this.ctx, `/v1/cinemas${buildQuery(params)}`);
  }

  get(cinemaId: string): Promise<CinemaResponse> {
    return request(this.ctx, `/v1/cinemas/${encodeURIComponent(cinemaId)}`);
  }

  screenings(
    cinemaId: string,
    params: CinemaScreeningsParams = {},
  ): Promise<Page<ScreeningResponse>> {
    return request(
      this.ctx,
      `/v1/cinemas/${encodeURIComponent(cinemaId)}/screenings${buildQuery(params)}`,
    );
  }

  movies(
    cinemaId: string,
    params: CinemaMoviesParams = {},
  ): Promise<Page<MovieResponse>> {
    return request(
      this.ctx,
      `/v1/cinemas/${encodeURIComponent(cinemaId)}/movies${buildQuery(params)}`,
    );
  }
}
