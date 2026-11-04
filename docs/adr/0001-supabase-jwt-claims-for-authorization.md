# 0001: Supabase JWT claims for authorization

- **Status:** accepted
- **Date:** 2026-09-02
- **Issues:** [#261](https://github.com/ArnaudJalbert/marquise/issues/261), [#263](https://github.com/ArnaudJalbert/marquise/issues/263)

## Context

Marquise needs authenticated API writes while keeping public reads open. Clients must not receive privileged Supabase credentials.

## Decision

Use short-lived Supabase access JWTs for API identity. Verify asymmetric signature, issuer, audience, expiry, subject and `app_metadata.marquise_role` at the API boundary through the core access-token query and a dedicated account identity reader. Valid Marquise roles are Member, Editor and Administrator; Administrator includes Editor authorization. Keep the Supabase reserved `role` claim unchanged. Do not duplicate role assignments in Marquise database tables.

## Consequences

- Supabase stays the identity provider and signing-key authority, so there is no second credential system.
- Signed application metadata allows authorization without per-request database or Auth API calls. Role changes take effect only after token refresh or expiry, bounded by the 15-minute JWT lifetime.
- Public read, health and readiness routes stay unauthenticated.
- Protected routes depend on injected token-verification collaborators; business use cases stay authentication-agnostic.
- The API needs the project URL and asymmetric signing keys, not the service-role key.
- Immediate role revocation and legacy HS256 verification are out of scope.

Applying the Auth settings: [docs/setup.md#auth](../setup.md#auth).
