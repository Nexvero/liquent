# LQ-635 — Direct wrapper artifact observation contract

## Status

Accepted as the prerequisite read boundary for observation-only Prepare and
Release parent orchestration.

## Decision

The parent may recognize Ready and Release Consumed only by reading the direct
child-owned control files. It may not call wrapper publication methods, construct
a publication from expected values, or treat engine `running` as either fact.

Each observation reads exactly one fixed role from the bound control directory,
applies the canonical control-artifact codec, and compares artifact ID, handle,
role, and correlation with the persistent gate and Release decision.

Ready binds the gate-owned Ready ID and gated observation ID. Consumed binds the
gate-owned Consumed ID and the already committed Release ID. Neither observation
accepts a caller-supplied success boolean, role, path, or authority.

## Absence and failure

A physically absent role is neutral `None`: the child has not yet supplied the
fact. It causes no journal transition and no artifact record.

A malformed, noncanonical, wrongly bound, duplicate, or technically unreadable
artifact is existing detail-free technical unavailability. A persistent
same-role conflict remains the existing closed runtime conflict.

## Scope

This contract adds no polling policy, parent state transition, Release-token
publication, executor, engine operation, schema, migration, port, or wiring.
LQ-636 implements observation and exact-fact persistence.
