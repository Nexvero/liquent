# LQ-2696 — Staging session operator composition

LQ-2696 provides the provider-neutral composition for a registry-bound staging
Research-index run. It binds one externally owned database engine, HTTP client,
and LQ-2695 handoff source to one callable operator. Execution delegates to the
LQ-2694 boundary, so registry checks still occur immediately around acquisition
and the validated handoff is passed to the existing controlled runtime.

Composition performs no database, HTTP, or source access. It owns and closes no
resource, exposes no lifecycle method, and retains no acquired session set.
Source and resource details remain absent from representations. Sessions remain
identification material only; fixture authority continues to resolve from the
system of record during execution.

This slice adds no credential source, secret persistence, login automation,
provider selection, cache, CLI, scheduled execution, deployment, or promotion.
A secure operational source, invocation boundary, and real staging promotion
remain explicit later work.
