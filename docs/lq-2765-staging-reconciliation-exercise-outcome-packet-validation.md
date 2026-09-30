# LQ-2765: Staging reconciliation exercise outcome packet validation

## Purpose

LQ-2765 defines the manual validation boundary for one completed LQ-2764
outcome packet. The validation confirms that the bounded staging reconciliation
exercise was recorded consistently and closed. It does not turn the outcome
packet into a credential, retry request, promotion decision or deployment
approval.

Validate the packet once after the exercise window is closed and before it is
used as completion evidence. No packet value is copied into a ticket, command
line, log or validation result.

## Ordered validation

Perform these checks in order and stop at the first failed step:

1. **Shape** — the packet has exactly the eight LQ-2764 fields, once each, in
   the published order, with no additional field or free-form text;
2. **Tokens** — every field contains exactly one published fixed token and the
   closing timestamp is a complete UTC timestamp;
3. **Command sequence** — after the first stop-boundary result, every later
   command is `not_run`; `not_run` never replaces an invoked command result;
4. **Durable evidence** — `final_candidate_state` came from a separate,
   authoritative system-of-record inspection performed after the command
   sequence;
5. **Result consistency** — `completed` appears only with `reconciled` from
   both reconciliation and the independent durable-state inspection;
   known non-completion is `stopped`, while any mismatch, missing fact or
   unavailable inspection is `unverified`;
6. **Closure** — the exercise window is closed and the LQ-2762 decision packet
   is recorded as consumed, including when the exercise stopped early.

Do not repair, infer, normalize or complete an outcome packet during
validation. Do not re-run a command to make the packet pass. A failed check
preserves the original private evidence and produces only a fixed validation
result.

## Fixed validation result

Record exactly one token in the approved private operational record:

```text
STAGING_RECONCILIATION_EXERCISE_OUTCOME_VALIDATION
result: valid|invalid|unverified
```

- `valid` means all six ordered checks passed;
- `invalid` means the packet shape, tokens, sequence, consistency or closure
  failed;
- `unverified` means the authoritative durable-state or consumption evidence
  could not be checked.

The validation result contains no packet value, reason detail, path, endpoint,
database URL, operation identity, response, receipt, credential, personal
identity, command line, exit code or stack trace. Detailed evidence remains in
its authoritative private system.

## Fail-closed boundary

`valid` is completion evidence for the already-finished bounded exercise only.
It grants no authority for another command, retry, polling, second candidate,
bulk drain, repair, cleanup, promotion, deployment or rollback. `invalid`,
`unverified`, a missing result or an ambiguous result remains closed and
requires investigation outside this command chain.

There is no fallback success, packet repair, automatic retry or result
normalization. A later exercise requires fresh evidence, a new LQ-2762 decision
packet, a new separate decision and a new LQ-2763 validation. The prior outcome
packet and its validation remain immutable evidence of the prior window.

LQ-2765 adds documentation and tests only. It creates no parser, validator,
command, writer, database record, route, credential, trigger, scheduler or
deployment. It neither executes nor authorizes a staging reconciliation
exercise and mutates no durable state.
