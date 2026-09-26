# LQ-2704 — Current staging promotion authority

LQ-2704 introduces a separate current-authority result for an authenticated
actor and one LQ-2703 evidence binding. Authentication identifies the actor but
grants no authority. Evidence establishes candidate fitness but grants no
authority. Only a trusted authority resolver may return the current capability.

The resolver binds actor, candidate digest, staging origin, and target
environment from its system of record. The caller cannot supply an allow
boolean, role, target environment, or authority assertion. Missing, inactive,
or revoked authority resolves as neutral absence, while malformed bindings and
technical resolver failures collapse to one detail-free unavailability signal.

Authority is resolved afresh for every later decision, so revocation affects
subsequent calls. The result carries no promote method and this slice performs
no promotion, deployment, publication, persistence mutation, or environment
change. It adds no schema, migration, CLI, route, worker, scheduler, retry,
credential, or secret decision. Atomic final revalidation and real promotion
remain separate later work.
