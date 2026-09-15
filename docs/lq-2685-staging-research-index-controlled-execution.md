# LQ-2685 — Controlled staging Research-index execution

## Outcome

This slice composes the existing staging acquisition, fixture-control, and
evidence boundaries into one explicit execution. It does not add another
authority decision or a second mutation implementation.

## Closed sequence

The execution requires one acceptance run, one opaque fixture handle, its
expected active revision, the exact per-stage session inventory, and injected
revocation, restoration, acquisition, and evidence capabilities.

It acquires the baseline first, revokes the bound fixture, acquires the
after-revocation observations, and then restores the exact committed fixture
chain in a mandatory cleanup step. The unavailability stage runs only after a
valid restoration. Evidence is evaluated and created only after all three
handoffs exist and restoration has succeeded.

If revocation succeeds, every exit from the revocation observation attempts
restoration. A missing, rejected, malformed, or technically failed restore
prevents later acquisition and evidence creation. All orchestration failures
collapse to one detail-free execution-unavailable result.

The fixture handle and expected revision do not grant authority. The injected
LQ-2683 controller and LQ-2684 resolver remain responsible for current
system-of-record binding and authority. Session material is accepted only in
the exact inventory required by each closed acquisition stage and is never
written to evidence.

## Exclusions

LQ-2685 creates no fixture, user, workspace, membership, role, capability,
credential, session, schema, migration, CLI, retry, scheduler, deployment, or
promotion. It does not choose staging URLs or read secrets. Operational
composition with concrete credential acquisition and a controlled operator
remain separate slices.
