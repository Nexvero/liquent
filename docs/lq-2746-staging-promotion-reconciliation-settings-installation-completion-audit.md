# LQ-2746: Staging promotion reconciliation settings installation completion audit

## Audit conclusion

LQ-2740 through LQ-2745 form one complete bounded path for manually installing
the two settings files required by staging promotion reconciliation. The path is
implementation-complete for one explicit operator invocation. It neither runs
reconciliation nor grants promotion or deployment authority.

## Closed path

The completed path has these ordered boundaries:

1. LQ-2740 fixes the four-path, private-source, no-replace and ordered
   publication contract.
2. LQ-2741 validates both exact settings projections and durably publishes the
   provider target before the process activation record.
3. LQ-2742 fixes the four-argument presentation, streams, tokens and exit codes.
4. LQ-2743 implements one detail-free CLI delegation without discovery.
5. LQ-2744 installs exactly one console entry point and synchronizes the release
   inventory and wheel identities.
6. LQ-2745 hands the command to an explicit manual runbook procedure.

## Verified invariants

- All four paths are explicit, absolute, distinct and free of parent traversal.
- Both sources are owner-private regular files with mode `0600` and one link.
- Existing targets are never overwritten, truncated, removed or compared.
- The process source names the exact canonical provider target.
- Both sources validate before target publication begins.
- Provider publication precedes process publication; process is the activation
  record.
- A retained provider without a process target is inert and is not success.
- `installed`, `present`, `unavailable` and `invalid_invocation` are the only
  observable tokens and expose no path, value, endpoint, DSN or error detail.
- The installed command performs exactly one attempt and contains no retry.
- Installation does not open the provider, database or reconciliation runtime.

## Operational readiness

The installed
`liquent-staging-promotion-reconciliation-settings-install` command and the
staging-promotion runbook are sufficient for a trained operator to transport
one separately prepared settings pair into two existing private target
directories. A successful installation is configuration readiness only and is
not permission to invoke reconciliation.

## Remaining external work

Real staging use still requires environment-specific source values and target
locations, infrastructure credentials outside Git where required, an approved
operator decision and subsequent verification of current durable state. Any
cleanup, replacement, rotation, secret-manager integration, automatic retry,
service, deployment wiring or reconciliation trigger is a new reviewed change.

This audit changes no schema, migration, runtime behavior, route, provider,
secret, deployment or external system. It closes only the manual reconciliation
settings-installation implementation strand.
