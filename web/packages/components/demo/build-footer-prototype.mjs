import { mkdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

// A portable review artifact. No production entry point imports this prototype.
let html = await readFile(new URL("./footer-prototype.html", import.meta.url), "utf8");
for (const name of ["dune", "perfect-days", "past-lives", "the-holdovers"]) {
  const image = await readFile(new URL(`./public/posters/${name}.jpg`, import.meta.url));
  html = html.replaceAll(`public/posters/${name}.jpg`, `data:image/jpeg;base64,${image.toString("base64")}`);
}
const directory = new URL("../demo-dist/footer/", import.meta.url);
await mkdir(directory, { recursive: true });
const target = new URL("index.html", directory);
await writeFile(target, html);
console.log(fileURLToPath(target));
