# LQ-2744: Staging promotion reconciliation settings installation entry point

## Decision

LQ-2744 installs the closed LQ-2743 command as
`liquent-staging-promotion-reconciliation-settings-install`. The entry point
targets the existing CLI `main` function and adds no second presentation or
installation path.

## Observable contract

- The installed command has exactly one declared target.
- Invocation semantics remain the LQ-2742 and LQ-2743 contract unchanged.
- The command accepts exactly four explicit absolute paths.
- `installed` remains stdout with exit zero.
- Neutral `present` remains stderr with exit three.
- Technical unavailability remains `unavailable` with exit one.
- Invalid invocation remains `invalid_invocation` with exit two.
- The package inventory contains 74 console entry points.
- The transport target adds no operator implementation module.

## Safety boundary

Installation makes an existing bounded operation addressable. It grants no
promotion authority, chooses no source or target path, and does not invoke the
command. The release inventory and exact wheel identities are updated together
so packaging drift continues to fail closed.

## Deliberate exclusions

LQ-2744 adds no shell wrapper, default arguments, environment lookup, prompt,
service unit, scheduler, timer, worker, retry, route, deployment, cleanup,
rotation, reconciliation trigger or production invocation. Operational
triggering and runbook handoff remain separate slices.
