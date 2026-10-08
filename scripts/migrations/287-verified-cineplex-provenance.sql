-- Separately approved provenance receipt for the five Screenings audited in #287.
-- Read-only verification on 2026-10-07 confirmed these immutable IDs and stored
-- Cineplex ticket links carrying the same VistaSessionId and LocationId=9172.
-- Do NOT infer provenance from cinema_source_assignments or broaden this receipt.
-- Requires 287-screening-source-provenance.sql and a registered cineplex source.
-- Does not change IDs, showtimes, or metadata. The next guarded import moves times.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

-- Stabilize every receipt field while checking ownership; run in a quiet window.
LOCK TABLE marquise.cinemas, marquise.movies, marquise.screenings
    IN SHARE ROW EXCLUSIVE MODE;

DO $$
DECLARE
    screening_ids TEXT[];
BEGIN
    SELECT array_agg(s.id)
    INTO screening_ids
    FROM (VALUES
        ('a297eb7aee024c8a80fd84ceeab2de7d', '597122', '66f77c4ca9c446fa863459d17123340f', 'DIGGER',        TIME '13:00', TIME '13:15'),
        ('cdc597ed360c4d1aac255dd4ea31ab7c', '597137', '66f77c4ca9c446fa863459d17123340f', 'DIGGER',        TIME '15:55', TIME '16:10'),
        ('d597fb40a95d43d6baea3e2cf790db48', '597142', 'c2ef9ab70a0b4a22b9e9490dfb633253', 'Chers Parents', TIME '14:00', TIME '14:05'),
        ('af6e45e97653455dbbac56047f28c5b1', '597152', 'c2ef9ab70a0b4a22b9e9490dfb633253', 'Chers Parents', TIME '16:20', TIME '16:25'),
        ('62db2eac23d24e48b0dfa9df86c38f08', '597161', 'c2ef9ab70a0b4a22b9e9490dfb633253', 'Chers Parents', TIME '18:30', TIME '18:35')
    ) AS receipt(screening_id, external_id, movie_id, movie_title, old_time, new_time)
    JOIN marquise.screenings s ON s.id = receipt.screening_id
    JOIN marquise.cinemas c ON c.id = s.cinema_id
    JOIN marquise.movies m ON m.id = s.movie_id
    WHERE c.id = '9fbeeb8d-b725-47b2-b10b-998331428d2b'
        AND c.name = 'Cinéma Cineplex Odeon Quartier Latin'
        AND s.external_id = receipt.external_id
        AND m.id = receipt.movie_id AND m.title = receipt.movie_title
        AND (s.source_name IS NULL OR s.source_name = 'cineplex')
        AND s.ticket_url LIKE 'https://apis.cineplex.com/prod/ticketing/api/v1/routing/redirect-to-ticketing?%'
        AND s.ticket_url ~ ('[?&]VistaSessionId=' || receipt.external_id || '(&|$)')
        AND s.ticket_url ~ '[?&]LocationId=9172(&|$)'
        AND s.showtime IN (
            (DATE '2026-10-07' + receipt.old_time)
                AT TIME ZONE 'America/Montreal' AT TIME ZONE 'UTC',
            (DATE '2026-10-07' + receipt.new_time)
                AT TIME ZONE 'America/Montreal' AT TIME ZONE 'UTC'
        );

    IF cardinality(screening_ids) IS DISTINCT FROM 5 THEN
        RAISE EXCEPTION 'Provenance receipt #287 does not match exactly five Screenings; no data changed';
    END IF;

    UPDATE marquise.screenings
    SET source_name = 'cineplex'
    WHERE id = ANY(screening_ids);
END;
$$;

COMMIT;
