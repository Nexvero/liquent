# LQ-2670 – Staging Research-index observation acquisition contract

## Purpose

LQ-2670 defines the read-only acquisition boundary that may later supply
sanitized observations to the LQ-2668 evaluator and LQ-2669 offline tool.

Acquisition observes an already deployed candidate. It grants no release,
deployment, promotion, identity, workspace, membership, permission, Research,
repair, or rollback authority.

## Binding

One acquisition is bound before its first request to one canonical immutable
candidate digest, one exact HTTPS staging origin, and one UTC execution time.

Every request uses the exact origin and `/research` path from that binding.
Caller-supplied hosts, paths, query parameters, redirects, workspace selectors,
page sizes, role names, allow booleans, and authority claims are not trusted.

The deployed candidate digest is an external prerequisite. The acquisition
cannot infer it from a mutable tag or replace repository and image gates.

## Inputs and credentials

The acquisition receives only separately provisioned opaque session material
for the exact admitted test cases. It must not receive passwords, OIDC codes,
refresh tokens, database coordinates, management credentials, or mutation
capabilities.

Session material identifies an authenticated actor but is not authority.
Workspace and Research-read authority remain freshly resolved by the deployed
system of record for every request.

Credentials are held only for the request that needs them. They are never
written to observation output, command arguments, logs, diagnostics, URLs, or
exception text.

## Request discipline

Each observation uses a new request with redirects disabled, bounded connect,
read, write, pool, and total time, identity content encoding, and a bounded
response body.

Responses from another origin, redirects, malformed headers, excessive bodies,
transport faults, time faults, and incomplete reads are technical
unavailability. They are never acceptance or neutral authorization rejection.

The anonymous and query-bearing checks send no credential. Authorized checks
use only the credential assigned to that exact case. Credentials cannot be
reused to select another workspace or broaden the request.

## Sanitized classifications

Acquisition emits only the closed check name and `passed`, `failed`, or
`unavailable`. It emits no status code, URL, header value, body fragment,
redirect target, cookie, token, identity, WorkspaceId, UserId, JobId, provider
message, timing detail, or exception detail.

A normal absence or authority rejection is classified neutrally only where the
corresponding check contract requires closure. A response that cannot be
reliably classified is detail-free technical unavailability.

The acquisition does not assemble, write, sign, or accept the final evidence.
The evaluator remains the sole component that reduces the complete sanitized
set to an overall outcome.

## Freshness and revocation

No response, authorization decision, workspace context, or classification is
cached. Every check is evaluated from its own current response.

The revocation check requires two separately acquired observations around a
separately authorized mutation: success before and neutral closure after. The
acquisition performs neither revocation nor restoration and receives no handle
that could do so.

The unavailability check likewise uses a separately controlled fixture or
fault boundary. Acquisition may observe it but cannot create, repair, or clear
the condition.

## Failure behavior

Unknown cases, missing inputs, duplicate execution, invalid binding, ambiguous
responses, unavailable clocks, and any internal or transport error fail closed.

Failure output is detail-free. Diagnostic data may remain transiently inside
existing protected operational controls, but it is not acceptance evidence and
must not cross this boundary.

## Explicit non-goals

This slice implements no HTTP client, request builder, response classifier,
credential loader, CLI, file codec, evidence writer, workflow, service, timer,
deployment, promotion, rollback, DNS, TLS, OIDC, or live staging execution.

It changes no application or edge route, schema, table, SQL, migration, model,
port, public signature, package entry point, image, or release artifact.

It creates or mutates no user, workspace, membership, role, permission,
capability, session, job, result, claim, lease, artifact, or authority fact.

## Next step

A later slice may implement a pure closed request plan for the non-mutating
HTTP observations. Response classification, credential loading, real network
acquisition, revocation coordination, evidence writing, and promotion remain
separate boundaries.
