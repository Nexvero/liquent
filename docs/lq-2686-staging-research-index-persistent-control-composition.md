# LQ-2686 — Persistent staging Research-index control composition

## Outcome

This slice provides one side-effect-free production composition for the
persistent fixture-control capability used by LQ-2685.

The composition wires one externally owned database engine into the LQ-2684
read-only fixture resolver and the existing authorized complete-membership
change store. Both are supplied to the LQ-2683 controller. A single secure
authority-material generator supplies fresh membership revision and change
identities through a narrow private adapter.

## Boundary

Construction performs no database query, migration, mutation, network call,
credential read, stage acquisition, fixture revocation, restoration, evidence
write, or process startup. The returned value exposes the controller and its
two persistent adapters for explicit higher-level composition, while its
identity source remains repr-private.

The controller still resolves actor, target, workspace, original snapshot, and
current management capability from persistent system-of-record facts on every
operation. Neither composition nor generated IDs grant authority.

## Exclusions

LQ-2686 adds no schema, migration, fixture provisioning, user, workspace,
membership, role, capability, session, secret source, HTTP client, CLI,
scheduler, deployment, or promotion. Binding concrete staging sessions and
request acquisition to the controlled execution remains separate.
