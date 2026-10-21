import { describe, expect, it } from "vitest";

import { posterRenditionUrl } from "./poster-rendition";

describe("posterRenditionUrl", () => {
  it("routes Cinéma Cinémas posters through Cloudflare resize renditions", () => {
    expect(
      posterRenditionUrl(
        "https://img.cinemacinema.ca/Affiches/beaubien/lbdg_partie1.jpg",
      ),
    ).toBe(
      "https://img.cinemacinema.ca/cdn-cgi/image/width=450,quality=80,format=auto/Affiches/beaubien/lbdg_partie1.jpg",
    );
  });

  it("swaps TMDB original renditions for w500", () => {
    expect(
      posterRenditionUrl(
        "https://image.tmdb.org/t/p/original/abc123.jpg",
      ),
    ).toBe("https://image.tmdb.org/t/p/w500/abc123.jpg");
  });

  it("downgrades oversized TMDB renditions but keeps w500 and smaller", () => {
    expect(posterRenditionUrl("https://image.tmdb.org/t/p/w780/a.jpg")).toBe(
      "https://image.tmdb.org/t/p/w500/a.jpg",
    );
    expect(posterRenditionUrl("https://image.tmdb.org/t/p/w500/a.jpg")).toBe(
      "https://image.tmdb.org/t/p/w500/a.jpg",
    );
  });

  it("is idempotent for both allowlisted hosts", () => {
    const once = posterRenditionUrl(
      "https://img.cinemacinema.ca/Affiches/a.jpg",
    )!;
    expect(posterRenditionUrl(once)).toBe(once);
    const tmdbOnce = posterRenditionUrl(
      "https://image.tmdb.org/t/p/original/a.jpg",
    )!;
    expect(posterRenditionUrl(tmdbOnce)).toBe(tmdbOnce);
  });

  it("leaves smaller TMDB renditions and other hosts untouched", () => {
    expect(
      posterRenditionUrl("https://image.tmdb.org/t/p/w185/abc123.jpg"),
    ).toBe("https://image.tmdb.org/t/p/w185/abc123.jpg");
    expect(
      posterRenditionUrl(
        "https://mediafiles.cineplex.com/Central/Film/Posters/61877_768_1024.jpg",
      ),
    ).toBe(
      "https://mediafiles.cineplex.com/Central/Film/Posters/61877_768_1024.jpg",
    );
  });

  it("passes through null, unparseable and non-https values", () => {
    expect(posterRenditionUrl(null)).toBe(null);
    expect(posterRenditionUrl("not a url")).toBe("not a url");
    expect(posterRenditionUrl("http://img.cinemacinema.ca/a.jpg")).toBe(
      "http://img.cinemacinema.ca/a.jpg",
    );
  });
});
