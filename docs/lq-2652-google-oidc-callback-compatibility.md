# LQ-2652 — Google OIDC callback compatibility

## Status

Implemented as a repository slice after the first controlled staging admission
proved that Google returns a successful authorization response with additional
annotations. Review, release and staging promotion remain separate gates.

## Observed problem

The callback transport previously accepted a success form only when its query
contained exactly `state` and `code`, and the raw query gate allowed no more
than four components. Google returned `state`, `iss`, `code`, `scope`,
`authuser`, `hd` and `prompt` after consent.

The request therefore matched the browser cookie but was converted into a
neutral rejection before authorization-code verification. The admission was
consumed fail closed, no external identity was bound and no session was issued.

## Observable contract

A successful callback still requires exactly one non-empty `state` and exactly
one non-empty `code`.

The transport additionally recognizes these Google success annotations:

- `iss`;
- `scope`;
- `authuser`;
- `hd`; and
- `prompt`.

Each recognized annotation is optional, must occur at most once and must be
non-empty when present. The complete callback therefore remains bounded to at
most seven raw query components.

No annotation is trusted as an identity, tenant, domain, role, capability,
permission, redirect destination or authority decision. The values are not
forwarded to authorization-code verification. The verified ID token and the
existing system-of-record checks remain the only source of provider identity
and access decisions.

## Fail-closed behavior

The callback remains a neutral rejection when it contains:

- an unknown parameter;
- a duplicate parameter;
- an empty recognized annotation;
- a missing, duplicate or empty state;
- a missing, duplicate or empty authorization code;
- a provider error alongside a code; or
- more than seven raw query components.

Raw query size and per-component bounds remain unchanged. They are evaluated
before framework decoding, cookie matching or dependency access.

Once state and browser cookie match, a malformed callback still consumes the
pending transaction fail closed. Before a state match, rejection neither
claims a transaction nor clears a potentially newer browser cookie.

Technical failures remain detail-free and use the existing callback
unavailability destination. This slice adds no new public error type.

## Security boundaries

The change does not weaken PKCE, nonce, issuer, signature, audience, token-age,
active-user, active-workspace, admission-consumption or session-creation gates.

The `iss` query annotation does not replace issuer verification. The `hd`
annotation does not establish workspace membership or a domain policy. The
`scope`, `authuser` and `prompt` annotations do not grant permissions or select
an internal user.

No caller-supplied boolean, role, membership, capability or user identifier is
accepted. The callback still resolves the target through its consumed
admission and persistent external identity binding.

No query value is copied into logs, response bodies, cookies, redirects or
session material. Success and rejection responses remain empty, non-cacheable
and constrained to validated internal destinations.

## Scope exclusions

This slice creates no user, workspace, membership, role or management
capability. It creates no admission and does not authorize onboarding.

It changes no database schema, migration, port, persistence model, public
route, provider registration, client secret, redirect URI or edge location.

It does not add generic acceptance of arbitrary provider parameters. Further
provider-specific annotations require an explicit reviewed extension.

## Verification

Focused route tests prove that the observed seven-component Google success
form reaches the existing verifier and forwards only the authorization code.

Regression cases prove that unknown, duplicate and empty annotations reject,
that eight components fail before dependency access, and that the previous
privacy, cookie-clearing and fail-closed behavior remains intact.

## Next controlled step

After review, merge, release and staging promotion, start a fresh browser login
and provision a fresh one-time admission. The previous admission was correctly
consumed by the rejected callback and must never be reused.
