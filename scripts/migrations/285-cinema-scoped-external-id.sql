-- Run during a quiet import window, after explicit live-rollout approval.
-- Existing screening data and gateway-compatible constraint name are preserved.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

ALTER TABLE marquise.screenings
    DROP CONSTRAINT screenings_external_id_key,
    ADD CONSTRAINT screenings_external_id_key UNIQUE (cinema_id, external_id);

COMMIT;
