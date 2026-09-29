# LQ-2762: Staging reconciliation exercise decision packet

## Purpose

LQ-2762 turns the LQ-2761 authorization handoff into a small, copyable record
for one future staging reconciliation exercise. The record lets a separate
approver accept, reject or expire one bounded exercise without copying private
settings, provider data, database details or an operation identity.

The packet is evidence of a decision only. It is not a credential, reusable
authorization token, command file or executable procedure. An `approved`
decision applies only to the named exercise window and expires before any later
invocation.

## Copyable packet

Copy the following block into the approved private operational record and
replace every placeholder. Do not add technical values or free-form failure
details.

```text
STAGING_RECONCILIATION_EXERCISE_DECISION
environment_boundary_confirmed: yes|no
settings_custody_confirmed: yes|no
provider_read_authorized: yes|no
postgresql_readiness_confirmed: yes|no
durable_candidate_confirmed: yes|no
operator_role_assigned: yes|no
approver_role_assigned: yes|no
incident_response_role_assigned: yes|no
window_start_utc: YYYY-MM-DDTHH:MM:SSZ
window_expires_utc: YYYY-MM-DDTHH:MM:SSZ
decision: approved|rejected|expired
decision_recorded_utc: YYYY-MM-DDTHH:MM:SSZ
```

The packet deliberately uses role assignments instead of names, accounts or
contact details. The authoritative access system remains the source for the
actual people and permissions.

## Validation rules

The packet is complete only when:

1. every confirmation is exactly `yes`;
2. the environment is the approved staging boundary, never production or a
   different tenant;
3. the window start, expiry and decision time are UTC timestamps;
4. the expiry is later than the start and the decision is recorded before the
   expiry;
5. `approved` is recorded by a separate approver immediately before the
   bounded exercise;
6. current readiness and candidate evidence still match the same window; and
7. no required fact is missing, stale, ambiguous or contradicted.

Any `no`, missing field, invalid timestamp, expired window, stale prerequisite
or decision other than `approved` stops the exercise before settings
installation, provider access or reconciliation. There is no implied approval
and no fail-open default.

## Forbidden material

The packet must not contain:

- a settings path or value;
- provider endpoint, response, receipt or error detail;
- database URL, host, schema revision or credential;
- operation identity or durable-record payload;
- personal name, account, email address or contact detail;
- command output, stack trace, token or secret.

Keep those facts in their authoritative private systems. The decision packet
records only confirmations, role assignment flags, the bounded UTC window and
the fixed decision token.

## Consumption boundary

An authorized operator may consult one valid `approved` packet before following
the existing manual command order in `operations/runbooks/staging-promotion.md`.
Each command result remains a new stop boundary. The packet cannot authorize a
retry, second candidate, polling, bulk drain, promotion, deployment or rollback.

After the window expires or one bounded pass finishes, record `expired` for any
later use. A new pass requires a new packet built from fresh readiness and
candidate evidence and a new separate decision.

LQ-2762 adds documentation and tests only. It creates no parser, command,
credential, database record, route, service, trigger, scheduler or deployment.
It neither performs nor authorizes the real staging exercise.
