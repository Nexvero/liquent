# LQ-2676 – Staging Research-index staged acquisition

## Result

LQ-2676 coordinates the closed request plan in three read-only stages:
baseline, after-revocation, and unavailability.

The baseline ends with the before-revocation observation. The after-revocation
stage contains only its matching follow-up. The unavailability fixture remains
independent. No stage performs or authorizes a mutation.

## Session boundary

Each stage requires the exact opaque session slots it needs and rejects missing,
additional, or untyped session values before acquisition. Anonymous requests
receive no session.

The caller retains session ownership. The coordinator does not persist, return,
log, or place session material in classifications.

## Immediate classification

Each bounded response is classified immediately and only its closed check,
phase, and outcome is retained. Acquisition or classification faults become
detail-free technical unavailability without provider or transport text.

Stages return classifications only. They neither combine evidence across an
unobserved mutation nor imply that revocation occurred.

## Verification

Tests prove exact stage sizes, phase separation, anonymous credential absence,
exact stage-session sets, immediate classification, and detail-free transport
failure.

## Explicit non-goals

This slice adds no revocation or restoration mutation, credential loader or
store, cross-stage state, evidence file, CLI, workflow, deployment, promotion,
rollback, schema, migration, route, image, secret, or installed operator.

## Next step

A later handoff contract may bind classifications from the three independently
authorized stages to one acceptance run without granting mutation authority.
Real credential provisioning, revocation, staging execution, evidence writing,
and promotion remain separate.
