# LQ-2701 — Staging promotion evidence binding

LQ-2701 binds an LQ-2700 eligibility observation to the complete canonical
staging Research-index evidence that produced it. The evidence is decoded and
re-evaluated; it must be canonical, accepted, and bound to the exact same
candidate digest, staging origin, and observation time. A stable SHA-256 digest
identifies those exact evidence bytes.

The resulting binding is evidence, not authority. It exposes no promotion or
deployment capability and does not establish current candidate, environment,
or operator state. Any later promotion decision must read the bound canonical
evidence and independently resolve current authority and lifecycle facts from
trusted systems of record.

This slice writes no file or database record and performs no publication,
deployment, environment mutation, or promotion. It adds no schema, migration,
CLI, route, worker, scheduler, credential, or secret decision. Durable storage,
current-authority resolution, and real promotion remain separate work.
