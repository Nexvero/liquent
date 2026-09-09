# LQ-2650 — OIDC form redirect policy

## Status

Implemented as a narrow correction to the staging login entry CSP.

## Observed failure

The browser successfully loaded `/login` and submitted its same-origin form.
The login-start boundary accepted the request and returned `303` with an exact
Google authorization URL. Safari and Chromium nevertheless remained on an
empty document instead of following that redirect.

The login document's `form-action 'self'` policy applies across redirects. It
therefore admitted the initial Liquent POST but rejected the subsequent
cross-origin navigation to the Google authorization endpoint.

## Decision

Only the exact `/login` edge location extends `form-action` with
`https://accounts.google.com`.

The policy continues to allow the same-origin login-start POST. It permits the
resulting browser navigation only to Google's exact HTTPS authorization origin.
No wildcard, alternate scheme, subdomain pattern, callback origin, script
origin, frame origin, or general external navigation permission is added.

The server-wide default remains `form-action 'self'`. Other responses therefore
do not inherit the Google exception. `default-src 'none'` and
`frame-ancestors 'none'` remain unchanged on the login document.

## Preserved boundaries

- The login start remains POST-only and exact-origin checked.
- `Origin: null` remains rejected.
- The provider redirect remains `no-referrer`.
- State, nonce, PKCE, callback, admission, session, and authority behavior are
  unchanged.
- No Google client identifier or secret enters the document or edge config.
- No additional provider or arbitrary caller-selected destination is allowed.
- No schema, migration, persistence, port, model, or CLI decision is made.

## Verification

Static edge-contract coverage requires the exact Google authorization origin
inside `/login` and proves it is absent from the server-wide policy. Existing
route tests continue to cover the accepted concrete origin and rejected null
origin. A real browser login remains the final staging verification after the
reviewed edge configuration is released.
