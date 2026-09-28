# LQ-2672 – Staging Research-index response classifier

## Result

LQ-2672 implements a pure classifier for bounded responses associated with the
closed LQ-2671 request plan.

It performs no network access and returns only check, closed request phase, and
`passed`, `failed`, or `unavailable`.

## Classification

Expected status, empty-body closure, HTML media type, index row shape, minimum
visible fields, security headers, fixed query rejection, the two revocation
phases, and the detail-free unavailable redirect are checked explicitly.

Malformed status, duplicate or malformed headers, oversized or non-byte bodies,
and internal classification faults become technical unavailability. A valid
response that does not match the required observation becomes failure.

The transient response container hides headers and body from representation.
The returned classification retains no URL, status, header, body, credential,
identity, workspace, JobId, provider message, or diagnostic detail.

## Verification

Tests cover all nine planned responses, mismatch versus technical
unavailability, forbidden visible facts, revocation ordering, and rejection of
a detail-bearing unavailable redirect.

## Explicit non-goals

This slice adds no HTTP client, credential loader, network execution, retry,
redirect following, revocation mutation, evidence writer, CLI, workflow,
deployment, promotion, rollback, schema, migration, route, or package entry
point.

## Next step

A later reducer may require exactly one classification per single phase and the
ordered before/after revocation pair before producing the eight sanitized
LQ-2668 observations. Real acquisition and promotion remain separate.
