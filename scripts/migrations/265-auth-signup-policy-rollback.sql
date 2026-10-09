-- Disable auth.enable_signup BEFORE deactivating the invitation guard.
-- The project role cannot drop triggers on managed auth.users. Keep the trigger
-- and replace its project-owned function with a no-op. Forward migration restores it.
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
    RETURN NULL;
END;
$$;
REVOKE ALL ON FUNCTION public.marquise_require_invitation() FROM PUBLIC;
COMMIT;
