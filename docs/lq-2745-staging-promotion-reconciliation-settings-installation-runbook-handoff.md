# LQ-2745: Staging promotion reconciliation settings installation runbook handoff

## Decision

LQ-2745 hands the installed LQ-2744 settings command to the existing staging
promotion runbook. Installation remains a separate manual preparation action
before reconciliation and is not part of normal promotion or rollback.

## Observable contract

- The runbook names the exact installed command and four explicit path arguments.
- It fixes the order as provider source, provider target, process source and
  process target.
- It preserves the closed owner, mode, link, directory and exact-binding rules.
- `installed` is the only successful installation result.
- Neutral `present` requires a stop without comparison or replacement.
- `unavailable` requires a stop without automatic retry.
- `invalid_invocation` means only that invocation must be corrected.
- Settings values are excluded from arguments, logs, tickets and evidence.
- Installation requires a separate later reconciliation decision.

## Safety boundary

The runbook communicates an existing bounded configuration transport. It does
not grant promotion authority, prove that an unknown attempt exists or invoke
reconciliation. A retained provider target is inert and is neither deleted nor
treated as permission to repair or replace configuration.

## Deliberate exclusions

LQ-2745 adds no settings value, credential, secret, default path, shell wrapper,
cleanup, rotation, overwrite, service, scheduler, retry, route, migration,
deployment or automatic invocation. Production triggering remains outside this
slice.
