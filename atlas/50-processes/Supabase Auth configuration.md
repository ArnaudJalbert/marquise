---
type: process
status: active
owner: Arno
review_date: 2027-09-02
---

# Supabase Auth configuration

Use this process to apply Marquise Auth settings to cloud Supabase project.

## Why config is explicit

`supabase config push` does not patch only keys written in `supabase/config.toml`. Missing keys take Supabase CLI defaults and can overwrite remote settings. Keep every remote value that must not change in `supabase/config.toml`.

Current file preserves project URL, redirect URLs, email confirmation and OTP policy, TOTP MFA, and disables Storage vector buckets. The last setting matters because vector buckets need paid Supabase plan.

## Apply configuration

1. Inspect `supabase/config.toml`. Expected Auth policy: public sign-up disabled, anonymous sign-ins disabled, JWT expiry `900` seconds.
2. Identify intended project. `supabase projects list` shows available projects. Confirm its name and ref before continuing.
3. Push with explicit ref:

   ```bash
   supabase config push --project-ref <project-ref>
   ```

4. Read every diff and approve only expected changes. A normal Marquise push updates Auth and leaves API, database, and Storage up to date.
5. Check Auth dashboard. Public sign-up must be off, Anonymous Sign-Ins off, and JWT expiry 900 seconds.

Do not use a bare `supabase config push` unless local project is linked to intended project.

## Recovery after an unexpected diff

Stop before approving. Update `supabase/config.toml` with current remote values for every setting that must stay unchanged, then push again with explicit project ref.

If an incomplete file was already pushed, restore affected values in the file and push it. For current Marquise configuration, this restores:

- `auth.site_url` to `http://localhost:3000`
- empty `auth.additional_redirect_urls`
- email confirmations, one-minute email frequency, and eight-character OTPs
- TOTP enrollment and verification
- `storage.vector.enabled = false`

Repeat dashboard check after recovery.

## Secrets

Never place project credentials, database connection strings, or service-role keys in `supabase/config.toml`. Keep them in secret manager. See [database setup](../../docs/setup.md) for application secrets and Auth account policy.
