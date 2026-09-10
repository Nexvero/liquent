# LQ-2653 – Authenticated post-login landing

## Status

Implemented as a narrow browser-facing completion of the controlled staging
OIDC path.

## Context

LQ-2652 made Google's successful callback shape compatible with the existing
verification chain. The controlled staging login then completed identity
binding and session issuance, but its fixed internal success destination `/`
still reached the edge default deny and returned 404.

That 404 did not mean authentication had failed. Persistent evidence confirmed
the consumed admission, external identity binding, and active browser session.
It did mean that the first successful browser journey had no safe terminal
document.

## Observable contract

When the complete OIDC callback composition and browser-session lookup are
available, the application exposes exactly one authenticated landing route:
`GET /`.

An active browser session receives a static HTML document with status 200. The
document says only that sign-in succeeded and that the authenticated session is
active. It contains no script, form, user identifier, workspace identifier,
provider subject, admission fact, CSRF material, membership, role, capability,
or research permission.

The response is `no-store` and uses `no-referrer`.

Authentication at this route establishes only the session actor. It does not
grant or imply workspace authority, ordinary membership, onboarding-management
capability, research access, or any other permission.

## Absence and rejection

A request without a session cookie redirects with 303 to `/login`. No session
lookup is attempted.

An invalid, malformed, expired, revoked, or unknown session is handled with the
same neutral redirect to `/login`. When a cookie was present it is cleared. The
browser cannot distinguish these conditions from the response.

The route does not disclose whether a user, identity binding, admission,
workspace, or historical session exists.

## Technical unavailability

If the session system of record cannot provide a decision, the route redirects
with 303 to `/login/unavailable` and preserves the cookie. This is a
detail-free technical-unavailability outcome, not an authentication decision.

No new exception or public error vocabulary is introduced. The behavior uses
the existing browser-session unavailability boundary and existing static
outcome page.

## Input boundary

The landing route accepts no query string. A query-bearing request returns an
empty 400 response and performs no session lookup.

Every method other than GET returns an empty 405 response with `Allow: GET` and
performs no session lookup. In particular, HEAD is not an implicit success
surface.

No request value may select a user, workspace, destination, role, capability,
or authorization result.

## Edge exposure

Staging exposes only the exact path `/` to the control plane. The existing
catch-all edge rule remains 404, so this slice does not widen the public route
surface below the root path.

The edge continues to terminate transport security and apply the established
security headers. The application remains responsible for session resolution
and neutral outcome selection.

## Composition boundary

The route is present only when OIDC callback handling and browser-session
lookup are both composed. The default application continues to return 404 at
`/`.

The existing persistent browser-session store is reused. There is no second
session source, fallback allow path, caller-supplied session principal, or
cached authorization decision.

Revoked or expired sessions therefore affect later landing decisions through
the same current system-of-record lookup used by the logout boundary.

## Explicit non-goals

This slice does not create or mutate users, workspaces, identity bindings,
admissions, memberships, roles, capabilities, research permissions, or browser
sessions.

It adds no schema, migration, SQL, persistence port, domain model, command-line
interface, provider configuration, secret, or bootstrap behavior.

It does not implement the product application, workspace selection, profile
display, navigation, onboarding management, or research UI. Those require
separate authority-aware slices.

It does not change the callback success destination. It makes the already
validated fixed internal destination observable and safe.

## Verification

Contract tests cover an active session, absent session, unknown session,
technical store unavailability, query rejection, every non-GET method, and the
default application without OIDC composition.

Edge tests require an exact root location, verify that it proxies to the
control plane, and retain the broad default-deny location.

The acceptance checkpoint for this slice is a successful controlled staging
OIDC journey that terminates at the static authenticated document rather than
an edge 404, while all existing login, callback, outcome, and health routes
remain unchanged.
