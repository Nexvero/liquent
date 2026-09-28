# LQ-2698 — Ephemeral staging runtime composition

LQ-2698 closes the provider-neutral composition chain from an externally owned
resolver to the controlled staging Research-index operator. The resolver is
wrapped by the LQ-2697 non-caching source, adapted by LQ-2695, and executed only
through the LQ-2694 registry-bound operator. Existing LQ-2696 resource ownership
and execution boundaries remain unchanged.

Construction performs no resolver, database, or HTTP access. Session material
can be requested only after an explicit execution call and is resolved afresh
for that call. The composition stores the resolver capability but no resolved
handoff, session set, credential, or authority fact. Representations remain
free of operational material.

This slice adds no secret store, provider adapter, login or refresh automation,
retry, cache, CLI, scheduling, deployment, or promotion. Supplying the secure
resolver and invoking a real staging run remain separate operational work.
