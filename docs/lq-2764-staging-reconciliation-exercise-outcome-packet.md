# LQ-2764: Staging reconciliation exercise outcome packet

## Purpose

LQ-2764 defines the minimal completion record for one bounded staging
reconciliation exercise authorized and validated through LQ-2761 to LQ-2763.
The record preserves only fixed command outcomes and the independently checked
final durable state. It is evidence of what happened in that window, not a
credential, retry request, promotion decision or deployment approval.

Create the packet after the exercise stops, including when it stops before the
reconciliation command. Do not copy command output beyond the fixed tokens.

## Copyable outcome packet

Copy this block into the approved private operational record and replace every
placeholder with exactly one allowed token:

```text
STAGING_RECONCILIATION_EXERCISE_OUTCOME
decision_validation: valid
settings_installation: installed|present|unavailable|invalid_invocation|not_run
readiness_audit: ready|unavailable|invalid_invocation|not_run
candidate_audit: pending|idle|unavailable|invalid_invocation|not_run
reconciliation: reconciled|idle|unavailable|invalid_invocation|not_run
final_candidate_state: reconciled|present|unverified
exercise_result: completed|stopped|unverified
window_closed_utc: YYYY-MM-DDTHH:MM:SSZ
```

`not_run` means the preceding stop boundary prevented that command from being
invoked. It must never be used to hide an invoked command's result.
`unverified` means the authoritative durable-state check did not complete; it
is a closed failure result, not permission to infer success.

## Recording order

Record the packet once, in this order:

1. copy the prior `valid` decision-validation result without packet values;
2. record each invoked command's exact fixed token and `not_run` for every
   later command after the first stop;
3. independently inspect the system of record for whether the exact durable
   candidate was reconciled or remains present;
4. record `unverified` if that independent inspection is unavailable or
   ambiguous;
5. close the exercise window with one UTC timestamp and mark the decision
   packet consumed.

`completed` is valid only when reconciliation reported `reconciled` and the
independent durable check reports `reconciled`. Every stop-boundary outcome is
`stopped` when the durable state is known. Any mismatch, missing fact or
unavailable final inspection is `unverified`.

## Data-minimizing and fail-closed boundary

The packet contains no settings path or value, provider endpoint, database URL,
operation identity, response body, receipt, credential, personal identity,
command line, exit code, stack trace or free-form reason. Those details remain
in their authoritative private systems.

The packet cannot authorize another command, retry, polling, a second
candidate, bulk drain, repair, cleanup, promotion, deployment or rollback.
`completed` proves only the bounded reconciliation exercise. `stopped` and
`unverified` require investigation outside this command chain. Any later pass
requires fresh evidence, a new LQ-2762 decision packet, a new separate decision
and a new LQ-2763 validation.

LQ-2764 adds documentation and tests only. It creates no command, parser,
writer, database record, route, credential, trigger, scheduler or deployment.
It does not execute the staging exercise or mutate durable state.
