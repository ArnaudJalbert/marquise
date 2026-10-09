-- Install before enabling auth.enable_signup. Keeps human accounts invitation-only.
-- GoTrue inserts an invited account and sets invited_at within one transaction,
-- so validation must examine the final stored row when the transaction commits.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

CREATE OR REPLACE FUNCTION public.marquise_require_invitation()
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

REVOKE ALL ON FUNCTION public.marquise_require_invitation() FROM PUBLIC;
-- Managed Supabase grants TRIGGER access but not ownership of auth.users.
-- Keep the existing trigger on reapplication; replacing its function is enough.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_trigger
        WHERE tgname = 'marquise_auth_signup_policy'
          AND tgrelid = 'auth.users'::regclass
    ) THEN
        CREATE CONSTRAINT TRIGGER marquise_auth_signup_policy
        AFTER INSERT OR UPDATE ON auth.users
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION public.marquise_require_invitation();
    ELSIF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_trigger
        WHERE tgname = 'marquise_auth_signup_policy'
          AND tgrelid = 'auth.users'::regclass
          AND tgfoid = 'public.marquise_require_invitation()'::regprocedure
          AND tgdeferrable AND tginitdeferred AND tgenabled = 'O'
          AND tgtype = 21 AND tgqual IS NULL AND tgconstraint <> 0
    ) THEN
        RAISE EXCEPTION 'Existing Marquise Auth guard has an unexpected definition';
    END IF;
END;
$$;

COMMIT;
