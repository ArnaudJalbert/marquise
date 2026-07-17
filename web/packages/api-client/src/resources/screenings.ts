import { request } from "../http";
import type { RequestContext } from "../http";
import { buildQuery } from "../query";
import type { Page, PaginationParams, ScreeningResponse } from "../types";

export interface SearchScreeningsParams extends PaginationParams {
  movie?: string;
  movie_id?: string;
  cinema_id?: string;
  from?: string | Date;
  to?: string | Date;
  language?: string;
}

export class ScreeningsResource {
  constructor(private readonly ctx: RequestContext) {}

  search(params: SearchScreeningsParams = {}): Promise<Page<ScreeningResponse>> {
    return request(this.ctx, `/v1/screenings${buildQuery(params)}`);
  }

  get(screeningId: string): Promise<ScreeningResponse> {
    return request(
      this.ctx,
      `/v1/screenings/${encodeURIComponent(screeningId)}`,
    );
  }
}
