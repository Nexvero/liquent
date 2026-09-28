# LQ-2738: Staging promotion reconciliation runbook handoff

## Decision

LQ-2738 adds an operator-facing handoff for the installed LQ-2737 command to
the existing staging-promotion runbook. Reconciliation remains a separate
manual recovery action and is not part of normal application promotion or
rollback.

## Observable contract

- The runbook names the exact installed command and one explicit path argument.
- It specifies both closed owner-private settings files and their exact keys.
- It preserves the LQ-2736 output and exit-code interpretation.
- `idle` and `reconciled` are the only successful results.
- `unavailable` requires a stop without automatic retry.
- `invalid_invocation` means only that invocation must be corrected.
- Settings values and durable identities are excluded from arguments and logs.
- Every later invocation requires a new explicit operator decision.

## Safety boundary

The runbook communicates an existing bounded recovery operation. It does not
grant promotion authority, infer that an unknown attempt exists, or treat a
successful command exit as application-deployment approval. Durable state and
provider response still cross all existing closed validation boundaries.

## Deliberate exclusions

LQ-2738 adds no settings file, credential, secret, default path, shell wrapper,
service unit, scheduler, timer, worker, watcher, retry, route, deployment,
migration, bootstrap, or automatic invocation. Production triggering remains
outside this slice.
