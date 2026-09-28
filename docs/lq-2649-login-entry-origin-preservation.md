# LQ-2649 — Login-entry origin preservation

## Status

Implemented as a narrow correction to the browser-facing OIDC login entry.

## Observed failure

The staging `/login` document was served with `Referrer-Policy: no-referrer`.
Safari and Chromium consequently submitted its same-origin HTML form with
`Origin: null` and `Sec-Fetch-Site: same-origin`.

The login-start route correctly rejected the present null origin before any
transaction was created. Browsers then rendered a neutral empty `403`; a
manual reload changed the method to `GET` and produced the expected empty
`405`. No request reached Google and no callback or session was created.

This was not a DNS, TLS, proxy reachability, provider, or credential failure.
Staging health and the login document remained available throughout.

## Decision

The static `/login` entry uses `Referrer-Policy: same-origin`.

This permits a same-origin form navigation to carry the concrete configured
origin to the login-start boundary. It does not disclose the login URL to a
cross-origin destination.

The `303` response that sends the browser to the identity provider continues
to use `Referrer-Policy: no-referrer`. The external provider therefore does not
receive the preceding Liquent URL as a referrer.

The staging edge applies the same policy specifically to `/login`. Because an
Nginx location-level `add_header` declaration replaces inherited declarations,
that location repeats the existing HSTS, content-type, frame, and CSP headers.
No security header is silently lost at the override boundary.

## Security invariants

- A present Origin must still equal the configured login origin exactly.
- `Origin: null` remains rejected, including with same-origin Fetch Metadata.
- A missing Origin is accepted only with exact `Sec-Fetch-Site: same-origin`.
- Cross-site, same-site, none, malformed, and conflicting metadata fail closed.
- Query values and request bodies remain prohibited.
- Login start accepts POST only and all neutral rejections remain empty.
- The browser supplies no provider, client, redirect, admission, role,
  permission, target, or authority value.
- Authentication identifies an actor; it grants no workspace authority.
- Admission and persistent authority resolution remain unchanged.

## Scope

This slice changes only the response policy of the static login entry, the
matching staging-edge location, and focused regression coverage.

It does not change OIDC configuration, provider trust, callback validation,
state or nonce handling, PKCE, cookies, sessions, admission, persistent users,
workspaces, memberships, capabilities, schemas, migrations, secrets, or
deployment automation.

It creates no user, workspace, membership, role, permission, admission, or
session fact.

## Verification contract

Automated coverage must prove that:

1. `/login` remains GET-only, script-free, input-free, and no-store.
2. The application emits `same-origin` only for the login-entry document.
3. The provider redirect retains `no-referrer`.
4. A null Origin remains neutral and rejected even with same-origin metadata.
5. The edge `/login` override retains every existing security header.
6. The CSP remains default-deny with only same-origin form submission allowed.

Staging verification must observe a browser POST with the concrete staging
origin, a `303` to the configured Google authorization endpoint, and no
regression in health or fail-closed rejection behavior.

## Next boundary

Review, release, promotion, and one real browser login remain separate gates.
Successful provider authentication must still pass callback, admission,
identity, and session validation before Liquent recognizes an actor.
