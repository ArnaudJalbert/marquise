import { describe, expect, it } from "vitest";

import { HttpMarquiseClient, MockMarquiseClient } from "marquise-client";

import { createMarquiseClient } from "./api-client";

describe("createMarquiseClient", () => {
  it("returns one mock client for both interfaces by default", () => {
    const client = createMarquiseClient();

    expect(client).toBeInstanceOf(MockMarquiseClient);
    expect(client.fetchForDate).toBeTypeOf("function");
    expect(client.fetchMovie).toBeTypeOf("function");
  });

  it("returns one HTTP client for both interfaces when configured", () => {
    const client = createMarquiseClient({
      dataSource: "api",
      apiBaseUrl: "https://marquise-api.fly.dev",
    });

    expect(client).toBeInstanceOf(HttpMarquiseClient);
    expect(client.fetchForDate).toBeTypeOf("function");
    expect(client.fetchMovie).toBeTypeOf("function");
  });
});
