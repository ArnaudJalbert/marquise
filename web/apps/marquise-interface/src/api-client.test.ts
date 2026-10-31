import { describe, expect, it } from "vitest";
import { HttpMarquiseClient } from "marquise-client";
import { createMarquiseClient } from "./api-client";

describe("createMarquiseClient", () => {
  it("uses the real HTTP client by default", () => {
    expect(createMarquiseClient()).toBeInstanceOf(HttpMarquiseClient);
  });
  it("accepts an explicit API base URL", () => {
    expect(
      createMarquiseClient({ apiBaseUrl: "https://marquise-api.example" }),
    ).toBeInstanceOf(HttpMarquiseClient);
  });
});
