import path from "node:path";
import https from "node:https";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

const externalLibraries = [
  "react",
  "react-dom",
  "react/jsx-runtime",
  "@radix-ui/react-hover-card",
  "@radix-ui/react-separator",
  "@radix-ui/react-slot",
  "class-variance-authority",
  "clsx",
  "lucide-react",
  "tailwind-merge",
];

const SLOW_POSTER_PATH = "/slow-poster.jpg";
const SLOW_POSTER_SOURCE =
  "https://xl.movieposterdb.com/23_12/2024/15239678/xl_dune-part-two-movie-poster_25f29250.jpg";
const SLOW_POSTER_DELAY_MS = 1000;
const SLOW_POSTER_TIMEOUT_MS = 10_000;

function slowPoster(): Plugin {
  return {
    name: "slow-poster",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (new URL(req.url ?? "", "http://localhost").pathname !== SLOW_POSTER_PATH) {
          next();
          return;
        }
        const startedAt = Date.now();
        const request = https.get(SLOW_POSTER_SOURCE, (upstream) => {
          const chunks: Buffer[] = [];
          upstream.on("data", (chunk: Buffer) => chunks.push(chunk));
          upstream.on("error", () => {
            clearTimeout(timeout);
            res.statusCode = 502;
            res.end();
          });
          upstream.on("end", () => {
            clearTimeout(timeout);
            const body = Buffer.concat(chunks);
            const remaining = SLOW_POSTER_DELAY_MS - (Date.now() - startedAt);
            const send = () => {
              res.statusCode = upstream.statusCode ?? 200;
              res.setHeader(
                "Content-Type",
                upstream.headers["content-type"] ?? "image/jpeg",
              );
              res.setHeader("Content-Length", body.length);
              res.end(body);
            };
            if (remaining > 0) {
              setTimeout(send, remaining);
            } else {
              send();
            }
          });
        });
        const timeout = setTimeout(() => {
          request.destroy();
          res.statusCode = 504;
          res.end();
        }, SLOW_POSTER_TIMEOUT_MS);
        request.on("error", () => {
          clearTimeout(timeout);
          res.statusCode = 502;
          res.end();
        });
      });
    },
  };
}

export default defineConfig({
  plugins: [slowPoster(), react(), tailwindcss()],
  build: {
    lib: {
      entry: path.resolve(import.meta.dirname, "src/index.ts"),
      formats: ["es"],
      fileName: "index",
      cssFileName: "index",
    },
    sourcemap: true,
    rollupOptions: {
      external: (id) =>
        externalLibraries.some(
          (lib) => id === lib || (typeof id === "string" && id.startsWith(`${lib}/`)),
        ),
    },
  },
});
