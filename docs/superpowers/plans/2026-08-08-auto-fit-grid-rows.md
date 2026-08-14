# Auto-Fit Grid Rows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the movie grid use available vertical rows before expanding the loaded cards into a single wide row.

**Architecture:** `MovieCardGrid` already observes its bounded grid area and measures a rendered card row. Retain width-derived maximum columns and page sizing, but once the available row count is known, cap the displayed columns at `ceil(items.length / availableRows)`. This preserves the minimum card width and maximum-column rules while distributing a small result set across every row that fits.

**Tech Stack:** React 19, TypeScript 6, Vitest 4, Tailwind CSS 4, pnpm workspaces.

## Global Constraints

- Keep `MovieCardGridProps` unchanged; this is an internal auto-fit layout-policy correction.
- Preserve numeric `pageSize` behavior and the existing 2–8 width/card-size column limits.
- `pageSize="auto"` must remain bounded-height and paginated when the result set exceeds its calculated page capacity.
- Run `pnpm test`, `pnpm typecheck`, and `pnpm lint` from `web/` before handoff.

---

### Task 1: Use vertical capacity when choosing auto-fit columns

**Files:**
- Modify: `web/packages/components/src/components/movie/MovieCardGrid.tsx:15-105`
- Test: `web/packages/components/src/components/movie/MovieCardGrid.test.tsx:358-485`

**Interfaces:**
- Consumes: `items`, measured `dims.width` / `dims.height`, measured `rowHeight`, and `cardSize`.
- Produces: an unchanged `MovieCardGrid` public interface with auto-fit CSS columns and pagination that use both available rows and width.

- [x] **Step 1: Write the failing small-result-set layout test**

Add a Vitest case using the existing 1430px × 1200px resize observer and 200px card height. Render six movie items with `pageSize="auto"` and assert:

```tsx
expect(list?.getAttribute("style")).toContain("repeat(2");
expect(screen.getByRole("heading", { name: "Movie 6" })).toBeInTheDocument();
expect(screen.queryByText(/^\d+ \/ \d+$/)).not.toBeInTheDocument();
```

The height fits five rows (`floor((1200 + 16) / (200 + 16)) = 5`), so six items should use two columns and three occupied rows instead of six columns and one row.

- [x] **Step 2: Run the focused test to verify it fails**

Run: `pnpm --filter marquise-components test -- MovieCardGrid.test.tsx`

Expected: FAIL because `columnsForWidth(1430, 200, 6)` currently produces six columns without considering available rows.

- [x] **Step 3: Implement row-aware column capping**

After `rowHeight` is known, calculate:

```ts
const availableRows = Math.max(
  1,
  Math.floor((dims.height + GRID_GAP) / (rowHeight + GRID_GAP)),
);
const columnsNeeded = Math.max(2, Math.ceil(items.length / availableRows));
const columns = Math.min(columnsForWidth(dims.width, cardWidth, maxColumns), columnsNeeded);
```

Use the width-derived column count until `rowHeight` is measured so the existing measurement subset can render. Once measured, use the capped count for both `gridTemplateColumns` and `effectivePageSize = columns * availableRows`. Keep `maxColumns` at 6 when `cardSize` is omitted and 8 when it is supplied.

- [x] **Step 4: Update large-result layout expectations**

Update the existing 12-item, 1430px × 1200px test to expect three columns and four occupied rows:

```tsx
expect(list?.getAttribute("style")).toContain("repeat(3");
expect(screen.getByRole("heading", { name: "Movie 12" })).toBeInTheDocument();
```

This confirms the grid uses as many available rows as possible even when the full result set fits on one page.

- [x] **Step 5: Run focused tests to verify the component behavior**

Run: `pnpm --filter marquise-components test -- MovieCardGrid.test.tsx`

Expected: PASS, including pagination, card-size, resize, and row-aware layout tests.

- [ ] **Step 6: Commit the focused component correction** (not requested)

```bash
git add web/packages/components/src/components/movie/MovieCardGrid.tsx web/packages/components/src/components/movie/MovieCardGrid.test.tsx
git commit -m "fix(web): use available rows in movie auto-fit"
```

## Self-Review

- Spec coverage: the row-aware cap directly prevents filter-panel hiding from turning a vertically-capable layout into one row.
- Placeholder scan: every implementation and test action has an exact formula, command, and expected outcome.
- Type consistency: no public component props change; all values are existing numeric measurements or item counts.
