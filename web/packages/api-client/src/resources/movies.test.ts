import { describe, expect, it, vi } from "vitest";
import { MoviesResource } from "./movies";

describe("MoviesResource.list", () => {
  it("assembles the URL and query string correctly", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0, page: 1, size: 20, pages: 0 }), {
        status: 200,
      }),
    );
    const movies = new MoviesResource({
      baseUrl: "https://marquise-api.fly.dev",
      fetchImpl,
    });

    await movies.list({ title: "Dune", page: 2, size: 20 });

    const [url] = fetchImpl.mock.calls[0];
    expect(url).toBe(
      "https://marquise-api.fly.dev/v1/movies?title=Dune&page=2&size=20",
    );
  });

  it("encodes the movie id in single-resource paths", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "a/b" }), { status: 200 }),
    );
    const movies = new MoviesResource({
      baseUrl: "https://marquise-api.fly.dev",
      fetchImpl,
    });

    await movies.get("a/b");

    const [url] = fetchImpl.mock.calls[0];
    expect(url).toBe("https://marquise-api.fly.dev/v1/movies/a%2Fb");
  });
});
