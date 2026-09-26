# LQ-2689 — Staging Research-index controlled operator

## Outcome

This slice adds one callable operator boundary for an explicitly prepared
staging Research-index acceptance run. It composes the LQ-2687 runtime and
passes one exact LQ-2688 session handoff into that runtime.

The operator request binds the validated acceptance run, evidence destination,
opaque fixture handle, expected active revision, and validated session handoff
before composition. Values with a different concrete type are rejected. The
request representation exposes none of this operational material.

## Execution boundary

The caller supplies one externally owned database engine and one externally
owned bounded HTTP client. The operator neither creates nor closes either
resource. It composes the runtime once and performs exactly one execution with
the request's bound values.

The operator accepts no caller-provided authority assertion, role, permission,
membership, workspace, user, or allow boolean. The fixture controller still
resolves actor, target workspace, lifecycle state, and management capability
from the persistent system of record for each mutation decision. The session
handoff continues to identify browser sessions without granting authority.

Operational failures are reduced to one detail-free unavailable signal. A
completed acceptance result retains its existing accepted, rejected, or
unavailable outcome and is not reinterpreted by the operator.

## Deliberately no CLI

This slice adds no command-line parser. Serializing browser sessions into
arguments, environment variables, or general request files would create a new
credential transport decision. Session acquisition and secure injection remain
the responsibility of a later, separately reviewed integration.

## Exclusions

LQ-2689 creates, loads, refreshes, persists, or logs no credentials or sessions.
It adds no schema, migration, fixture provisioning, retry, scheduler, process
launcher, deployment, promotion, or public endpoint. Controlled credential
acquisition and real promotion remain separate.
