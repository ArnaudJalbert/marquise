import path from "node:path";

import { defineConfig } from "vite";

export default defineConfig({
  build: {
    lib: {
      entry: path.resolve(import.meta.dirname, "src/index.ts"),
      formats: ["es"],
      fileName: "index",
    },
    sourcemap: true,
    rollupOptions: {
      external: (id) =>
        id === "marquise-components" || id.startsWith("marquise-components/"),
    },
  },
});
