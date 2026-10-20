import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { MovieCardGridItem } from "marquise-client";
import { PosterCard } from "./PosterCard";

const date = "2026-08-08";
function movieItem(title = "Anora"): MovieCardGridItem {
  return {
    movie: {
      title,
      posterUrl: "https://example.com/poster.jpg",
      releaseYear: 2024,
      durationMinutes: 139,
    },
    showtimesUrl: "/movies/anora",
    showtimes: [
      {
        startsAt: `${date}T23:00:00-04:00`,
        ticketUrl: "https://tickets.example/seat",
        language: "VOSTF",
        cinema: { id: "cinema-1", name: "Cinema One", link: null },
      },
    ],
  };
}

async function advance(milliseconds: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(milliseconds);
  });
}

function card(index = 0) {
  return document.querySelectorAll(".poster-card")[index]!;
}

beforeEach(() => {
  vi.useFakeTimers();
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

it("does not open a preview when the mouse briefly passes over the poster", async () => {
  render(<PosterCard item={movieItem()} date={date} />);
  fireEvent.pointerEnter(card(), { pointerType: "mouse" });
  await advance(100);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  fireEvent.pointerLeave(card(), { pointerType: "mouse" });
  await advance(300);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("opens on deliberate mouse hover without moving focus or activating Showtimes", async () => {
  render(<PosterCard item={movieItem()} date={date} />);
  fireEvent.pointerEnter(card(), { pointerType: "mouse" });
  await advance(300);
  const preview = screen.getByRole("dialog", { name: "Showtimes for Anora" });
  expect(within(preview).getByText("VOSTF")).toBeInTheDocument();
  expect(document.activeElement).toBe(document.body);
  expect(
    screen.getByRole("button", { name: "Showtimes for Anora" }),
  ).toHaveAttribute("aria-expanded", "false");
  fireEvent.keyDown(preview, { key: "Escape" });
  await advance(0);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(document.activeElement).toBe(document.body);
});

it("keeps the hover preview open while the mouse dwells on the Showtimes strip", async () => {
  render(<PosterCard item={movieItem()} date={date} />);
  fireEvent.pointerEnter(card(), { pointerType: "mouse" });
  await advance(300);
  const dialog = screen.getByRole("dialog", { name: "Showtimes for Anora" });
  const poster = screen.getByRole("link", { name: "View Anora" });
  const trigger = screen.getByRole("button", { name: "Showtimes for Anora" });
  // The strip overlaps the poster; crossing that inner boundary stays inside
  // the hover trigger, so neither a child leave nor a touch on the button
  // closes the preview.
  fireEvent.pointerLeave(poster, {
    pointerType: "mouse",
    relatedTarget: trigger,
  });
  await advance(300);
  expect(dialog).toBeInTheDocument();
  expect(trigger).toHaveAttribute("aria-expanded", "false");
  fireEvent.pointerDown(trigger, { pointerType: "mouse" });
  fireEvent.click(trigger);
  await advance(0);
  expect(screen.getAllByRole("dialog")).toHaveLength(1);
  expect(trigger).toHaveAttribute("aria-expanded", "true");
  fireEvent.pointerLeave(trigger, { pointerType: "mouse" });
  await advance(300);
  expect(screen.getAllByRole("dialog")).toHaveLength(1);
});

it("keeps an explicit interactive preview open when Showtimes is clicked after hover", async () => {
  render(<PosterCard item={movieItem()} date={date} />);
  fireEvent.pointerEnter(card(), { pointerType: "mouse" });
  await advance(300);
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  const trigger = screen.getByRole("button", { name: "Showtimes for Anora" });
  fireEvent.pointerDown(trigger, { pointerType: "mouse" });
  fireEvent.click(trigger);
  await advance(0);
  expect(screen.getAllByRole("dialog")).toHaveLength(1);
  expect(trigger).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("button", { name: "Close preview" })).toHaveFocus();
  fireEvent.pointerLeave(card(), { pointerType: "mouse" });
  await advance(300);
  expect(screen.getAllByRole("dialog")).toHaveLength(1);
  fireEvent.pointerEnter(card(), { pointerType: "mouse" });
  await advance(300);
  expect(screen.getAllByRole("dialog")).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: "Close preview" }));
  await advance(0);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});

