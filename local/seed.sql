-- Controlled test data in local PostgreSQL. Names and posters are real films;
-- screenings and booking links are fictional.
-- Repeatable: replace generated screenings only, retaining other database rows.
BEGIN;
INSERT INTO marquise.cinemas(id,name,address,city,website)
SELECT 'local-cinema-' || i, 'Local test cinema ' || i,
       i || ' Test Street', 'Montreal', 'https://example.com/local-cinema-' || i
FROM generate_series(1,7) i
ON CONFLICT (id) DO NOTHING;

INSERT INTO marquise.movies(id,title,release_year,directors,duration_minutes,description,poster_url)
VALUES
('local-dune','Dune: Part Two',2024,'Denis Villeneuve',166,
 'Local test data. Fictional dense schedule across seven cinemas for two weeks.', '/local-posters/dune.jpg'),
('local-sparse','Perfect Days',2023,'Wim Wenders',124,
 'Local test data. One fictional screening.', '/local-posters/perfect-days.jpg'),
('local/catalogue-only','Arrival',2016,'Denis Villeneuve',116,
 'Local test data. Catalogue movie without screenings.', '/local-posters/arrival.jpg'),
('local-film-01','Parasite',2019,NULL,NULL,'Local catalogue test film.','/local-posters/parasite.jpg'),
('local-film-02','The Grand Budapest Hotel',2014,NULL,NULL,'Local catalogue test film.','/local-posters/grand-budapest-hotel.jpg'),
('local-film-03','Past Lives',2023,NULL,NULL,'Local catalogue test film.','/local-posters/past-lives.jpg'),
('local-film-04','Spirited Away',2001,NULL,NULL,'Local catalogue test film.','/local-posters/spirited-away.jpg'),
('local-film-05','The Assassination of Jesse James by the Coward Robert Ford',2007,NULL,NULL,'Local catalogue test film.','/local-posters/jesse-james.jpg'),
('local-film-06','Aftersun',2022,NULL,NULL,'Local catalogue test film.','/local-posters/aftersun.jpg'),
('local-film-07','Portrait of a Lady on Fire',2019,NULL,NULL,'Local catalogue test film.','/local-posters/portrait-of-a-lady-on-fire.jpg'),
('local-film-08','In the Mood for Love',2000,NULL,NULL,'Local catalogue test film.','/local-posters/in-the-mood-for-love.jpg'),
('local-film-09','The Handmaiden',2016,NULL,NULL,'Local catalogue test film.','/local-posters/the-handmaiden.jpg'),
('local-film-10','Everything Everywhere All at Once',2022,NULL,NULL,'Local catalogue test film.','/local-posters/everything-everywhere-all-at-once.jpg'),
('local-film-11','Moonlight',2016,NULL,NULL,'Local catalogue test film.','/local-posters/moonlight.jpg'),
('local-film-12','The Matrix',1999,NULL,NULL,'Local catalogue test film.','/local-posters/the-matrix.jpg'),
('local-film-13','Oppenheimer',2023,NULL,NULL,'Local catalogue test film.','/local-posters/oppenheimer.jpg'),
('local-film-14','Poor Things',2023,NULL,NULL,'Local catalogue test film.','/local-posters/poor-things.jpg'),
('local-film-15','The Zone of Interest',2023,NULL,NULL,'Local catalogue test film.','/local-posters/the-zone-of-interest.jpg'),
('local-film-16','Eternal Sunshine of the Spotless Mind',2004,NULL,NULL,'Local catalogue test film.','/local-posters/eternal-sunshine.jpg'),
('local-film-17','Her',2013,NULL,NULL,'Local catalogue test film.','/local-posters/her.jpg'),
('local-film-18','The Truman Show',1998,NULL,NULL,'Local catalogue test film.','/local-posters/the-truman-show.jpg'),
('local-film-19','Whiplash',2014,NULL,NULL,'Local catalogue test film.','/local-posters/whiplash.jpg'),
('local-film-20','Roma',2018,NULL,NULL,'Local catalogue test film.','/local-posters/roma.jpg'),
('local-film-21','The Lighthouse',2019,NULL,NULL,'Local catalogue test film.','/local-posters/the-lighthouse.jpg'),
('local-film-22','The Florida Project',2017,NULL,NULL,'Local catalogue test film.','/local-posters/the-florida-project.jpg'),
('local-film-23','The Worst Person in the World',2021,NULL,NULL,'Local catalogue test film.','/local-posters/the-worst-person-in-the-world.jpg'),
('local-film-24','Drive My Car',2021,NULL,NULL,'Local catalogue test film.','/local-posters/drive-my-car.jpg'),
('local-film-25','The Tale of the Princess Kaguya',2013,NULL,NULL,'Local catalogue test film.','/local-posters/princess-kaguya.jpg'),
('local-film-26','Tokyo Story',1953,NULL,NULL,'Local catalogue test film.','/local-posters/tokyo-story.jpg'),
('local-film-27','The Godfather',1972,'Francis Ford Coppola',NULL,'Local catalogue test film.','/local-posters/the-godfather.jpg'),
('local-film-28','The Godfather Part II',1974,'Francis Ford Coppola',NULL,'Local catalogue test film.','/local-posters/the-godfather-part-ii.jpg'),
('local-film-29','Inception',2010,'Christopher Nolan',NULL,'Local catalogue test film.','/local-posters/inception.jpg'),
('local-film-30','The Dark Knight',2008,'Christopher Nolan',NULL,'Local catalogue test film.','/local-posters/the-dark-knight.jpg'),
('local-film-31','Pulp Fiction',1994,'Quentin Tarantino',NULL,'Local catalogue test film.','/local-posters/pulp-fiction.jpg'),
('local-film-32','The Shawshank Redemption',1994,'Frank Darabont',NULL,'Local catalogue test film.','/local-posters/shawshank-redemption.jpg'),
('local-film-33','Goodfellas',1990,'Martin Scorsese',NULL,'Local catalogue test film.','/local-posters/goodfellas.jpg'),
('local-film-34','2001: A Space Odyssey',1968,'Stanley Kubrick',NULL,'Local catalogue test film.','/local-posters/2001-a-space-odyssey.png'),
('local-film-35','Blade Runner',1982,'Ridley Scott',NULL,'Local catalogue test film.','/local-posters/blade-runner.png'),
('local-film-36','Before Sunrise',1995,'Richard Linklater',NULL,'Local catalogue test film.','/local-posters/before-sunrise.jpg'),
('local-film-37','Before Sunset',2004,'Richard Linklater',NULL,'Local catalogue test film.','/local-posters/before-sunset.jpg'),
('local-film-38','Before Midnight',2013,'Richard Linklater',NULL,'Local catalogue test film.','/local-posters/before-midnight.jpg'),
('local-film-39','Amélie',2001,'Jean-Pierre Jeunet',NULL,'Local catalogue test film.','/local-posters/amelie.jpg'),
('local-film-40','Chungking Express',1994,'Wong Kar-wai',NULL,'Local catalogue test film.','/local-posters/chungking-express.jpg'),
('local-film-41','The Royal Tenenbaums',2001,'Wes Anderson',NULL,'Local catalogue test film.','/local-posters/royal-tenenbaums.jpg'),
('local-film-42','The Social Network',2010,'David Fincher',NULL,'Local catalogue test film.','/local-posters/social-network.png'),
('local-film-43','Phantom Thread',2017,'Paul Thomas Anderson',NULL,'Local catalogue test film.','/local-posters/phantom-thread.png'),
('local-film-44','The Banshees of Inisherin',2022,'Martin McDonagh',NULL,'Local catalogue test film.','/local-posters/banshees-of-inisherin.jpg'),
('local-film-45','Anatomy of a Fall',2023,'Justine Triet',NULL,'Local catalogue test film.','/local-posters/anatomy-of-a-fall.jpg'),
('local-film-46','The Holdovers',2023,'Alexander Payne',NULL,'Local catalogue test film.','/local-posters/the-holdovers.jpg'),
('local-film-47','Little Women',2019,'Greta Gerwig',NULL,'Local catalogue test film.','/local-posters/little-women-2019.jpg'),
('local-film-48','The Fabelmans',2022,'Steven Spielberg',NULL,'Local catalogue test film.','/local-posters/the-fabelmans.jpg'),
('local-film-49','The French Dispatch',2021,'Wes Anderson',NULL,'Local catalogue test film.','/local-posters/the-french-dispatch.jpg'),
('local-film-50','Memories of Murder',2003,'Bong Joon-ho',NULL,'Local catalogue test film.','/local-posters/memories-of-murder.jpg')
ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title, poster_url=EXCLUDED.poster_url,
    release_year=EXCLUDED.release_year, directors=EXCLUDED.directors,
    duration_minutes=EXCLUDED.duration_minutes, description=EXCLUDED.description;

