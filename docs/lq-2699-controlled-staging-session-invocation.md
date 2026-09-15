# LQ-2699 — Controlled staging session invocation

LQ-2699 provides one callable invocation boundary over the complete LQ-2698
composition. Each explicit call validates one exact LQ-2694 request, constructs
one ephemeral operator, and invokes that operator at most once. The boundary
does not retry, schedule, loop, or reuse a prior composition or session result.

An invalid request is rejected before composition and therefore before any
resolver, database, or HTTP access. Neutral session-set absence remains neutral
and starts no acceptance runtime. Composition, resolution, acquisition, and
execution failures collapse to one detail-free technical-unavailability signal.

This slice adds no CLI, HTTP route, worker, scheduler, retry, idempotency claim,
provider adapter, login automation, secret persistence, deployment, or
promotion. Choosing an externally exposed invocation mechanism and performing
a real controlled staging run remain separate operational work.
