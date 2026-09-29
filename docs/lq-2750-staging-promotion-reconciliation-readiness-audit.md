# LQ-2750: Staging promotion reconciliation readiness audit

## Status

Implemented as a read-only, detail-free operational preflight. The audit does not run reconciliation.
It does not grant promotion or deployment authority.

## Scope

LQ-2750 bundles the next safe integration step after the settings installation
chain from LQ-2740 through LQ-2746:

- load exactly one explicit reconciliation process settings file;
- validate the provider settings file referenced by that process file;
- create one process-owned database engine from the validated database URL;
- execute the existing database readiness probe exactly once;
- dispose the engine on every path;
- return only the fixed result `ready` or a detail-free failure.

The installed command is:

```text
liquent-staging-promotion-reconciliation-readiness-audit /absolute/process.env
```

Successful readiness writes `ready` to stdout and exits with code 0. Invalid
invocation writes `invalid_invocation` to stderr and exits with code 2. Every
technical or readiness failure writes `unavailable` to stderr and exits with
code 1.

## Closed boundaries

The audit performs no provider HTTP request, no reconciliation, no promotion,
no database mutation, no migration, no bootstrap and no retry. It does not
print paths, endpoints, database URLs, metadata or exception details. A ready
result is only prerequisite evidence and is never an authorization signal.

Real settings provisioning, the later explicit reconciliation decision,
provider mutation, staging acceptance and deployment remain separate external
operations.
