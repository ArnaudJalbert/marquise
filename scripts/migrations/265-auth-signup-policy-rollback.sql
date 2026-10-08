-- Disable auth.enable_signup BEFORE removing the invitation guard.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
DROP TRIGGER IF EXISTS marquise_auth_signup_policy ON auth.users;
DROP FUNCTION IF EXISTS auth.marquise_require_invitation();
COMMIT;
