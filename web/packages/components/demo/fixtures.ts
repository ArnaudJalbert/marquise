import type { CatalogueCinema, CatalogueMovie } from "marquise-components";

// Review fixtures only. These are not real cinema listings or booking links.
export const cinemas: CatalogueCinema[] = [
  {
    id: "moderne",
    name: "Cinéma Moderne",
    address: "Sample address, 5150 boulevard Saint-Laurent, Montréal",
    website: "https://www.cinemamoderne.com",
  },
  {
    id: "beaubien",
    name: "Cinéma Beaubien",
    address: "Sample address, 2396 rue Beaubien Est, Montréal",
    website: "https://cinemabeaubien.com",
  },
  { id: "cinematheque", name: "Cinémathèque québécoise" },
];
export const today = "2026-10-30";
export const tomorrow = "2026-10-31";
export const weekend = ["2026-10-31", "2026-11-01"] as const;
export const movies: CatalogueMovie[] = [
  {
    id: "dune",
    title: "Dune: Part Two",
    poster: "/posters/dune.jpg",
    year: 2024,
    director: "Denis Villeneuve",
    runtime: 166,
    synopsis:
      "Paul Atreides joins the Fremen on Arrakis. Sample synopsis for layout review.",
  },
  {
    id: "perfect-days",
    title: "Perfect Days",
    year: 2023,
    director: "Wim Wenders",
    runtime: 123,
  },
  {
    id: "past-lives",
    title: "Past Lives",
    poster: "/posters/past-lives.jpg",
    year: 2023,
    director: "Celine Song",
    runtime: 106,
  },
  {
    id: "spirited-away",
    title: "Spirited Away",
    poster: "/posters/spirited-away.jpg",
    year: 2001,
    director: "Hayao Miyazaki",
    runtime: 125,
  },
  {
    id: "long-title",
    title: "The Assassination of Jesse James by the Coward Robert Ford",
    year: 2007,
    director: "Andrew Dominik",
    runtime: 160,
  },
  { id: "missing", title: "Untitled catalogue entry" },
].map((m, i) => ({
  ...m,
  screenings: [
    {
      cinemaId: "moderne",
      date: today,
      time: `18:${String(i * 5).padStart(2, "0")}`,
      language: "English",
      bookingUrl: "https://example.com/sample-booking",
    },
    { cinemaId: "beaubien", date: today, time: "20:30", language: "French" },
    {
      cinemaId: "moderne",
      date: tomorrow,
      time: "18:45",
      language: "English",
      bookingUrl: "https://example.com/sample-booking",
    },
    {
      cinemaId: "cinematheque",
      date: "2026-11-01",
      time: "19:00",
      language: "Japanese",
    },
  ],
}));
