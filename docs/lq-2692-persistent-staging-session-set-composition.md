# LQ-2692 — Persistent staging session-set composition

LQ-2692 composes the LQ-2691 persistent session-set registry around exactly one
externally owned database engine. Construction creates only the read-only
resolver object and performs no database access, mutation, session acquisition,
network request, or execution.

The composition exposes the resolver and nothing that can create, update,
delete, rotate, acquire, or execute a session set. It owns and closes no engine.
Its representation contains no engine details, registry identifiers, revisions,
sessions, credentials, or secrets.

This slice adds no schema, migration, authority decision, cache, login flow,
provider integration, credential source, CLI, deployment, or promotion.
Concrete secret resolution, controlled acquisition integration, and promotion
remain separate.
