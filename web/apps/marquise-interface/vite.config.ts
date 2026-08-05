import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      // Consume the workspace packages from source for instant HMR — no
      // prebuild. "$" makes the alias exact so subpath imports (e.g.
      // "marquise-components/index.css") still resolve via package exports.
      "marquise-components$": path.resolve(
        import.meta.dirname,
        "../../packages/components/src/index.ts",
      ),
      "marquise-client$": path.resolve(
        import.meta.dirname,
        "../../packages/marquise-client/src/index.ts",
      ),
    },
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
