import { MarquiseApiError } from "./errors";
import type { ApiErrorBody } from "./types";

export type FetchLike = typeof fetch;

export interface RequestContext {
  baseUrl: string;
  fetchImpl: FetchLike;
}

export async function request<T>(
  ctx: RequestContext,
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = `${ctx.baseUrl.replace(/\/$/, "")}${path}`;
  const response = await ctx.fetchImpl(url, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });

  if (!response.ok) {
    throw await toApiError(response);
  }

  return (await response.json()) as T;
}

async function toApiError(response: Response): Promise<MarquiseApiError> {
  try {
    const body = (await response.json()) as ApiErrorBody;
    return new MarquiseApiError({
      status: response.status,
      detail: body.detail ?? response.statusText,
      errorCode: body.error_code ?? null,
      requestId: body.request_id ?? null,
    });
  } catch {
    return new MarquiseApiError({
      status: response.status,
      detail: response.statusText || "Request failed",
      errorCode: null,
      requestId: null,
    });
  }
}
