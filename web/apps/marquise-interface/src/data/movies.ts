import type { PosterMovie } from '@marquise/components';
import { toDateKey, parseDateKey } from '@marquise/components';
import { montrealTodayKey } from '@marquise/components';

/**
 * Poster URLs are hotlinked from Wikipedia/Wikimedia Commons (verified
 * working, editorial use of official theatrical posters) rather than
 * checked into this repo — avoids licensing/redistribution concerns and
 * repo bloat for a prototype fixture.
 */
const POSTERS = {
  idaho: 'https://upload.wikimedia.org/wikipedia/en/6/69/My_Own_Private_Idaho.png',
  huit: 'https://upload.wikimedia.org/wikipedia/en/4/46/8Mezzo.jpg',
  chump: 'https://upload.wikimedia.org/wikipedia/en/0/0e/L%26H_Chump_at_Oxford_1940.jpg',
  perfect: 'https://upload.wikimedia.org/wikipedia/en/c/c9/Perfect_Days_poster.jpg',
  portrait: 'https://upload.wikimedia.org/wikipedia/en/c/cb/Portrait_of_a_Lady_on_Fire.jpg',
  gleaners: 'https://upload.wikimedia.org/wikipedia/en/7/74/Les_glaneurs_et_la_glaneuse_%28film%29.jpg',
  mood: 'https://upload.wikimedia.org/wikipedia/en/4/45/In_the_Mood_for_Love_movie.jpg',
  playtime: 'https://upload.wikimedia.org/wikipedia/en/c/c8/Playtimeoriginalposter.jpg',
  stalker: 'https://upload.wikimedia.org/wikipedia/en/d/d4/Stalker_poster.jpg',
  paris: 'https://upload.wikimedia.org/wikipedia/en/d/db/Paris%2C_Texas_%281984_film_poster%29.png',
  umbrellas: 'https://upload.wikimedia.org/wikipedia/en/c/cc/The_Umbrellas_of_Cherbourg_%281964_film%29_poster.jpg',
  // "Rex: A Dinosaur's Story" (2024, dir. Toby Genkel) does not appear to be
  // a real released film — no poster could be found. Left unresolved on
  // purpose so PosterImage falls back to the documented neutral placeholder.
  rex: 'posters/rex.webp',
} as const;

// The original design spec anchored its mock week to fixed day-of-month
// values (14-20) with day 15 implicitly meaning "today". Bare day-of-month
// ints don't carry a month/year, so re-running this fixture on any day
// whose real date isn't 15 (i.e. almost always) produced a week with no
// relation to the actual current date. Anchor the same relative week to
// Montreal's actual "today" instead, so the fixture always spans a
// real, matchable week regardless of when the app runs.
const TODAY = parseDateKey(montrealTodayKey());
function D(dayOfMonthInOriginalSpec: number): string {
  const offset = dayOfMonthInOriginalSpec - 15;
  const date = new Date(TODAY);
  date.setDate(date.getDate() + offset);
  return toDateKey(date);
}

/**
 * Mock movie fixture reproduced from the Poster Wall Reference design spec.
 * Language is tracked per-showtime (`screenings[].lang`), not on the movie
 * itself — the same title can run a VO track and a VF track, even at
 * different cinemas, and that's a screening-level fact, not a movie-level
 * one. Several titles legitimately appear more than once here because
 * they're playing at more than one cinema (that's the whole point of an
 * aggregator) — those are separate `PosterMovie` entries, one per cinema;
 * `filterMovies` merges same-title entries back into one card per movie.
 */
