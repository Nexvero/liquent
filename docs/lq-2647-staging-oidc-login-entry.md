# LQ-2647 — Staging OIDC login entry

## Status

Implemented as a repository slice. Review, merge, release, promotion and the
real controlled staging login remain separate operational steps.

## Objective

LQ-2647 provides the missing same-origin browser entry needed to execute the
controlled admission login from LQ-2646. The existing login-start endpoint is
POST-only and binds its short-lived state to an HttpOnly browser cookie. A
server-side request followed by opening only the provider URL cannot preserve
that binding and must continue to fail closed.

The new `/login` document lets the same browser issue the existing POST and
receive both the provider redirect and binding cookie. It does not change the
OIDC protocol, admission contract, callback, session model or authority model.

## Observable contract

The entry is present only when the complete OIDC login composition is active.
The default application therefore continues to expose no login surface.

`GET /login` returns one static HTML document containing exactly one form. The
form has no input fields and posts to `/v1/session/oidc/login`. It carries no
provider, issuer, client, redirect, state, admission, actor, workspace, role,
permission, capability, return path or caller-supplied authorization value.

The document contains no script and loads no external asset. It is marked
`no-store` and uses a no-referrer response policy. A query string is rejected
with an empty response rather than being interpreted or reflected.

Every non-GET method is owned explicitly and returns an empty 405 with `GET` as
the only allowed method. None of these responses starts an OIDC transaction.

## Edge boundary

Staging exposes exactly `/login` in addition to the existing exact liveness,
OIDC login-start and callback paths. The default edge route remains 404 and no
broader prefix is proxied.

The Content Security Policy remains default-deny and adds only
`form-action 'self'`. This permits the one same-origin form submission while
scripts, images, styles, frames, connections and cross-origin form targets
remain blocked by default.

## Authority and persistence boundaries

Rendering the entry grants no authority and creates no persistent fact. The
POST continues to create only a short-lived pending login transaction. The
browser cannot attach an admission; LQ-2646 remains the sole controlled path
that may bind an already authorized admission to one unambiguous pending login.

Authentication still identifies an actor but grants no membership, onboarding
management, research permission or other capability. All authority resolution
continues to use active system-of-record facts and later revocation continues
to affect later decisions.

This slice creates no user, workspace, membership, role, capability, external
identity binding, admission or session. It changes no schema, migration, model,
port, provider configuration, secret, DNS record or certificate.

## Verification

Focused tests verify route activation, absence without OIDC composition, the
single input-free and script-free form, privacy headers, query rejection, empty
method rejection, exact Edge proxying, default-deny routing and the restricted
same-origin form policy.

## Next controlled step

After review, release and staging promotion, an operator may open `/login`,
start exactly one Google login and pause at the provider. The private LQ-2646
operator can then bind one authorized admission before the same browser
continues.

The acceptance evidence must remain value-free and verify aggregate outcomes:
one consumed admission, one external identity binding and one valid session.
An authenticated application landing page, membership and research authority
remain separate later slices.
