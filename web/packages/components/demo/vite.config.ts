import path from "node:path";
import type { IncomingMessage, ServerResponse } from "node:http";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, loadEnv, type Plugin } from "vite";
import { sampleApiResponse } from "./sample-api.ts";

function serveSamples(
  request: IncomingMessage,
  response: ServerResponse,
  next: () => void,
) {
  if (request.method !== "GET") return next();
  const body = sampleApiResponse(
    new URL(request.url ?? "/", "http://prototype.invalid"),
  );
  if (!body) return next();
  response.setHeader("Content-Type", "application/json");
  response.end(JSON.stringify(body));
}

const sampleApi: Plugin = {
  name: "prototype-sample-api",
  configureServer(server) {
    server.middlewares.use(serveSamples);
  },
  configurePreviewServer(server) {
    server.middlewares.use(serveSamples);
  },
};
export default defineConfig(({ mode }) => {
  const apiMode =
    loadEnv(mode, import.meta.dirname, "VITE_").VITE_MARQUISE_DATA_SOURCE ===
    "api";
  return {
    root: import.meta.dirname,
    plugins: [react(), tailwindcss(), !apiMode && sampleApi],
    resolve: {
      alias: [
        {
          find: /^marquise-client$/,
          replacement: path.resolve(
            import.meta.dirname,
            "../../marquise-client/src/index.ts",
          ),
        },
        {
          find: /^marquise-components$/,
          replacement: path.resolve(import.meta.dirname, "../src/index.ts"),
        },
      ],
    },
    server: {
      host: "0.0.0.0",
      port: 4174,
      proxy: apiMode ? { "/v1": "http://localhost:8000" } : undefined,
    },
    build: { outDir: "../demo-dist", emptyOutDir: true },
  };
});