export const MOVIES: PosterMovie[] = [
  { id: 'idaho', movieId: 'my-own-private-idaho', title: 'My Own Private Idaho', director: 'Gus Van Sant', year: 1991, runtimeMin: 104, genre: 'Drama', cinema: 'Cinéma Moderne', dates: [D(14), D(15)], screenings: [{ time: '17:15', lang: 'VO' }, { time: '19:45', lang: 'VO', ticketUrl: 'https://example.com/tickets/idaho-1' }, { time: '22:00', lang: 'VO' }], poster: POSTERS.idaho },
  { id: 'huit', movieId: '8-1-2', title: '8½', director: 'Federico Fellini', year: 1963, runtimeMin: 138, genre: 'Drama', cinema: 'Cinémathèque québécoise', dates: [D(14)], screenings: [{ time: '18:30', lang: 'VO' }, { time: '21:00', lang: 'VO', ticketUrl: 'https://example.com/tickets/huit-1' }], poster: POSTERS.huit },
  { id: 'chump', movieId: 'a-chump-at-oxford', title: 'A Chump at Oxford', director: 'Alfred Goulding', year: 1940, runtimeMin: 63, genre: 'Comedy', cinema: 'Cinémathèque québécoise', dates: [D(15), D(16)], screenings: [{ time: '14:15', lang: 'VO' }, { time: '20:40', lang: 'VO' }], poster: POSTERS.chump },
  { id: 'perfect', movieId: 'perfect-days', title: 'Perfect Days', director: 'Wim Wenders', year: 2023, runtimeMin: 124, genre: 'Drama', cinema: 'Cinéma Beaubien', dates: [D(16), D(17), D(18)], screenings: [{ time: '16:00', lang: 'VO' }, { time: '21:30', lang: 'VO', ticketUrl: 'https://example.com/tickets/perfect-1' }], poster: POSTERS.perfect },
  { id: 'portrait', movieId: 'portrait-of-a-lady-on-fire', title: 'Portrait of a Lady on Fire', director: 'Céline Sciamma', year: 2019, runtimeMin: 122, genre: 'Drama', cinema: 'Cinéma Public', dates: [D(17)], screenings: [{ time: '19:00', lang: 'VF', ticketUrl: 'https://example.com/tickets/portrait-1' }], poster: POSTERS.portrait },
  { id: 'rex', movieId: 'rex-a-dinosaurs-story', title: "Rex: A Dinosaur's Story", director: 'Toby Genkel', year: 2024, runtimeMin: 91, genre: 'Family', cinema: 'Cineplex Forum', dates: [D(18), D(19), D(20)], screenings: [{ time: '14:00', lang: 'VF' }, { time: '16:15', lang: 'VF' }], poster: POSTERS.rex },
  { id: 'gleaners', movieId: 'the-gleaners-and-i', title: 'The Gleaners and I', director: 'Agnès Varda', year: 2000, runtimeMin: 82, genre: 'Documentary', cinema: 'Cinéma du Musée', dates: [D(19)], screenings: [{ time: '18:15', lang: 'VO', ticketUrl: 'https://example.com/tickets/gleaners-1' }], poster: POSTERS.gleaners },
  { id: 'mood', movieId: 'in-the-mood-for-love', title: 'In the Mood for Love', director: 'Wong Kar-wai', year: 2000, runtimeMin: 98, genre: 'Drama', cinema: 'Cinéma Moderne', dates: [D(14), D(16), D(18), D(20)], screenings: [{ time: '20:15', lang: 'VO', ticketUrl: 'https://example.com/tickets/mood-1' }], poster: POSTERS.mood },
  { id: 'playtime', movieId: 'playtime', title: 'Playtime', director: 'Jacques Tati', year: 1967, runtimeMin: 115, genre: 'Comedy', cinema: 'Cinéma Impérial', dates: [D(15), D(17), D(19)], screenings: [{ time: '15:30', lang: 'VO' }], poster: POSTERS.playtime },
  { id: 'stalker', movieId: 'stalker', title: 'Stalker', director: 'Andrei Tarkovsky', year: 1979, runtimeMin: 162, genre: 'Sci-Fi', cinema: 'Cinéma Excentris', dates: [D(20)], screenings: [{ time: '20:00', lang: 'VO', ticketUrl: 'https://example.com/tickets/stalker-1' }], poster: POSTERS.stalker },
  { id: 'paris', movieId: 'paris-texas', title: 'Paris, Texas', director: 'Wim Wenders', year: 1984, runtimeMin: 147, genre: 'Drama', cinema: 'Cinéma Moderne', dates: [D(16)], screenings: [{ time: '17:45', lang: 'VO' }], poster: POSTERS.paris },
  { id: 'umbrellas', movieId: 'the-umbrellas-of-cherbourg', title: 'The Umbrellas of Cherbourg', director: 'Jacques Demy', year: 1964, runtimeMin: 91, genre: 'Musical', cinema: 'Cinéma Public', dates: [D(20)], screenings: [{ time: '18:45', lang: 'VF', ticketUrl: 'https://example.com/tickets/umbrellas-1' }], poster: POSTERS.umbrellas },
  { id: 'moderne1', movieId: 'playtime', title: 'Playtime', director: 'Jacques Tati', year: 1967, runtimeMin: 115, genre: 'Comedy', cinema: 'Cinéma Beaubien', dates: [D(14)], screenings: [{ time: '19:15', lang: 'VF' }], poster: POSTERS.playtime },
  { id: 'gleaners2', movieId: 'the-gleaners-and-i', title: 'The Gleaners and I', director: 'Agnès Varda', year: 2000, runtimeMin: 82, genre: 'Documentary', cinema: 'Cinéma Excentris', dates: [D(15)], screenings: [{ time: '21:00', lang: 'VF', ticketUrl: 'https://example.com/tickets/gleaners-2' }], poster: POSTERS.gleaners },
  { id: 'stalker2', movieId: 'stalker', title: 'Stalker', director: 'Andrei Tarkovsky', year: 1979, runtimeMin: 162, genre: 'Sci-Fi', cinema: 'Cinéma Impérial', dates: [D(17)], screenings: [{ time: '21:30', lang: 'VF', ticketUrl: 'https://example.com/tickets/stalker-2' }], poster: POSTERS.stalker },
  { id: 'idaho2', movieId: 'my-own-private-idaho', title: 'My Own Private Idaho', director: 'Gus Van Sant', year: 1991, runtimeMin: 104, genre: 'Drama', cinema: 'Cinéma du Musée', dates: [D(19), D(20)], screenings: [{ time: '21:45', lang: 'VO', ticketUrl: 'https://example.com/tickets/idaho-2' }], poster: POSTERS.idaho },
  { id: 'rex2', movieId: 'rex-a-dinosaurs-story', title: "Rex: A Dinosaur's Story", director: 'Toby Genkel', year: 2024, runtimeMin: 91, genre: 'Family', cinema: 'Cineplex Cavendish', dates: [D(16), D(18)], screenings: [{ time: '13:00', lang: 'VO' }], poster: POSTERS.rex },
];
