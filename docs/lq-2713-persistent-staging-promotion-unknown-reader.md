# LQ-2713: Persistent staging promotion unknown reader

## Decision

LQ-2713 adds a read-only database adapter that reconstructs a durable unknown
promotion attempt by opaque operation identity. It is the persistence source a
later reconciliation trigger can use before invoking the trusted observation
boundary from LQ-2712.

The adapter resolves an unknown value only when the immutable attempt row and
the complete event history are structurally exact. It does not grant authority,
contact a provider, or mutate state.

## Observable contract

- The caller supplies only an opaque operation identity.
- Missing operations resolve to neutral absence.
- Prepared-only and write-started-only operations are not unknown and resolve
  to neutral absence.
- Directly committed and reconciled committed operations resolve to neutral
  absence.
- Only `prepared`, `write_started`, `effect_unknown` with contiguous sequence
  numbers reconstructs an unknown domain value.
- Actor, evidence, candidate, staging origin, and target are reconstructed from
  the persistent system of record, never from caller assertions.
- Receipt presence must match committed state exactly.
- Gaps, reordered events, unsupported histories, malformed facts, and technical
  database failures fail closed with detail-free unavailability.
- The reader exposes no write, retry, or promotion operation.

## Safety boundary

Resolving an unknown attempt is not authorization to retry or proof of a
provider outcome. It supplies the exact durable binding to the separate trusted
observer. If a later observation is absent or unavailable, the journal remains
unknown.

Session reconstruction preserves only the previously persisted actor identity.
It does not recreate authentication freshness or promotion authority and must
not be used as a session for another action.

## Deliberate exclusions

LQ-2713 adds no enumeration, queue claim, scheduler, worker, provider call,
automatic retry, route, CLI, schema, migration, credential, secret, or
deployment decision. Operational selection and concrete provider observation
remain explicit later slices.
