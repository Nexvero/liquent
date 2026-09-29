# LQ-2760: Staging promotion reconciliation acceptance completion audit

## Audit conclusion

LQ-2750 through LQ-2759 close the manual staging-promotion reconciliation
acceptance strand. The installed operator chain is covered from private
settings installation through readiness and candidate inspection to one exact
reconciliation, including failure containment and a real PostgreSQL acceptance.
The strand is ready for an explicit, separately authorized staging exercise;
it does not authorize that exercise, another reconciliation, promotion or
deployment.

## Closed acceptance path

1. LQ-2750 proves a read-only readiness audit over installed private process
   and provider settings.
2. LQ-2751 binds readiness to the manual runbook and records its closed
   presentation and authority boundary.
3. LQ-2752 adds a read-only candidate audit that selects no work and performs
   no provider request.
4. LQ-2753 accepts the complete operator boundary while preserving one-shot,
   fail-closed behavior.
5. LQ-2754 rehearses the exact SQLite-backed operator sequence:
   `installed` -> `ready` -> `pending` -> `reconciled` -> `idle`.
6. LQ-2755 contains provider HTTP and decoder failures without durable state
   change or automatic retry.
7. LQ-2756 contains owner-private settings tamper before provider access.
8. LQ-2757 contains database unavailability before provider access.
9. LQ-2758 contains schema-revision mismatch before provider access.
10. LQ-2759 repeats the complete positive chain against a dedicated real
    PostgreSQL database and confirms the committed result through an
    independent database engine.

## Verified acceptance matrix

The acceptance suite now proves these externally observable outcomes:

- installation reports only `installed` or `present`;
- readiness reports only `ready`, `unavailable` or `invalid_invocation`;
- candidate inspection reports only `pending`, `idle`, `unavailable` or
  `invalid_invocation`;
- reconciliation reports only `reconciled`, `idle`, `unavailable` or
  `invalid_invocation`;
- one bounded successful run issues exactly one provider request;
- provider failure, settings tamper, database failure and schema mismatch do
  not record reconciliation and do not remove the unknown-effect candidate;
- PostgreSQL success is durable outside the command-owned engine and removes
  the exact candidate from the persistent unknown-effect index;
- CLI output exposes no settings path, endpoint, database URL, operation
  identity, response body or internal error chain.

## Installed and documented operator surface

The project exposes exactly one entry point for each manual boundary:

- `liquent-staging-promotion-reconciliation-settings-install`;
- `liquent-staging-promotion-reconciliation-readiness-audit`;
- `liquent-staging-promotion-reconciliation-candidate-audit`;
- `liquent-staging-promotion-reconcile`.

The staging-promotion runbook orders those commands and keeps installation,
readiness, candidate inspection and reconciliation as separate operator
decisions. None of the commands schedules, retries or invokes the next command.

## Remaining external work

A real staging exercise still requires environment-specific owner-private
settings, provider authorization, current durable evidence, an approved
operator decision and an available migrated PostgreSQL database. Promotion
approval, deployment, monitoring, scheduling, automatic retry, bulk draining,
credential provisioning and incident response remain external work.

This audit adds tests and documentation only. It changes no production code,
schema, migration, command, route, trigger, scheduler, service or deployment.
It closes only the manual reconciliation acceptance strand.