DELETE FROM marquise.screenings WHERE id LIKE 'local-screening-%';

-- Use Montreal wall time, then convert each day independently to UTC for DST.
INSERT INTO marquise.screenings(id,movie_id,cinema_id,showtime,language,ticket_url)
SELECT 'local-screening-dense-' || day || '-' || slot,
       'local-dune', 'local-cinema-' || (1 + slot % 7),
       ((date_trunc('day', now() AT TIME ZONE 'America/Montreal')
           + day * interval '1 day' + interval '9 hours'
           + slot * interval '30 minutes') AT TIME ZONE 'America/Montreal') AT TIME ZONE 'UTC',
       (ARRAY['VO','VOA','VOSTF','VF','VOSTA','VOF'])[1 + slot % 6],
       CASE WHEN slot % 3 = 0 THEN NULL ELSE 'https://example.com/local-test-booking' END
FROM generate_series(0,13) day CROSS JOIN generate_series(0,24) slot;

INSERT INTO marquise.screenings(id,movie_id,cinema_id,showtime,language,ticket_url)
SELECT 'local-screening-film-' || i, 'local-film-' || lpad(i::text,2,'0'),
       'local-cinema-' || (1 + i % 7),
       ((date_trunc('day', now() AT TIME ZONE 'America/Montreal')
           + interval '23 hours 59 minutes') AT TIME ZONE 'America/Montreal') AT TIME ZONE 'UTC',
       'VO', NULL
FROM generate_series(1,26) i;

INSERT INTO marquise.screenings(id,movie_id,cinema_id,showtime,language,ticket_url)
VALUES ('local-screening-sparse','local-sparse','local-cinema-1',
        ((date_trunc('day', now() AT TIME ZONE 'America/Montreal')
            + interval '1 day 18 hours') AT TIME ZONE 'America/Montreal') AT TIME ZONE 'UTC',
        'VOSTF', NULL);
COMMIT;
