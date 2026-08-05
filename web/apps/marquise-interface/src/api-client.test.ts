import { describe, expect, it } from "vitest";

import { HttpMovieGridClient, MockMovieGridClient } from "marquise-client";

import { createMovieGridClient } from "./api-client";

describe("createMovieGridClient", () => {
  it("returns the mock client by default", () => {
    expect(createMovieGridClient()).toBeInstanceOf(MockMovieGridClient);
  });

  it("returns the mock client for the mock data source", () => {
    expect(createMovieGridClient({ dataSource: "mock" })).toBeInstanceOf(
      MockMovieGridClient,
    );
  });

  it("returns the HTTP client for the api data source", () => {
    expect(
      createMovieGridClient({
        dataSource: "api",
        apiBaseUrl: "https://marquise-api.fly.dev",
      }),
    ).toBeInstanceOf(HttpMovieGridClient);
  });

  it("allows a same-origin (empty) API base URL", () => {
    expect(createMovieGridClient({ dataSource: "api" })).toBeInstanceOf(
      HttpMovieGridClient,
    );
  });
});
