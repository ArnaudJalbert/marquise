// @vitest-environment node
import { spawnSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";

const script = path.resolve(import.meta.dirname, "check-isolation.mjs");

function checkIsolation(files: Record<string, string>) {
  const dist = mkdtempSync(path.join(tmpdir(), "isolation-"));
  for (const [name, source] of Object.entries(files)) {
    mkdirSync(path.dirname(path.join(dist, name)), { recursive: true });
    if (source.startsWith("copy:")) copyFileSync(source.slice(5), path.join(dist, name));
    else writeFileSync(path.join(dist, name), source);
  }
  return spawnSync(process.execPath, [script, dist], { encoding: "utf8" });
}

describe("check-isolation", () => {
  it("accepts library code, styles, maps and declarations", () => {
    const result = checkIsolation({
      "index.js": "export const x = 1;",
      "index.css": ".x{}",
      "index.js.map": "{}",
      "types/index.d.ts": "export {};",
    });

    expect(result.status).toBe(0);
  });

  it("rejects a copied demo poster even without text markers", () => {
    const poster = path.resolve(import.meta.dirname, "public/posters/arrival.jpg");
    const result = checkIsolation({ "index.js": "export {};", "assets/cover.jpg": `copy:${poster}` });

    expect(result.status).not.toBe(0);
    expect(result.stderr).toContain("cover.jpg");
  });
});
