# LQ-2711: Persistent staging promotion reconciliation commit

## Decision

LQ-2711 adds the distinct persistence transition that can close an
`effect_unknown` attempt after a trusted external observation proves the
promotion was committed. This transition is deliberately separate from the
ordinary provider-success path introduced by LQ-2710.

The journal does not perform the external observation. It records only an
already established, exactly bound conclusion and preserves the uncertainty
event in the immutable history.

## Observable contract

- `record_reconciled_committed` accepts only a typed unknown-effect value and a
  typed receipt.
- The receipt must match operation, actor, evidence, candidate, staging origin,
  and target of the nested prepared attempt exactly.
- The persisted event prefix must be `prepared`, `write_started`, then
  `effect_unknown`.
- A reconciled committed event is appended transactionally as sequence four;
  the prior uncertainty is never overwritten.
- The receipt identity is stored only on the committed event.
- An exact repetition is idempotent and adds no duplicate event.
- Missing state, substituted receipt, different operation, malformed order, or
  later state fails closed.
- The transition grants no authority and exposes no retry capability.
- Technical persistence failures remain detail-free.

## Safety boundary

This method is not evidence that reconciliation occurred. Its caller must be a
later trusted composition that obtains a conclusive provider observation and
binds it to the persisted operation. Absence, timeout, ambiguity, or a
provider-side technical failure must leave the attempt unknown.

The normal `record_committed` path continues to reject an unknown-effect
history. Only this explicit reconciliation transition may append a conclusion
after uncertainty, making the distinction observable in the event sequence.

## Deliberate exclusions

LQ-2711 adds no provider reader, network call, automatic retry, negative
provider conclusion, scheduler, worker, route, CLI, schema, migration,
credential, secret, or deployment decision. Trusted reconciliation observation
and its orchestration remain separate later slices.
