import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./index.css";
// Component styles + design tokens. Workspace development resolves this import
// to source for HMR; published consumers receive the package's built CSS.
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
