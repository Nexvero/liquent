# LQ-2667 – Staging workspace Research-job index acceptance contract

## Purpose

LQ-2667 defines the observable staging acceptance boundary for the persistent
workspace Research-job index completed through LQ-2666.

Acceptance is read-only evidence. It grants no deployment, promotion,
bootstrap, identity, membership, permission, or Research mutation authority.

## Candidate binding

An acceptance attempt is bound to one immutable release candidate digest, one
configured HTTPS staging origin, and one execution time.

Evidence from another digest, origin, environment, execution, browser session,
or earlier deployment cannot satisfy the attempt.

The candidate must already have passed repository quality and release gates.
This contract cannot waive a failed image vulnerability gate or substitute a
mutable tag for an approved digest.

## Preconditions

The staging deployment, TLS endpoint, exact edge route, database migrations,
OIDC trust, admitted test identity, active workspace, active membership, and
Research-read permission must already exist through their separate authority
paths.

The acceptance probe creates none of those facts. Missing prerequisites fail
closed without attempting repair or bootstrap.

## Required observations

The bound execution must establish all of the following:

- unauthenticated `GET /research` does not disclose index content;
- authenticated current Research-read authority returns HTML success;
- the page carries `Cache-Control: no-store` and `Referrer-Policy: no-referrer`;
- an authorized empty workspace renders the explicit empty state;
- a committed visible job renders only its opaque JobId, status, and update time;
- UserId, WorkspaceId, session, CSRF, membership, revision, claim, worker, and artifact facts remain absent;
- caller-controlled query input is rejected and cannot select workspace or page size;
- committed Research permission removal affects the next request;
- technical store unavailability yields only the established detail-free unavailable outcome.

The authority-revocation and unavailability observations may use dedicated,
pre-authorized test fixtures. The probe itself receives no mutation capability.

## Exact surface

Only `https://<staging-origin>/research` is in scope. A trailing slash,
subpath, query-bearing success, alternate host, direct container address, or
Research API does not satisfy acceptance.

Redirects are not followed when classifying rejection or unavailability.
Cross-origin redirects, plaintext HTTP, and origin changes fail closed.

## Evidence and secrecy

Evidence records the candidate digest, normalized staging origin, execution
time, observation names, and pass/fail classification.

It must not retain cookies, authorization headers, OIDC codes, CSRF values,
email addresses, UserIds, WorkspaceIds, JobIds, response bodies, database
coordinates, secrets, or provider diagnostics.

Failed observations remain detail-free. Diagnostic material may be inspected
locally under existing operator controls but is not acceptance evidence.

## Freshness

Every observation performs a new request. Cached pages, browser history,
screenshots, prior probe output, and earlier acceptance evidence are not
current proof.

Revocation evidence must observe success before the separately authorized
mutation and neutral denial immediately afterward. Restoring test authority is
a separate operator action and is not performed by the read-only probe.

## Outcome

Acceptance succeeds only when every mandatory observation belongs to the same
bound execution and passes. Missing, duplicate, unknown, stale, or conflicting
observations fail closed.

Technical inability to make or classify any request is unavailability, not a
pass, neutral denial, partial acceptance, or retry promise.

No automatic promotion follows success. A separate release authority decides
whether the accepted candidate may advance.

## Explicit non-goals

This slice implements no HTTP client, CLI, evidence file, workflow, deployment,
promotion, rollback, DNS, TLS, OIDC, secret, or staging mutation.

It changes no schema, SQL, migration, application route, edge route, model,
port, function signature, container, release artifact, or test fixture.

It creates or mutates no user, workspace, membership, role, permission,
capability, session, job, result, claim, lease, artifact, or authority fact.

## Next step

A later slice may implement a closed evaluator for sanitized observations from
one bound execution. Network acquisition, operator CLI, and real staging use
remain separate after that evaluator is tested.
