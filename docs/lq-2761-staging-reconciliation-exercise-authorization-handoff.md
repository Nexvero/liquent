# LQ-2761: Staging reconciliation exercise authorization handoff

## Purpose

LQ-2761 turns the closed LQ-2760 acceptance evidence into a bounded handoff for
one future staging reconciliation exercise. The handoff lets an approver decide
whether the real environment is ready without copying private settings,
provider data, database details or an operation identity into a ticket or log.

This document is a decision checklist, not an approval record, reusable
authorization token or executable procedure. Completing it does not authorize
settings installation, a provider request, reconciliation, promotion,
deployment or retry.

## Required decision packet

Immediately before the exercise, an authorized operator and a separate
approver must review all of these facts together:

1. **Exact staging boundary** — the intended environment is the approved
   staging instance and not production or another tenant.
2. **Owner-private settings custody** — the provider and process settings are
   held under the runbook's owner-only file rules; their paths and values stay
   outside copied evidence.
3. **Current provider authorization** — the provider-status read is authorized
   for the exact staging boundary and exercise window, without granting any
   provider mutation.
4. **Current PostgreSQL readiness** — the selected database is available,
   migrated to the expected revision and approved for this staging exercise.
5. **Current durable state** — an eligible unknown-effect candidate is still
   present and requires manual reconciliation.
6. **Named decision roles** — the operator, approver and incident-response role
   are assigned through the environment's normal access controls.
7. **Bounded exercise window** — the start, expiry and stop owner are fixed
   before any command is invoked.

The packet records only `approved`, `rejected` or `expired` for the decision.
It must not contain settings paths or values, endpoint, database URL,
credentials, operation identity, provider response, receipt or technical error
detail. Approval expires before any later run and cannot be reused.

## Authorized command boundary

Only a separately approved exercise may follow the manual order already fixed
by `operations/runbooks/staging-promotion.md`:

1. `liquent-staging-promotion-reconciliation-settings-install`
2. `liquent-staging-promotion-reconciliation-readiness-audit`
3. `liquent-staging-promotion-reconciliation-candidate-audit`
4. `liquent-staging-promotion-reconcile`

Each result is a new stop boundary. `present`, `unavailable`,
`invalid_invocation` or `idle` never authorizes the next command. `ready` and
`pending` are point-in-time prerequisite evidence only. The reconciliation
command may run once only after a fresh approved decision that follows the
current `pending` result.

## Stop and expiry rules

Stop without a provider request or reconciliation when any required fact is
missing, stale, ambiguous, rejected or expired. Stop on settings tamper,
database unavailability, schema mismatch, provider failure or an unexpected
command result. Preserve the durable unknown-effect candidate and investigate
outside the command chain.

There is no automatic retry, loop, polling, bulk drain, repair, cleanup,
promotion, deployment or rollback decision in this handoff. A second attempt
requires fresh readiness and candidate evidence plus a new explicit operator
decision and approval.

## Completion evidence

After one approved pass, record only the exercise window, decision roles,
fixed command outcomes and whether the durable candidate remains present or
was reconciled. Verify the final durable state through the system of record.
Do not infer deployment success, release readiness or production authority from
`reconciled`.

LQ-2761 adds documentation and tests only. It changes no production code,
schema, migration, command, route, settings, credential, trigger, scheduler,
service or deployment. It prepares a reviewable handoff but deliberately does
not perform or authorize the real staging exercise.
