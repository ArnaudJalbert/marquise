import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync } from "node:fs";

const dist = new URL("../dist/", import.meta.url);
const assets = new URL("assets/", dist);
const css = readdirSync(assets)
  .filter((name) => name.endsWith(".css"))
  .map((name) => readFileSync(new URL(name, assets), "utf8"))
  .join("\n");

// Barrel tree-shaking must not drop the app's layout or shared poster utilities.
for (const selector of [".minimal-site", ".minimal-grid", ".minimal-preview", ".minimal-poster"])
  assert(css.includes(selector), `Production CSS is missing ${selector}`);
console.log("Production layout and poster styles verified.");

// The tab title and both icon links must survive, and point at shipped files.
const html = readFileSync(new URL("index.html", dist), "utf8");
assert.match(html, /<title>Marquise<\/title>/, "Production HTML title must be exactly Marquise");
for (const [rel, file, type] of [
  ["icon", "favicon.svg", ' type="image/svg+xml"'],
  ["apple-touch-icon", "apple-touch-icon.png", ""],
]) {
  assert(html.includes(`<link rel="${rel}" href="/${file}"${type}`), `Production HTML is missing the ${rel} link`);
  assert(existsSync(new URL(file, dist)), `Production build is missing ${file}`);
}
console.log("Production title and icon links verified.");
