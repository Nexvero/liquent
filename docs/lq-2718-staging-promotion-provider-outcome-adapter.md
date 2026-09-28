# LQ-2718: Staging promotion provider outcome adapter

## Decision

LQ-2718 adds a narrow read-only adapter between a trusted provider-status
gateway and the reconciliation observation contract. The gateway is queried
only with the operation identity reconstructed from the durable Unknown value.

The adapter accepts a committed status only when every identity and promotion
binding matches the Unknown attempt exactly. It then constructs the receipt
used by the existing reconciliation boundary.

## Observable contract

- The adapter accepts one exact durable Unknown value.
- The gateway is called once with its persisted operation identity.
- Provider absence returns neutral absence.
- A committed status binds operation, actor, evidence, candidate, staging
  origin, target environment, and aware observation time.
- An exact status returns one trusted committed observation.
- Substitution, malformed status, invalid time, and gateway failure fail
  closed with detail-free unavailability.
- No caller-supplied receipt or success flag enters the adapter.

## Safety boundary

Provider observation is not promotion authority and does not authorize replay.
The adapter exposes no mutation, retry, claim, or credential surface. Its
result remains subject to the independent exact-binding checks and durable
recorder in LQ-2712.

The gateway protocol is trusted but transport-neutral. Concrete HTTP routes,
authentication, response classification, and timeout policy remain outside
this slice.

## Deliberate exclusions

LQ-2718 adds no provider mutation, network client, retry, polling loop,
scheduler, worker, route, CLI, schema, migration, credential, secret, or
deployment decision. Concrete provider transport remains a separate slice.
