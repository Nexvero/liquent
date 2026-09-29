# LQ-2751: Staging promotion reconciliation readiness runbook and completion audit

## Decision

LQ-2751 hands the installed LQ-2750 readiness-audit command to the existing
staging-promotion runbook and closes the read-only readiness strand in one
documentation-only package. The audit remains a manual prerequisite check
between settings installation and a separate reconciliation decision.

The handed-off command is:

```text
liquent-staging-promotion-reconciliation-readiness-audit /ABSOLUTE/PROCESS_SETTINGS
```

## Runbook contract

- The runbook names the exact installed command and one explicit absolute
  process-settings path.
- `ready` on stdout with exit 0 is the only successful audit result.
- `unavailable` on stderr with exit 1 requires a stop without automatic retry
  or reconciliation.
- `invalid_invocation` on stderr with exit 2 means only that the path argument
  must be corrected.
- Paths, settings values, endpoint, database URL and failure details remain
  excluded from logs, tickets and copied evidence.
- Readiness can become stale immediately and requires a later review of current
  durable state plus a new explicit operator decision.

## Closed path

The completed read-only path has these ordered boundaries:

1. LQ-2731 and LQ-2732 define and load the closed process settings projection.
2. LQ-2724 and LQ-2725 define and load the closed provider settings projection.
3. LQ-2734 provides the existing exact database-readiness gate.
4. LQ-2750 composes one read-only audit, owns and disposes its database engine,
   reduces all presentation to fixed outcomes and installs one console command.
5. LQ-2751 places that command after settings installation and before any
   independent reconciliation decision in the manual runbook.

## Verified safety boundary

The audit performs no provider request, reconciliation, database mutation,
migration, bootstrap or retry. `ready` proves only that the closed settings and
database prerequisites passed at audit time. It neither proves that an unknown
attempt exists nor grants reconciliation, promotion or deployment authority.

The runbook does not add a settings value, credential, default path, discovery,
shell wrapper, scheduler, service, worker, watcher, automatic trigger, retry,
route, migration or deployment. Real staging provisioning, durable-state
review, the later operator decision, reconciliation execution and acceptance
remain separate external work.

## Completion conclusion

The readiness strand is implementation- and runbook-complete for one explicit
operator audit. This package changes no schema, runtime behavior, provider,
secret or external system. It closes only the manual read-only preflight and
does not close or automate the separately authorized reconciliation procedure.
