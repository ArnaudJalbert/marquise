import type { PosterMovie } from '@marquise/components';
import { toDateKey, parseDateKey } from '@marquise/components';
import { montrealTodayKey } from '../timezone';

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
  { id: 'idaho', title: 'My Own Private Idaho', director: 'Gus Van Sant', year: 1991, runtimeMin: 104, format: '35mm', genre: 'Drama', cinema: 'Cinéma Moderne', dates: [D(14), D(15)], screenings: [{ time: '5:15 PM', lang: 'VO' }, { time: '7:45 PM', lang: 'VO' }, { time: '10:00 PM', lang: 'VO' }], poster: POSTERS.idaho },
  { id: 'huit', title: '8½', director: 'Federico Fellini', year: 1963, runtimeMin: 138, format: 'DCP', genre: 'Drama', cinema: 'Cinémathèque québécoise', dates: [D(14)], screenings: [{ time: '6:30 PM', lang: 'VO' }, { time: '9:00 PM', lang: 'VO' }], poster: POSTERS.huit },
  { id: 'chump', title: 'A Chump at Oxford', director: 'Alfred Goulding', year: 1940, runtimeMin: 63, format: '16mm', genre: 'Comedy', cinema: 'Cinémathèque québécoise', dates: [D(15), D(16)], screenings: [{ time: '2:15 PM', lang: 'VO' }, { time: '8:40 PM', lang: 'VO' }], poster: POSTERS.chump },
  { id: 'perfect', title: 'Perfect Days', director: 'Wim Wenders', year: 2023, runtimeMin: 124, format: 'DCP', genre: 'Drama', cinema: 'Cinéma Beaubien', dates: [D(16), D(17), D(18)], screenings: [{ time: '4:00 PM', lang: 'VO' }, { time: '9:30 PM', lang: 'VO' }], poster: POSTERS.perfect },
  { id: 'portrait', title: 'Portrait of a Lady on Fire', director: 'Céline Sciamma', year: 2019, runtimeMin: 122, format: '35mm', genre: 'Drama', cinema: 'Cinéma Public', dates: [D(17)], screenings: [{ time: '7:00 PM', lang: 'VF' }], poster: POSTERS.portrait },
  { id: 'rex', title: "Rex: A Dinosaur's Story", director: 'Toby Genkel', year: 2024, runtimeMin: 91, format: 'DCP', genre: 'Family', cinema: 'Cineplex Forum', dates: [D(18), D(19), D(20)], screenings: [{ time: '2:00 PM', lang: 'VF' }, { time: '4:15 PM', lang: 'VF' }], poster: POSTERS.rex },
  { id: 'gleaners', title: 'The Gleaners and I', director: 'Agnès Varda', year: 2000, runtimeMin: 82, format: 'DCP', genre: 'Documentary', cinema: 'Cinéma du Musée', dates: [D(19)], screenings: [{ time: '6:15 PM', lang: 'VO' }], poster: POSTERS.gleaners },
  { id: 'mood', title: 'In the Mood for Love', director: 'Wong Kar-wai', year: 2000, runtimeMin: 98, format: '35mm', genre: 'Drama', cinema: 'Cinéma Moderne', dates: [D(14), D(16), D(18), D(20)], screenings: [{ time: '8:15 PM', lang: 'VO' }], poster: POSTERS.mood },
  { id: 'playtime', title: 'Playtime', director: 'Jacques Tati', year: 1967, runtimeMin: 115, format: 'DCP', genre: 'Comedy', cinema: 'Cinéma Impérial', dates: [D(15), D(17), D(19)], screenings: [{ time: '3:30 PM', lang: 'VO' }], poster: POSTERS.playtime },
  { id: 'stalker', title: 'Stalker', director: 'Andrei Tarkovsky', year: 1979, runtimeMin: 162, format: '35mm', genre: 'Sci-Fi', cinema: 'Cinéma Excentris', dates: [D(20)], screenings: [{ time: '8:00 PM', lang: 'VO' }], poster: POSTERS.stalker },
  { id: 'paris', title: 'Paris, Texas', director: 'Wim Wenders', year: 1984, runtimeMin: 147, format: '35mm', genre: 'Drama', cinema: 'Cinéma Moderne', dates: [D(16)], screenings: [{ time: '5:45 PM', lang: 'VO' }], poster: POSTERS.paris },
  { id: 'umbrellas', title: 'The Umbrellas of Cherbourg', director: 'Jacques Demy', year: 1964, runtimeMin: 91, format: 'DCP', genre: 'Musical', cinema: 'Cinéma Public', dates: [D(20)], screenings: [{ time: '6:45 PM', lang: 'VF' }], poster: POSTERS.umbrellas },
  { id: 'moderne1', title: 'Playtime', director: 'Jacques Tati', year: 1967, runtimeMin: 115, format: 'DCP', genre: 'Comedy', cinema: 'Cinéma Beaubien', dates: [D(14)], screenings: [{ time: '7:15 PM', lang: 'VF' }], poster: POSTERS.playtime },
  { id: 'gleaners2', title: 'The Gleaners and I', director: 'Agnès Varda', year: 2000, runtimeMin: 82, format: 'DCP', genre: 'Documentary', cinema: 'Cinéma Excentris', dates: [D(15)], screenings: [{ time: '9:00 PM', lang: 'VF' }], poster: POSTERS.gleaners },
  { id: 'stalker2', title: 'Stalker', director: 'Andrei Tarkovsky', year: 1979, runtimeMin: 162, format: '35mm', genre: 'Sci-Fi', cinema: 'Cinéma Impérial', dates: [D(17)], screenings: [{ time: '9:30 PM', lang: 'VF' }], poster: POSTERS.stalker },
  { id: 'idaho2', title: 'My Own Private Idaho', director: 'Gus Van Sant', year: 1991, runtimeMin: 104, format: '35mm', genre: 'Drama', cinema: 'Cinéma du Musée', dates: [D(19), D(20)], screenings: [{ time: '9:45 PM', lang: 'VO' }], poster: POSTERS.idaho },
  { id: 'rex2', title: "Rex: A Dinosaur's Story", director: 'Toby Genkel', year: 2024, runtimeMin: 91, format: 'DCP', genre: 'Family', cinema: 'Cineplex Cavendish', dates: [D(16), D(18)], screenings: [{ time: '1:00 PM', lang: 'VO' }], poster: POSTERS.rex },
];
