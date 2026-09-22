# LQ-2739: Staging promotion reconciliation completion audit

## Audit conclusion

LQ-2712 through LQ-2738 form one complete, bounded manual reconciliation
path for durable staging research-index promotion attempts whose provider effect
is unknown. The path is implementation-complete for explicit one-shot operator
use. It is not an automatic recovery service and grants no deployment or
promotion authority.

## Closed path

The completed path has these ordered boundaries:

1. LQ-2712 accepts only a trusted observation for an exact durable attempt.
2. LQ-2713 reloads the unknown attempt from the system of record.
3. LQ-2714 reconciles one exact operation and records only proven outcomes.
4. LQ-2715 and LQ-2716 discover and select at most one bounded candidate.
5. LQ-2717 executes one controlled reconciliation pass.
6. LQ-2718 through LQ-2723 acquire, decode, classify and adapt one provider
   observation through the closed HTTPS boundary.
7. LQ-2724 through LQ-2727 source endpoint settings and own provider-client
   lifecycle without adding credentials or authority.
8. LQ-2728 through LQ-2730 compose the database-backed one-shot runtime.
9. LQ-2731 through LQ-2734 source private process settings, own the database
   engine and stop before provider access unless schema readiness is exact.
10. LQ-2735 and LQ-2736 reduce all external presentation to fixed outcomes,
    output streams and exit statuses.
11. LQ-2737 installs exactly one console entry point.
12. LQ-2738 hands that command to an explicit manual runbook procedure.

## Verified invariants

- Caller input never supplies an allow boolean, role or promotion decision.
- Durable unknown state and the target operation come from persistent records.
- Provider routing settings grant no authority and embed no credential.
- Provider content crosses request, decode, classification and outcome checks.
- Database readiness must match the expected migration head before observation.
- A pass reconciles at most one candidate and contains no internal retry loop.
- Neutral absence remains `idle`; exact completion remains `reconciled`.
- Invocation and technical failures remain fixed and detail-free.
- Receipts, operation identities, paths, DSNs and provider details are not
  emitted by the CLI.
- Resource ownership closes provider clients and database engines on every
  success, absence and failure path.
- Revoked or changed durable facts are reread by each later explicit process.

## Operational readiness

The installed `liquent-staging-promotion-reconcile` command and the existing
staging-promotion runbook are sufficient for a trained operator to perform one
explicit reconciliation decision with separately provisioned owner-private
settings. The command does not create those files, choose their locations,
schedule itself or infer that a run is required.

## Remaining external work

Production use still requires environment-specific private settings,
credentials outside Git where required by infrastructure, an approved operator
decision and current durable evidence. Any timer, service, worker, alert-driven
trigger, automatic retry, bulk drain or deployment integration is a new slice
with its own authority, concurrency and incident-response review.

This audit changes no schema, migration, runtime behavior, route, provider,
secret, deployment or external system. It closes only the manual reconciliation
implementation strand.
