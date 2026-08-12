import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: [
      // Consume the workspace packages from source for instant HMR — no
      // prebuild. Exact-match regexes keep subpath imports (e.g.
      // "marquise-components/index.css") resolving via package exports.
      {
        find: /^marquise-components$/,
        replacement: path.resolve(
          import.meta.dirname,
          "../../packages/components/src/index.ts",
        ),
      },
      {
        find: /^marquise-client$/,
        replacement: path.resolve(
          import.meta.dirname,
          "../../packages/marquise-client/src/index.ts",
        ),
      },
    ],
  },
  server: {
    proxy: {
      // Same-origin API calls in dev: /v1/* is forwarded to the local API.
      "/v1": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
