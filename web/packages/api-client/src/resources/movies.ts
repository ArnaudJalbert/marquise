import { request } from "../http";
import type { RequestContext } from "../http";
import { buildQuery } from "../query";
import type {
  MovieResponse,
  Page,
  PaginationParams,
  ScreeningResponse,
} from "../types";

export interface ListMoviesParams extends PaginationParams {
  title?: string;
}

export type MovieScreeningsParams = PaginationParams;

export class MoviesResource {
  constructor(private readonly ctx: RequestContext) {}

  list(params: ListMoviesParams = {}): Promise<Page<MovieResponse>> {
    return request(this.ctx, `/v1/movies${buildQuery(params)}`);
  }

  get(movieId: string): Promise<MovieResponse> {
    return request(this.ctx, `/v1/movies/${encodeURIComponent(movieId)}`);
  }

  /**
   * Fetches multiple movies in one request. Ids with no matching movie are
   * omitted from the response. The API caps this at 100 ids per call.
   */
  getByIds(ids: string[]): Promise<MovieResponse[]> {
    return request(this.ctx, `/v1/movies/by-ids${buildQuery({ ids })}`);
  }

  screenings(
    movieId: string,
    params: MovieScreeningsParams = {},
  ): Promise<Page<ScreeningResponse>> {
    return request(
      this.ctx,
      `/v1/movies/${encodeURIComponent(movieId)}/screenings${buildQuery(params)}`,
    );
  }
}
