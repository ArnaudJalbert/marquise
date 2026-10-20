import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { MoviePoster } from "./MoviePoster";

it("reserves poster dimensions, loads lazily, and falls back to the title after an image failure", () => {
  const view = render(
    <MoviePoster
      title="A film"
      posterUrl="https://posters.example/first.jpg"
    />,
  );
  const image = screen.getByRole("img", { name: "Poster for A film" });
  expect(image).toHaveAttribute("loading", "lazy");
  expect(image).toHaveAttribute("width", "400");
  expect(image).toHaveAttribute("height", "600");
  fireEvent.error(image);
  expect(screen.queryByRole("img")).toBeNull();
  expect(screen.getByText("A film")).toBeVisible();
  view.rerender(
    <MoviePoster
      title="Another film"
      posterUrl="https://posters.example/second.jpg"
    />,
  );
  expect(
    screen.getByRole("img", { name: "Poster for Another film" }),
  ).toHaveAttribute("src", "https://posters.example/second.jpg");
});
