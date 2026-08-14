import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const externalLibraries = [
  "react",
  "react-dom",
  "react/jsx-runtime",
  "@radix-ui/react-hover-card",
  "@radix-ui/react-popover",
  "@radix-ui/react-slot",
  "class-variance-authority",
  "clsx",
  "lucide-react",
  "marquise-client",
  "tailwind-merge",
];

export default defineConfig({
  plugins: [react(), tailwindcss()],
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
