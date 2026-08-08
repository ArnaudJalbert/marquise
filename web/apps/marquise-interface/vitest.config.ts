import path from "node:path";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: [
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
  test: {
    environment: "jsdom",
  },
});
