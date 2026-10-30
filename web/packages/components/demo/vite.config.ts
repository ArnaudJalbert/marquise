import path from "node:path";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
export default defineConfig({
  root: import.meta.dirname,
  plugins: [react(), tailwindcss()],
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
  server: { host: "0.0.0.0", port: 4174 },
  build: { outDir: "../demo-dist", emptyOutDir: true },
});
