-- Controlled test data in local PostgreSQL. These are fictional schedules.
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
 'Local test data. Catalogue movie without screenings.', '/local-posters/arrival.jpg')
ON CONFLICT (id) DO NOTHING;

INSERT INTO marquise.movies(id,title,description)
SELECT 'local-film-' || lpad(i::text,2,'0'),
       CASE WHEN i = 26 THEN 'A deliberately long local test movie title that should keep its complete accessible name and aligned card rows'
            ELSE 'Local test film ' || lpad(i::text,2,'0') END,
       'Local test data. Missing optional metadata and poster are intentional.'
FROM generate_series(1,26) i
ON CONFLICT (id) DO NOTHING;

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
