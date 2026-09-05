# LQ-631 — Single supervisor execution owner contract

## Status

Accepted as the ownership decision for the corrected Docker supervisor graph.

## Decision

The bound wrapper child is the sole future owner of Writer or Recovery capability
execution. It alone publishes Ready, consumes Release, invokes the capability,
and publishes Terminal.

The parent owns durable registration, launch, runtime binding, release decision,
Release-token publication, observation, terminal correlation, termination, and
retention. It must not publish Ready or Consumed and must not invoke a Writer or
Recovery executor in the corrected graph.

The existing parent-side LQ-476 execution remains a compatibility implementation
but is excluded from the future Docker composition. This slice does not silently
change or activate that path. No graph may contain both execution owners.

## Restart rule

Child exit, engine terminality, Release commitment, or missing Terminal does not
authorize another execution. Once consumption is possible or observed, automatic
restart is prohibited. Only read-only reconciliation may classify current facts.

An ambiguous consumed execution remains blocked until a separately designed
recovery decision can prove an outcome without repeating capability effects.
Neither settings nor operator convenience can convert ambiguity into permission.

## Authority

Execution ownership is architecture, not actor authority. Session, membership,
role, research permission, caller booleans, environment values, and container
state cannot grant execution or restart.

## Scope

No parent refactor, wiring, schema, migration, process entrypoint, Compose, or
deployment changes here. LQ-632 implements the observation-only classifier.
