# LQ-2715: Persistent staging promotion unknown index

## Decision

LQ-2715 adds bounded, read-only discovery of durable staging-promotion
operations whose latest recorded event is `effect_unknown`. The index returns
only opaque operation identities. Each identity remains an untrusted candidate
that LQ-2714 must reload and validate before any provider observation.

The index uses the existing attempt journal and introduces no new persistence
facts. It provides operational discovery without turning discovery into a
claim, lease, retry permission, or proof of outcome.

## Observable contract

- One call returns an immutable tuple of opaque operation identities.
- Results are ordered deterministically by operation identity.
- The result is bounded to at most 100 candidates.
- Prepared, write-started, directly committed, and reconciled operations are
  absent.
- An operation is only a candidate when its latest durable event is
  `effect_unknown`.
- A reconciliation commit affects the next index read.
- Missing candidates return an empty tuple.
- Duplicate, malformed, or excessive adapter results fail closed.
- Technical database failures become detail-free unavailability.

## Safety boundary

An indexed identity grants no authority and proves neither a valid history nor
an unresolved provider effect. Consumers must pass each identity through the
single-operation boundary from LQ-2714, which reloads the complete durable
value and applies exact-history validation before observation.

The fixed bound prevents an unbounded operational read. Ordering is for stable
selection only; it does not establish priority, ownership, fairness, or a
lease. Concurrent readers may observe the same candidate.

## Deliberate exclusions

LQ-2715 adds no claim, lease, cursor, pagination token, scheduler, worker,
batch reconciler, provider call, automatic retry, route, CLI, schema,
migration, credential, secret, or deployment decision. Claiming and controlled
execution remain separate later slices.
