import { describe, expect, it, vi } from "vitest";
import { MarquiseApiError } from "./errors";
import { request } from "./http";
import type { RequestContext } from "./http";

function makeCtx(fetchImpl: RequestContext["fetchImpl"]): RequestContext {
  return { baseUrl: "https://marquise-api.fly.dev", fetchImpl };
}

describe("request", () => {
  it("resolves with parsed JSON on a successful response", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "1" }), { status: 200 }),
    );

    const result = await request(makeCtx(fetchImpl), "/v1/movies/1");

    expect(result).toEqual({ id: "1" });
    expect(fetchImpl).toHaveBeenCalledWith(
      "https://marquise-api.fly.dev/v1/movies/1",
      expect.objectContaining({ headers: expect.objectContaining({ Accept: "application/json" }) }),
    );
  });

  it("throws MarquiseApiError with body fields on a JSON error response", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "not found", error_code: "not_found", request_id: "abc" }),
        { status: 404, statusText: "Not Found" },
      ),
    );

    await expect(request(makeCtx(fetchImpl), "/v1/movies/x")).rejects.toMatchObject({
      status: 404,
      detail: "not found",
      errorCode: "not_found",
      requestId: "abc",
    });
  });

  it("falls back to statusText when the error body is not JSON", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response("<html>gateway timeout</html>", {
        status: 504,
        statusText: "Gateway Timeout",
      }),
    );

    const error = await request(makeCtx(fetchImpl), "/v1/movies").catch((e) => e);

    expect(error).toBeInstanceOf(MarquiseApiError);
    expect(error.status).toBe(504);
    expect(error.detail).toBe("Gateway Timeout");
    expect(error.errorCode).toBeNull();
    expect(error.requestId).toBeNull();
  });
});
