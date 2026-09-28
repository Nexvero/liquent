# LQ-2681 — Staging Research-index evidence composition

## Outcome

This slice composes the existing closed staging Research-index acquisition,
run-bound handoff, evaluation, and owner-private evidence publication boundaries.

## Stage composition

One function accepts an already validated run, one explicit closed stage, its
single-request acquisition adapter, and the exact opaque sessions required for
that stage. It delegates acquisition and immediate classification to LQ-2676,
then immediately constructs the LQ-2677 handoff bound to that run and stage.

Stages remain separate calls. The composition does not infer stage order, retain
sessions across calls, trigger revocation, restore a fixture, or hold mutable
cross-stage state.

## Publication composition

A second function accepts one explicit evidence path and an exact tuple of
handoffs. It performs complete same-run evaluation before any filesystem
operation, then delegates canonical encoding and owner-private no-replace
publication to LQ-2678 and LQ-2679. It returns only the existing detail-free
acceptance result.

Incomplete, duplicated, wrongly phased, or cross-run sets fail before a target
can be created. Existing evidence is never replaced. Successful publication can
be independently read and fully revalidated through LQ-2680.

## Exclusions

This composition creates no sessions or credentials, performs no admission or
authority decision, and provides no revocation, restore, retry, scheduling,
workflow, deployment, or promotion operation. An accepted result and its stored
evidence remain observations rather than mutation authority.

## Next slice

A later slice may define the explicit fixture-revocation and restoration
boundary needed between the independently invoked stages. Promotion remains
separate.

## Regression correction

Full-suite verification exposed a persistent-wiring test fixture whose fixed
session expired on its encoded calendar day. Its deterministic fixture instant
is moved beyond the project test horizon; production session semantics are
unchanged.
