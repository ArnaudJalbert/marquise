-- Run only against an empty, disposable PostgreSQL database.
\set ON_ERROR_STOP on
CREATE SCHEMA auth;
CREATE TABLE auth.users (
    id uuid PRIMARY KEY,
    is_anonymous boolean,
    invited_at timestamptz,
    raw_user_meta_data jsonb
);
-- The manually provisioned first Administrator predates this migration.
INSERT INTO auth.users (id, is_anonymous)
VALUES ('00000000-0000-0000-0000-000000000001', false);

\ir ../migrations/265-auth-signup-policy.sql

-- Anonymous creation commits successfully.
BEGIN;
INSERT INTO auth.users (id, is_anonymous)
VALUES ('00000000-0000-0000-0000-000000000002', true);
COMMIT;

-- GoTrue invitation inserts first, then updates invited_at before commit.
BEGIN;
INSERT INTO auth.users (id, is_anonymous)
VALUES ('00000000-0000-0000-0000-000000000003', false);
UPDATE auth.users SET invited_at = now()
WHERE id = '00000000-0000-0000-0000-000000000003';
COMMIT;

-- Existing human accounts can still sign in and receive role updates.
UPDATE auth.users SET raw_user_meta_data = '{}'::jsonb
WHERE id = '00000000-0000-0000-0000-000000000001';

DO $$
BEGIN
    -- Public email, phone, or magic-link creation cannot commit.
    BEGIN
        INSERT INTO auth.users (id, is_anonymous)
        VALUES ('00000000-0000-0000-0000-000000000004', false);
        SET CONSTRAINTS auth.marquise_auth_signup_policy IMMEDIATE;
        RAISE EXCEPTION 'Uninvited human creation was incorrectly accepted';
    EXCEPTION WHEN check_violation THEN
        NULL;
    END;

    -- Missing anonymous status does not bypass the guard.
    BEGIN
        INSERT INTO auth.users (id, is_anonymous)
        VALUES ('00000000-0000-0000-0000-000000000005', NULL);
        SET CONSTRAINTS auth.marquise_auth_signup_policy IMMEDIATE;
        RAISE EXCEPTION 'Missing anonymous status was incorrectly accepted';
    EXCEPTION WHEN check_violation THEN
        NULL;
    END;

    -- Anonymous callers cannot register a human identity by linking credentials.
    BEGIN
        UPDATE auth.users SET is_anonymous = false,
            raw_user_meta_data = '{"invited_at":"2026-10-08"}'::jsonb
        WHERE id = '00000000-0000-0000-0000-000000000002';
        SET CONSTRAINTS auth.marquise_auth_signup_policy IMMEDIATE;
        RAISE EXCEPTION 'Uninvited anonymous conversion was incorrectly accepted';
    EXCEPTION WHEN check_violation THEN
        NULL;
    END;

    IF (SELECT count(*) FROM auth.users) <> 3 THEN
        RAISE EXCEPTION 'Policy tests left unexpected accounts';
    END IF;
END;
$$;

-- Reapplying the migration preserves accounts and policy.
\ir ../migrations/265-auth-signup-policy.sql
\ir ../migrations/265-auth-signup-policy-rollback.sql
SELECT 'Auth signup policy checks passed' AS result;
