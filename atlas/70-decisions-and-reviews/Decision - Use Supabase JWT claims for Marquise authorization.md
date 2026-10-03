---
type: decision
status: active
owner: Arno
date: 2026-09-02
review_date: 2027-09-02
---

# Decision: Use Supabase JWT claims for Marquise authorization

## Context

Marquise needs authenticated API writes for humans and Bots while keeping public reads open. Clients must not receive privileged Supabase credentials.

## Decision

Use short-lived Supabase access JWTs for API identity. Verify asymmetric signature, issuer, audience, expiry, subject, and `app_metadata.marquise_role` at API boundary through the core access-token query and dedicated account identity reader. Valid Marquise roles are Member, Editor, and Administrator; Administrator includes Editor authorization. Keep Supabase reserved `role` unchanged. Do not duplicate role assignments in Marquise database tables.

## Rationale and trade-offs

Supabase remains identity provider and signing-key authority, avoiding another credential system. Signed application metadata allows authorization without per-request database or Auth API calls. Role changes take effect only after token refresh or expiry, bounded by 15-minute JWT lifetime.

## Consequences

- Public read, health, and readiness routes remain unauthenticated.
- Protected routes depend on reusable injected token-verification collaborators; existing business use cases remain authentication-agnostic.
- API needs project URL and asymmetric Supabase signing keys, not service-role key.
- Immediate role revocation and legacy HS256 verification remain out of scope.

## Related links

- [GitHub issue #261](https://github.com/ArnaudJalbert/marquise/issues/261)
- [GitHub issue #263](https://github.com/ArnaudJalbert/marquise/issues/263)
- [[../50-processes/Supabase Auth configuration]]
