import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./index.css";
// Prebuilt component styles + design tokens. The JS is consumed from source
// (see vite.config.ts) for HMR, but the stylesheet is imported from the
// package's built bundle, which rolldown emits reliably in production builds.
import "marquise-components/index.css";

const root = document.getElementById("root");
if (root === null) {
  throw new Error("Root element not found");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
