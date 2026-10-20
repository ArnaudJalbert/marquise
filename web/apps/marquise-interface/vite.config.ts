import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: [
      // Consume workspace packages from source for instant HMR. Exact-match
      // regexes keep subpath imports resolving via package exports.
      // Source CSS must match source components, not a stale dist bundle.
      {
        find: /^marquise-components\/index\.css$/,
        replacement: path.resolve(
          import.meta.dirname,
          "../../packages/components/src/index.css",
        ),
      },
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
