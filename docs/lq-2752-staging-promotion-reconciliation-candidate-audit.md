# LQ-2752: Staging promotion reconciliation candidate audit

## Status

Implemented as a read-only, detail-free durable-state preflight with its
runbook handoff. The audit does not run reconciliation. It does not expose the operation identity.
It does not grant reconciliation, promotion or deployment authority.

## Scope

LQ-2752 bundles the next safe operator step after the LQ-2750 readiness audit
and LQ-2751 runbook handoff:

- load exactly one explicit reconciliation process settings file;
- validate the referenced provider settings without using the provider;
- create one process-owned database engine;
- execute the existing database readiness probe exactly once;
- read the existing bounded unknown-effect index exactly once;
- apply the existing deterministic candidate selector;
- dispose the engine on every path;
- return only whether an eligible candidate existed at audit time.

The installed command is:

```text
liquent-staging-promotion-reconciliation-candidate-audit /absolute/process.env
```

An eligible candidate writes `pending` to stdout and exits with code 0. An
empty eligible index writes `idle` to stdout and exits with code 0. Invalid
invocation writes `invalid_invocation` to stderr and exits with code 2. Every
technical, structural or readiness failure writes `unavailable` to stderr and
exits with code 1.

## Closed boundaries

The audit performs no provider HTTP request, no unknown-operation detail read,
no reconciliation and no database mutation. It does not claim, lease, lock,
retry, promote or deploy anything. It prints no operation identity, path,
endpoint, database URL, metadata or exception detail.

Both `pending` and `idle` can become stale immediately. They are only
point-in-time prerequisite evidence and never an authorization signal. The
operator must make a separate explicit decision before the existing bounded
reconciliation command may run.

The staging runbook now places this candidate audit after a fresh readiness
result and before the manual reconciliation action. Real settings provisioning,
the decision to reconcile, provider observation, durable mutation, staging
acceptance and deployment remain separate external operations.
