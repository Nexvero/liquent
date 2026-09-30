# LQ-2770 — Authenticated staging Research start

LQ-2770 closes the staging composition gap between the authenticated Control
Plane and the already isolated Research worker without widening Production.

The runtime now has an explicit `staging` environment. It retains the same
JSON logging, wildcard listener, PostgreSQL secret and driver requirements as
Production. A Research data root in a shared environment is accepted only in
this staging mode and only while the complete OIDC contract and database-backed
authorization are active. Preview and Production remain fail-closed.

The reviewed Compose contract mounts the operator-selected Research data
directory read-only into the Control Plane as well as the worker. The mount
alone does not activate Research start: the staging runtime environment must
also explicitly select `staging` and the fixed container data path. The worker
remains the only process with a writable artifact volume.

This makes the existing authenticated, CSRF-protected Research-job start route
available for a controlled staging acceptance. It creates no identities,
memberships, permissions, jobs or datasets and grants no Production deployment
authority. The exact immutable staging image must still prove current
authorization, one synthetic job, permission revocation, artifact integrity and
bounded worker shutdown.
