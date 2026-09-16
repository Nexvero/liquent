# LQ-2706 — Staging promotion attempt state

LQ-2706 defines the crash-safe persistence contract behind the LQ-2705 atomic
gateway. Preparation binds one opaque operation identity to the authenticated
command and system-of-record authority. The store must resolve current evidence,
candidate, authority, and target atomically while preparing that binding.

Before any external mutation, the store records `write started` while all facts
remain current. Once that state is committed, failure or loss of acknowledgement
is an unknown effect, never permission to retry. A committed receipt may be
recorded only for the exact write-started attempt. No state transition accepts a
caller-supplied allow flag, role, candidate, origin, target, or authority.

This slice defines immutable states and the persistence port only. It performs no
database write, provider call, promotion, deployment, or publication and adds no
schema, migration, CLI, route, worker, scheduler, retry, credential, or secret
decision. Database persistence, reconciliation of unknown effects, and a real
provider adapter remain separate later work.
