# LQ-2661 – Staging Research-read edge

## Result

LQ-2661 exposes the LQ-2660 read-only Research destination through the staging
edge at exactly `/research`.

The change adds one exact Nginx location. It does not expose a prefix, child
resource, Research API, job endpoint, internal endpoint, or management path.

## Exact public surface

The HTTPS edge proxies only `location = /research` to the control-plane path
`/research`.

The exact-match form is intentional. `/research/`, `/research/jobs`, encoded
suffixes, and every other unmatched path continue to reach the broad default
deny and return `404` at the edge.

No regex, prefix, rewrite, fallback, alias, or browser-supplied target is added.
The existing exact root, login, OIDC, outcome, and health locations remain
unchanged.

The HTTP listener still redirects requests to HTTPS without adding an
application proxy surface. TLS configuration and the ACME challenge exception
are unchanged.

## Proxy boundary

The location uses the existing internal control-plane upstream, HTTP/1.1
connection handling, forwarded host and scheme, and bounded proxy timeouts.

Only the edge publishes network ports. The control plane remains private on
the deployment network, and this slice changes no container network,
capability, volume, secret, or runtime identity.

The edge does not make an authorization decision. It supplies no allow
boolean, role, status, capability, permission, user identifier, or workspace
identifier to the application.

## Application authority remains decisive

The LQ-2660 route still resolves the active browser session, current workspace
context, and Research membership for every request.

The `SessionPrincipal` identifies only the actor. Public reachability of the
path grants no workspace visibility or Research authority.

Missing or ambiguous workspace context and Research authorization denial
remain the same empty application `404`. Technical store unavailability
continues to use the established detail-free `/login/unavailable` outcome.

Committed session revocation, lifecycle deactivation, membership deactivation,
or permission removal affects the next application request. The edge caches no
authorization result and introduces no alternate success path.

## Security headers and caching

The route inherits the existing HTTPS server security headers: HSTS,
`nosniff`, frame denial, `no-referrer`, and the default-deny content security
policy.

The application response additionally retains `no-store`. The edge adds no
cache, cookie transformation, content-type override, cross-origin permission,
or relaxed form policy.

The Google-specific form-action exception remains confined to the exact
`/login` location and is not repeated for `/research`.

## Verification

The edge contract test requires the exact location, exact upstream target,
bounded read timeout, and absence of Research prefix locations.

The existing test continues to require the broad default deny and exclusion of
readiness and internal metrics endpoints.

Application authorization and destination tests remain the behavioral boundary
for session, workspace, membership, denial, revocation, and unavailability.

## Explicit non-goals

This slice does not create or mutate any user, workspace, admission,
external-identity binding, session, membership, role, capability, permission,
authority, Research job, or artifact.

It adds no schema, table, migration, SQL statement, port, model, application
route, API payload, CLI, operator command, bootstrap action, secret, image,
container, or release artifact.

It does not expose `/v1/research/jobs`, job details, evidence, job creation,
workspace selection, management operations, or a Research path prefix.

No deployment, promotion, server mutation, DNS change, or real browser
acceptance is performed in this slice.

## Next step

After review and merge of the full stack, a separate controlled release and
staging promotion may deploy this exact edge configuration. Real acceptance
must verify authorized success, neutral denial, revocation, and continued
default deny without revealing persistent identifiers.
