# LQ-2707 — Persistent staging promotion attempt schema

LQ-2707 adds the durable database foundation for the LQ-2706 crash-safe attempt
contract. An immutable attempt row binds operation, actor, evidence digest,
candidate digest, staging origin, system-of-record target, and creation time.
An append-only event journal records prepared, write-started, effect-unknown, or
committed observations using a per-operation sequence.

Only a committed event may carry a provider receipt identity; every other state
must omit it. Primary, foreign-key, state, sequence, digest-length, and receipt
shape constraints fail closed. The migration creates no seed data and stores no
session, credential, role, allow flag, authority object, or provider secret.

This slice supplies schema only. It performs no attempt transition, provider
call, promotion, deployment, publication, retry, or reconciliation and adds no
CLI, route, worker, scheduler, credential, or secret decision. The transactional
store and unknown-effect reconciliation remain separate later work.
