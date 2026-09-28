# LQ-2673 – Staging Research-index classification reducer

## Result

LQ-2673 closes the boundary between the nine LQ-2672 response classifications
and the eight sanitized observations consumed by LQ-2668.

The reducer performs no I/O, network access, persistence, authority lookup,
mutation, deployment, or promotion.

## Exact set

Input must be a tuple containing exactly one single-phase classification for
each non-revocation check and exactly one before- plus one after-revocation
classification. Missing, duplicate, unknown, or incorrectly phased input is
rejected before observations are produced.

Output contains exactly one observation for every closed acceptance check in
canonical order. No URL, response, status, header, body, credential, identity,
workspace, JobId, timing, provider, or diagnostic detail crosses the boundary.

## Revocation reduction

The revocation observation passes only when both phases pass. Either technical
unavailability makes the combined observation unavailable. Otherwise any
failure makes it failed.

This reduction proves only the supplied before/after response classifications.
It does not perform, authorize, restore, or infer the revocation mutation.

## Verification

Tests prove canonical eight-observation output, both revocation phases,
unavailability precedence, and fail-closed rejection of missing, duplicate,
wrong-phase, list, and untyped input.

## Explicit non-goals

This slice adds no HTTP client, credential loader, network execution, evidence
file, CLI, workflow, mutation, deployment, promotion, rollback, schema,
migration, route, image, or installed operator.

## Next step

A later composition slice may connect the pure request plan, classifier,
reducer, and evaluator without acquiring credentials or performing network
access. Real acquisition and promotion remain separate.
