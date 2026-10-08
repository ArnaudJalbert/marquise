-- Install before enabling auth.enable_signup. Keeps human accounts invitation-only.
-- GoTrue inserts an invited account and sets invited_at within one transaction,
-- so validation must examine the final stored row when the transaction commits.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

CREATE OR REPLACE FUNCTION auth.marquise_require_invitation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    -- Existing human accounts, including the first Administrator, remain valid.
    IF TG_OP = 'UPDATE' AND OLD.is_anonymous IS NOT TRUE THEN
        RETURN NULL;
    END IF;

    IF EXISTS (
        SELECT 1 FROM auth.users
        WHERE id = NEW.id
          AND is_anonymous IS NOT TRUE
          AND invited_at IS NULL
    ) THEN
        RAISE EXCEPTION 'Human accounts require an Administrator invitation'
            USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$;

REVOKE ALL ON FUNCTION auth.marquise_require_invitation() FROM PUBLIC;
DROP TRIGGER IF EXISTS marquise_auth_signup_policy ON auth.users;
CREATE CONSTRAINT TRIGGER marquise_auth_signup_policy
AFTER INSERT OR UPDATE ON auth.users
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION auth.marquise_require_invitation();

COMMIT;
