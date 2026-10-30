import type { CatalogueCinema, CatalogueMovie } from "marquise-components";

// Sample listings, cinema details, and booking links are deliberately fictional.
export const cinemas: CatalogueCinema[] = [
  {
    id: "moderne",
    name: "Cinéma Moderne",
    website: "https://www.cinemamoderne.com",
  },
  {
    id: "beaubien",
    name: "Cinéma Beaubien",
    website: "https://cinemabeaubien.com",
  },
  { id: "cinematheque", name: "Cinémathèque québécoise" },
  { id: "parc", name: "Cinéma du Parc" },
  { id: "forum", name: "Cineplex Forum" },
  { id: "quartier-latin", name: "Cineplex Odeon Quartier Latin" },
  { id: "dollar", name: "Dollar Cinema" },
];
export const today = "2026-10-30";
export const tomorrow = "2026-10-31";
export const weekend = ["2026-10-31", "2026-11-01"] as const;

const dates = Array.from({ length: 14 }, (_, index) => {
  const date = new Date(`${today}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + index);
  return date.toISOString().slice(0, 10);
});

function sampleScreenings(movieIndex: number, count: number) {
  return Array.from({ length: count }, (_, index) => {
    const dateIndex = Math.floor((index * dates.length) / count);
    const slot = count === dates.length * 25 ? index % 25 : index;
    const cinema =
      cinemas[(dateIndex * 3 + slot + movieIndex) % cinemas.length]!;
    const hour =
      count === dates.length * 25
        ? 10 + Math.floor(slot / 2)
        : 17 + (index % 5);
    return {
      cinemaId: cinema.id,
      date: dates[dateIndex]!,
      time: `${String(hour).padStart(2, "0")}:${slot % 2 ? "30" : "00"}`,
      language: ["VO", "VOA", "VOF", "VOSTF", "VOSTA", "VF"][index % 6]!,
      bookingUrl: "https://example.com/sample-booking",
    };
  });
}

const films: { movie: Omit<CatalogueMovie, "screenings">; count: number }[] = [
  {
    movie: {
      id: "dune",
      title: "Dune: Part Two",
      poster: "/posters/dune.jpg",
      year: 2024,
      director: "Denis Villeneuve",
      runtime: 166,
      synopsis:
        "Paul Atreides joins the Fremen on Arrakis. Sample synopsis for layout review.",
    },
    count: 350,
  },
  {
    movie: {
      id: "perfect-days",
      title: "Perfect Days",
      poster: "/posters/perfect-days.jpg",
      year: 2023,
      director: "Wim Wenders",
      runtime: 123,
    },
    count: 12,
  },
  {
    movie: {
      id: "past-lives",
      title: "Past Lives",
      poster: "/posters/past-lives.jpg",
      year: 2023,
      director: "Celine Song",
      runtime: 106,
    },
    count: 5,
  },
  {
    movie: {
      id: "spirited-away",
      title: "Spirited Away",
      poster: "/posters/spirited-away.jpg",
      year: 2001,
      director: "Hayao Miyazaki",
      runtime: 125,
    },
    count: 9,
  },
  {
    movie: {
      id: "jesse-james",
      title: "The Assassination of Jesse James by the Coward Robert Ford",
      poster: "/posters/jesse-james.jpg",
      year: 2007,
      director: "Andrew Dominik",
      runtime: 160,
    },
    count: 1,
  },
  {
    movie: {
      id: "arrival",
      title: "Arrival",
      poster: "/posters/arrival.jpg",
      year: 2016,
      director: "Denis Villeneuve",
      runtime: 116,
    },
    count: 3,
  },
];

export const movies: CatalogueMovie[] = films.map(
  ({ movie, count }, index) => ({
    ...movie,
    screenings: sampleScreenings(index, count),
  }),
);
