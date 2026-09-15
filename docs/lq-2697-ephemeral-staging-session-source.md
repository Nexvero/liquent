# LQ-2697 — Ephemeral staging session source

LQ-2697 adapts an externally owned resolver into the LQ-2695 handoff-source
contract. Every lookup invokes that resolver afresh with the exact opaque
session-set identity and expected revision. The adapter neither caches nor
retains a returned handoff, allowing later source-side rotation, revocation, or
absence to affect every later acquisition.

The resolver may return one already validated complete LQ-2688 handoff or
neutral absence. Any other result is rejected. Resolver failures propagate to
the existing detail-free LQ-2693 and LQ-2694 boundaries. Resolver identity,
session values, set identity, and revision remain absent from representations.

This adapter owns no resource and performs no work during construction. It
adds no secret store, credential persistence, login automation, provider
selection, refresh policy, retry, cache, CLI, scheduling, deployment, or
promotion. Supplying and operating the external resolver remains a separate
integration responsibility.
