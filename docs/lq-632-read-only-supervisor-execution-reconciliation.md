# LQ-632 — Read-only supervisor execution reconciliation

## Status

Implemented as a pure closed classifier over existing journal, runtime, gate,
engine, Release-token, Consumed, and Terminal facts.

## Classifications

The classifier returns one of six states:

- waiting for direct child consumption;
- child capability in flight;
- ambiguous after consumption;
- waiting for direct engine terminality;
- terminal evidence ready for parent correlation;
- blocked divergence.

Every result fixes `may_start_child`, `may_publish_release`, and
`may_execute_capability` to false. These fields cannot be constructed as true.

## Binding checks

Journal, runtime, gate, and observation must agree on handle, directory, runtime
container, creation, image, and profile. Release-token and Consumed must bind the
same persisted Release ID. Consumed and Terminal must use their gate-owned IDs,
roles, handles, and correlations.

Terminal evidence is ready only when Consumed and Terminal both exist and the
same engine observation is `exited` or `dead`. Consumed plus terminal engine
without Terminal is explicitly ambiguous, never retryable.

Malformed dependency shapes are existing detail-free technical unavailability;
well-formed divergent facts produce the closed blocked classification.

LQ-633 provides executable crash-window evidence.
