# LQ-2720: Staging promotion provider acquisition request

## Decision

LQ-2720 introduces a closed request object for one provider-status acquisition.
It converts the opaque operation identity accepted by LQ-2719 into a typed,
immutable request before any concrete transport can run.

The adapter invokes one acquisition exactly once and accepts only the explicit
pending, committed, or absent response forms already defined by the classifier.

## Observable contract

- One valid opaque operation identity creates one immutable request.
- The request hides its operation identity from representation.
- The acquisition receives the request exactly once.
- Neutral absence passes through unchanged.
- Only pending or committed provider-response values may pass through.
- Malformed identities never reach acquisition.
- Unsupported response values and acquisition failures become detail-free
  unavailability.
- No URL, method, credential, retry, or timeout is caller supplied here.

## Safety boundary

The request is a read instruction, not authority to promote or retry. It
contains no actor role, success flag, receipt, target override, credential, or
provider mutation data. LQ-2719 and LQ-2718 still perform independent response
and exact-binding validation.

## Deliberate exclusions

LQ-2720 adds no HTTP implementation, endpoint path, authentication, credential
loader, timeout, redirect, polling loop, automatic retry, scheduler, worker,
route, CLI, schema, migration, secret, or deployment decision. Concrete
acquisition remains a separate later slice.
