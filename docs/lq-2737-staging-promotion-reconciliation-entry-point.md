# LQ-2737: Staging promotion reconciliation entry point

## Decision

LQ-2737 installs the closed LQ-2736 command as
`liquent-staging-promotion-reconcile`. The entry point targets the existing CLI
`main` function and adds no second presentation or execution path.

## Observable contract

- The installed command has exactly one declared target.
- Invocation semantics remain the LQ-2736 contract unchanged.
- The command accepts exactly one explicit process-settings path.
- Successful outcomes remain `idle` or `reconciled` with exit zero.
- Technical unavailability remains `unavailable` with exit one.
- Invalid invocation remains `invalid_invocation` with exit two.
- The package inventory contains 73 console entry points.
- The transport target does not add an operator implementation module.

## Safety boundary

Installation makes an existing bounded operation addressable. It grants no
promotion authority, chooses no settings path, and does not trigger execution.
The release inventory and exact wheel entry-point identity are updated together
so packaging drift continues to fail closed.

## Deliberate exclusions

LQ-2737 adds no shell wrapper, default arguments, environment lookup, service
unit, scheduler, timer, worker, retry, route, deployment, migration, bootstrap,
or production invocation. Operational triggering remains a separate slice.
