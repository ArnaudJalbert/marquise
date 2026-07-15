import type { JSX } from "react";

/**
 * Smoke-test component proving the shared @marquise/core package resolves and
 * renders inside consuming apps. Replace/extend with real shared components.
 */
export function CoreHello(): JSX.Element {
  return <span>Hello from @marquise/core</span>;
}
