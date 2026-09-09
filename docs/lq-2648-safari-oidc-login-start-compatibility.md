# LQ-2648 Safari OIDC login-start compatibility

## Purpose

LQ-2648 repairs the public browser handoff introduced by LQ-2647 without
weakening the login-start boundary. Safari submitted the script-free form but
the deployed route answered with an empty 403. Safari then treated that
untyped empty navigation response as a downloadable file named `login`.

The observed staging evidence contained two rejected POST requests and no OIDC
callback. Consequently no Google authorization, external identity binding, or
Liquent session had occurred.

## Browser-origin decision

The preferred browser proof remains an exact `Origin` match against the
configured trusted login origin.

Some user agents may omit `Origin` for a same-origin HTML form navigation. A
missing `Origin` is accepted only when the browser-controlled
`Sec-Fetch-Site` value is exactly `same-origin`.

A present `Origin` never falls back to fetch metadata. It must match exactly.
The following requests remain rejected before the clock, material generator,
configuration lookup, or transaction store is reached:

- missing `Origin` without exact same-origin fetch metadata;
- `Origin: null`;
- a foreign, malformed, differently cased, or differently ported origin;
- `cross-site`, `same-site`, `none`, empty, or unknown fetch metadata;
- a matching origin accompanied by non-same-origin fetch metadata;
- a Referer without an accepted origin or fetch-metadata proof.

This fallback does not trust Host, Forwarded, X-Forwarded-Host, Referer, query,
form fields, or caller-selected provider data. Web content cannot set
`Sec-Fetch-Site` as an arbitrary request header, so a cross-site form cannot
turn itself into a same-origin browser navigation.

## Response compatibility

Neutral login-start rejections remain empty and detail-free. They now carry an
explicit `text/plain` media type in addition to `Cache-Control: no-store`.
This gives navigation clients a renderable empty response instead of an
untyped payload that Safari may download.

The media type discloses no rejection reason. Status codes, empty bodies,
absence of Location and Set-Cookie, and absence of Retry-After remain intact.
Successful starts remain empty 303 redirects with the authorization URL only
in Location and the host-only state-binding cookie.

## Preserved boundaries

LQ-2648 does not:

- accept a caller-supplied allow value, role, provider, state, or return path;
- create or mutate users, workspaces, memberships, roles, or permissions;
- change admission eligibility or bypass the controlled LQ-2646 admission;
- make SessionPrincipal an authority source;
- change callback verification, one-time transaction claiming, or revocation;
- change persistence, schema, migrations, ports, CLI, or provider secrets;
- publish, promote, deploy, or perform a real Google login.

## Verification

Focused route, runtime-wiring, and edge-contract tests cover 179 cases. The
complete suite covers 7,216 passing tests with 111 intentional skips.

Tests prove the Safari-compatible missing-Origin path succeeds only with exact
same-origin fetch metadata, while incomplete and foreign proofs fail before
all stateful collaborators. Every neutral rejection is still empty and now has
the browser-safe media type.

## Next boundary

Review, merge, release, and staging promotion remain separate controlled
operations. After promotion, one real browser login must be started, bound to
one authorized admission through the private operator, and completed exactly
once. That acceptance must verify one consumed admission, one external identity
binding, and one active session without exposing their identifiers.
