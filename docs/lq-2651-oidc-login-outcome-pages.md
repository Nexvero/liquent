# LQ-2651 — OIDC Login Outcome Pages

## Status

Implemented as a repository slice. Review, merge, release, edge activation and
the controlled staging admission remain separate operational steps.

## Problem

The real staging browser flow now reaches Google and returns to Liquent. A
callback which cannot complete redirects to one of the already configured
internal destinations:

- `/login/rejected` for a neutral rejection; or
- `/login/unavailable` for detail-free technical unavailability.

Neither exact destination had an application page or an edge route. The
browser therefore displayed `404`, hiding the intentional fail-closed outcome
behind what looked like a broken callback.

## Observable contract

Both destinations are available only when the complete OIDC login composition
is active. A default or partially composed application continues to return
`404`, preserving the existing all-or-none boundary.

An exact query-free `GET` returns a small static HTML document with HTTP 200.
The rejection page says only that sign-in could not be completed. The
unavailable page says only that sign-in is temporarily unavailable. Both state
that access has not changed and provide one same-origin link back to `/login`.

The pages do not disclose:

- whether a user, workspace, external binding or admission exists;
- whether an admission is absent, expired, consumed or unbound;
- any provider response, subject, email address or internal identifier;
- any authority, membership, capability or research permission state; or
- any exception, persistence, network or configuration detail.

This keeps neutral absence or rejection distinct from detail-free technical
unavailability without making either state an enumeration surface.

## Request boundary

The pages accept no browser-supplied values. Query strings are rejected with an
empty HTTP 400 and are never rendered. Every method other than `GET`, including
`HEAD`, is owned explicitly and receives an empty HTTP 405 with `Allow: GET`.

Successful documents are script-free and form-free. They carry `no-store` and
`no-referrer`; the existing edge headers retain `default-src 'none'`, frame
protection, MIME-sniffing protection and HTTPS transport protection.

No session or OIDC cookie is read, created, changed or cleared by these pages.
Visiting or retrying either page performs no identity, admission or authority
mutation.

## Edge boundary

The staging edge adds only two exact locations for `/login/rejected` and
`/login/unavailable`. It does not expose `/login/`, a wildcard, or a broader
API prefix. All other unknown paths remain under the existing default `404`.

The Google authorization exception remains confined to the exact `/login`
entry document. The two outcome pages inherit the server-wide
`form-action 'self'` policy and contain no form.

## Relationship to controlled admission

This slice makes the current rejection understandable; it does not turn that
rejection into successful admission. Google authenticates the external person
but grants no Liquent authority.

The existing LQ-2646 operator must still resolve onboarding authority from the
system of record, provision one short-lived admission for the existing target
user and workspace, and bind it server-side to exactly one pending browser
login. No state, admission handle, role or caller-supplied allow value may be
accepted from the browser.

Only the callback may then atomically consume the admission, create or resolve
the external identity binding and issue a session. Ordinary membership,
management capability and research permissions remain separate facts.

## Verification

Focused tests establish that:

- both exact pages render only under complete OIDC composition;
- their messages remain provider- and admission-neutral;
- neither document contains script or form markup;
- query values and non-GET methods return empty rejections;
- cache and referrer protections are present; and
- the edge exposes exactly both destinations while retaining default deny.

## Non-goals and next operation

No schema, migration, model, port, persistence or provider configuration is
changed. No user, workspace, membership, role, capability, permission,
admission, external identity binding or session is created in this slice.

After review, merge, release and promotion, the next controlled staging
operation is the LQ-2646 sequence: begin exactly one fresh browser login, pause
at Google, apply one privately authorized admission decision, then continue the
same browser flow and verify the resulting session without disclosing identity
material.

