-- Controlled integration data. Run only in a fresh disposable database after
-- scripts/marquise-schema.sql. None of these rows are production listings.
INSERT INTO marquise.cinemas(id,name) VALUES
('cinema-1','Test Cinema One'),('cinema-2','Test Cinema Two');
INSERT INTO marquise.movies(id,title,directors,description,poster_url)
SELECT 'film-' || lpad(i::text,2,'0'), 'Controlled film ' || lpad(i::text,2,'0'),
       'Test Director', 'Controlled integration data, not a live listing.',
       CASE WHEN i % 3 = 0 THEN NULL ELSE 'https://posters.example/' || i || '.png' END
FROM generate_series(0,27) i;
INSERT INTO marquise.screenings(id,movie_id,cinema_id,showtime,language,ticket_url)
SELECT 'show-' || i || '-' || j, 'film-' || lpad(i::text,2,'0'),
       'cinema-' || (1+j%2),
       (now() AT TIME ZONE 'UTC') + interval '1 hour' + j * interval '1 minute',
       CASE WHEN j % 2 = 0 THEN 'VOSTF' ELSE 'VO' END,
       CASE WHEN j % 2 = 0 THEN NULL ELSE 'https://tickets.example/controlled' END
FROM generate_series(0,26) i CROSS JOIN generate_series(0,3) j;
