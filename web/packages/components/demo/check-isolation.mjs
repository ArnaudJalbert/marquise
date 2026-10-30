import { readdir, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const dist = fileURLToPath(new URL("../dist/", import.meta.url));
const markers = ["sample-booking", "Sample address", "Untitled catalogue entry", "Fixed review date", "/posters/dune.jpg"];
let checked = 0;
async function inspect(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) { await inspect(target); continue; }
    const content = await readFile(target, "utf8");
    for (const marker of markers) if (content.includes(marker)) throw new Error(`Demo fixture ${marker} leaked into ${target}`);
    if (target.includes("fixtures") || target.includes("/demo/")) throw new Error(`Demo file shipped: ${target}`);
    checked++;
  }
}
await inspect(dist);
console.log(`Fixture isolation verified in ${checked} production library files.`);
