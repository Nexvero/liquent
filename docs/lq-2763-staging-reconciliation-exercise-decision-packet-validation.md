# LQ-2763: Staging reconciliation exercise decision packet validation

## Purpose

LQ-2763 defines the manual validation boundary for the LQ-2762 decision packet
before one future staging reconciliation exercise. Validation answers only
whether the packet may be consulted for the named window. It does not turn the
packet into a credential, command input or reusable authorization token.

The reviewer validates a private copy of the packet immediately before the
exercise. No packet value is copied into a ticket, command line, log or
automated result.

## Validation order

Review the packet once, in this order:

1. **Shape** — the packet has exactly the twelve LQ-2762 fields, once each, in
   the documented order, with no additional field or free-form text.
2. **Tokens** — every confirmation is exactly `yes`; the decision is exactly
   `approved`, `rejected` or `expired`; timestamps use the documented UTC form.
3. **Window** — the start precedes the expiry, the decision was recorded no
   later than the expiry, and the current review time is within the same named
   window.
4. **Current evidence** — staging boundary, settings custody, provider-read
   authorization, PostgreSQL readiness and durable candidate evidence still
   refer to that window and have not been replaced, revoked or contradicted.
5. **Role separation** — the authoritative access system still shows separate
   operator and approver roles and an assigned incident-response role.
6. **Single use** — no command has already consumed the packet and no earlier
   pass, retry or later window is being attached to it.

Stop at the first failed step. Do not repair, infer, normalize or complete a
packet during validation. Any correction requires a fresh packet and a new
separate decision.

## Fixed validation result

Record exactly one of these data-minimizing results in the private operational
record:

- `valid` — all checks pass for one not-yet-started exercise in the current
  window;
- `rejected` — the packet decision is `rejected`;
- `expired` — the decision is `expired` or the window is no longer current;
- `invalid` — shape, token, timestamp, evidence, role or single-use validation
  fails.

The result contains no field values, reason detail, path, endpoint, database
detail, operation identity, personal identity, command output or secret.
`valid` is point-in-time evidence only. It does not authorize a provider
request or the next command, and each fixed command outcome remains a new stop
boundary.

## Fail-closed boundary

Only `valid` permits the authorized operator to continue consulting the
existing manual runbook for the same window. `rejected`, `expired`, `invalid`,
a missing result or an ambiguous result stops before settings installation,
provider access or reconciliation.

There is no fallback approval, packet repair, retry, polling, bulk drain,
promotion, deployment or rollback authority. A second attempt requires fresh
evidence, a new LQ-2762 packet, a new separate decision and a new validation.

LQ-2763 adds documentation and tests only. It creates no parser, validator,
command, route, database record, credential, trigger, scheduler or deployment.
It neither performs nor authorizes the real staging exercise.
