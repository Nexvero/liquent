# LQ-2675 – Staging Research-index HTTP acquisition adapter

## Result

LQ-2675 implements one bounded HTTP acquisition for one already validated
LQ-2671 request. It returns the transient response container consumed by the
LQ-2672 classifier.

The adapter executes no plan, retry, redirect, revocation, restoration,
evidence write, deployment, or promotion.

## Request boundary

The method and exact URL come only from the closed request object. Anonymous
slots reject supplied sessions; authorized slots require one opaque session.

Inherited Cookie and Authorization headers are removed. An authorized request
receives only the dedicated Liquent session cookie. The opaque token is bounded,
syntax checked, and excluded from representations.

Every request asks for HTML with identity encoding, uses fixed timeouts, follows
no redirects, and is sent exactly once without client authentication.

## Response boundary

Compressed responses, invalid or excessive declared lengths, streamed bodies
beyond 64 KiB, transport faults, and client faults yield the same detail-free
technical unavailability.

Successful acquisition returns only status, response headers, and bounded raw
bytes for immediate classification. Headers and body are hidden from object
representation and are not acceptance evidence.

## Verification

Tests prove inherited-credential removal, exact session-cookie use, slot/session
matching, encoding and byte limits, and suppression of transport diagnostics.

## Explicit non-goals

This slice adds no credential loader or persistence, multi-request coordinator,
revocation mutation, evidence file, CLI, workflow, deployment, promotion,
rollback, schema, migration, route, image, secret, or installed operator.

## Next step

A later coordinator may execute independently authorized stages and immediately
classify each bounded response. Revocation mutation, credential provisioning,
real staging execution, evidence writing, and promotion remain separate.
