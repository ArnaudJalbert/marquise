import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

const assets = new URL("../dist/assets/", import.meta.url);
const css = readdirSync(assets)
  .filter((name) => name.endsWith(".css"))
  .map((name) => readFileSync(new URL(name, assets), "utf8"))
  .join("\n");

// Barrel tree-shaking must not drop the app's layout or shared poster utilities.
for (const selector of [".minimal-site", ".minimal-grid", ".minimal-preview", ".minimal-poster"])
  assert(css.includes(selector), `Production CSS is missing ${selector}`);
console.log("Production layout and poster styles verified.");
