# LQ-2716: Staging promotion reconciliation candidate selection

## Decision

LQ-2716 selects at most one operation identity from the bounded persistent
Unknown index introduced by LQ-2715. Selection is deliberately separate from
the reconciliation operation: it neither claims nor executes the candidate.

The complete index result is validated before its first identity is returned.
This preserves the deterministic ordering and fixed bound of the persistence
contract without trusting an arbitrary adapter result.

## Observable contract

- The Unknown index is read exactly once per selection.
- An empty index returns neutral absence.
- A non-empty valid index returns its first operation identity.
- The index result must be an immutable tuple with at most 100 entries.
- Every identity must be opaque, valid, unique, and ascending.
- Lists, duplicate identities, malformed identities, unsorted results, and
  excessive results fail closed.
- Index failures become detail-free unavailability.
- Selection performs no persistence mutation or provider observation.

## Safety boundary

The selected identity is only an untrusted lookup candidate. It grants no
authority, ownership, exclusivity, retry permission, or evidence of a provider
outcome. A consumer must submit it to the LQ-2714 single-operation boundary,
which reloads and validates the durable Unknown value before observation.

Concurrent selectors may return the same identity. That is safe because this
slice makes no exclusivity claim. A later execution design must decide whether
claiming is required before it composes selection with reconciliation.

## Deliberate exclusions

LQ-2716 adds no claim, lease, fairness rule, cursor, loop, batch reconciler,
scheduler, worker, provider adapter, retry, route, CLI, schema, migration,
credential, secret, or deployment decision. Controlled execution remains a
separate later slice.
