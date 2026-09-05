# LQ-626 — Wrapper launch mount and loader completion audit

## Status

LQ-623 through LQ-626 are complete as the isolated mount-and-load strand.

## Result

The prior aliasing blocker is removed: immutable launch bytes are no longer
reachable through the dynamic read-write mount. Docker create and inspect agree
on the exact two-bind capability profile, while the six-label ID/digest anchor
remains unchanged.

The new loader verifies filesystem facts, a bounded SHA-256, canonical bytes,
document identity, creation, handle, directory, image, and profile before
returning a typed launch document. It has no method that publishes Ready or
executes the requested writer/recovery capability.

The focused strand passes 82 tests. The strict full regression passes 5,231
tests with 108 environment-dependent skips under the DeprecationWarning error
boundary.

## Unchanged boundaries

There is no schema, table, SQL, migration, database port, CLI, settings,
application-factory, Compose, deployment, release, commit, or push change.
Launch publication remains before create; runtime-container identity remains a
separate parent/engine fact.

The next strand can define a child-owned wrapper state machine that loads first,
publishes Ready second, waits for Release, and only then invokes one capability.