it("does not open a transient stack while the mouse crosses seven posters quickly", async () => {
  render(
    <>
      {Array.from({ length: 7 }, (_, index) => (
        <PosterCard
          key={index}
          item={movieItem(`Movie ${index}`)}
          date={date}
        />
      ))}
    </>,
  );
  for (let index = 0; index < 7; index++) {
    fireEvent.pointerEnter(card(index), { pointerType: "mouse" });
    await advance(40);
    expect(screen.queryAllByRole("dialog")).toHaveLength(0);
    fireEvent.pointerLeave(card(index), { pointerType: "mouse" });
  }
  await advance(300);
  expect(screen.queryAllByRole("dialog")).toHaveLength(0);
});

it("allows the mouse to enter preview content and use its ticket and details links", async () => {
  const { container } = render(<PosterCard item={movieItem()} date={date} />);
  const poster = screen.getByRole("link", { name: "View Anora" });
  expect(poster).toHaveAttribute("href", `/movies/anora?date=${date}`);
  expect(screen.getByRole("img")).toHaveAttribute("loading", "lazy");
  fireEvent.pointerEnter(card(), { pointerType: "mouse" });
  await advance(300);
  const preview = screen.getByRole("dialog");
  expect(container).not.toContainElement(preview);
  fireEvent.pointerLeave(card(), { pointerType: "mouse" });
  await advance(50);
  fireEvent.pointerEnter(preview, { pointerType: "mouse" });
  await advance(300);
  expect(preview).toBeInTheDocument();
  const ticket = within(preview).getByRole("link", { name: "23:00" });
  expect(ticket).toHaveAttribute("href", "https://tickets.example/seat");
  expect(ticket).toHaveAttribute("target", "_blank");
  const details = within(preview).getByRole("link", {
    name: "Movie details & all screening pages →",
  });
  expect(details).toHaveAttribute("href", `/movies/anora?date=${date}`);
  const activated = vi.fn((event: Event) => event.preventDefault());
  details.addEventListener("click", activated);
  fireEvent.click(details);
  expect(activated).toHaveBeenCalledOnce();
  fireEvent.pointerLeave(preview, { pointerType: "mouse" });
  await advance(200);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("ignores touch hover and opens Showtimes on touch with Escape restoring trigger focus", async () => {
  render(<PosterCard item={movieItem()} date={date} />);
  fireEvent.pointerEnter(card(), { pointerType: "touch" });
  await advance(300);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  const trigger = screen.getByRole("button", { name: "Showtimes for Anora" });
  fireEvent.pointerDown(trigger, { pointerType: "touch" });
  fireEvent.click(trigger);
  await advance(0);
  const preview = screen.getByRole("dialog");
  expect(
    within(preview).getByRole("button", { name: "Close preview" }),
  ).toHaveFocus();
  fireEvent.keyDown(preview, { key: "Escape" });
  await advance(0);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});

it("preserves the poster link as a plain navigable link", () => {
  render(<PosterCard item={movieItem()} date={date} />);
  const poster = screen.getByRole("link", { name: "View Anora" });
  expect(poster).toHaveAttribute("href", `/movies/anora?date=${date}`);
  expect(poster).not.toHaveAttribute("aria-haspopup");
});

it("keeps keyboard navigation on the poster and opens a focusable preview with Showtimes", async () => {
  render(<PosterCard item={movieItem()} date={date} />);
  act(() => screen.getByRole("link", { name: "View Anora" }).focus());
  await advance(300);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  const trigger = screen.getByRole("button", { name: "Showtimes for Anora" });
  act(() => trigger.focus());
  fireEvent.click(trigger); // Keyboard Enter activates a button in the browser.
  await advance(0);
  const preview = screen.getByRole("dialog");
  const details = within(preview).getByRole("link", {
    name: "Movie details & all screening pages →",
  });
  expect(details.tabIndex).toBe(0);
  act(() => details.focus());
  expect(details).toHaveFocus();
  fireEvent.click(
    within(preview).getByRole("button", { name: "Close preview" }),
  );
  await advance(0);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});
