# LQ-643 — Parent launch prefix contract

## Status

Accepted as the parent-owned prefix preceding direct wrapper Ready observation.

## Owned transitions

The prefix may register the exact Writer or Recovery job, commit its stable launch
identity, resolve or create one digest-bound container, persist its runtime
binding, persist the immutable gate binding, start a newly created container, and
observe that same container as running.

Registration and launch commitment precede every engine operation. Create carries
the complete launch document ID and SHA-256. Runtime and gate persistence precede
start. Retry resolves existing persistent and engine facts before any create or
start.

## Stop boundary

The prefix ends at a typed result containing journal, runtime, gate, and direct
running observation. It does not publish, read, decode, or persist Ready. It does
not advance `prepared_gated`.

It has no Release, Consumed, capability executor, Terminal, termination, cleanup,
or authority method. Running is process state only and never substitutes for
Ready.

## Candidate composition

Only an exact successful prefix result may call the LQ-640 direct Ready
completion. Neutral absence and closed conflict return without completion.

No current application composition is replaced. LQ-644 implements the extracted
prefix and typed result.
