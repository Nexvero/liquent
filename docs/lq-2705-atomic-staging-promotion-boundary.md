# LQ-2705 — Atomic staging promotion boundary

LQ-2705 defines the only safe boundary for a future staging Research-index
promotion. A command contains exactly an authenticated actor and a persisted
evidence digest. It contains no allow boolean, role, candidate assertion,
staging origin, target environment, authority assertion, or credential.

The gateway contract requires one atomic operation to reload persisted evidence,
resolve the currently active candidate, resolve current actor authority and its
system-of-record target, revalidate every binding, perform at most one mutation,
and persist the resulting receipt. Neutral absence or revocation must produce no
effect. Technical failure must not be converted into permission.

No reusable preauthorization token exists between validation and mutation.
The receipt describes an observed committed effect and grants no future
authority. This slice provides only command, receipt, and gateway contracts; it
implements no persistence, provider, deployment, publication, or promotion.
It adds no schema, migration, CLI, route, worker, scheduler, retry, credential,
or secret decision. Atomic persistence and a real promotion adapter remain
separate later work.
