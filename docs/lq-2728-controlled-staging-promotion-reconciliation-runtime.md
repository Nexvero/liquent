# LQ-2728: Controlled staging promotion reconciliation runtime

## Decision

LQ-2728 binds the owned LQ-2727 provider lifecycle to the LQ-2717 controlled
single-operation reconciliation. A caller explicitly invokes `execute_one`;
the runtime never starts or repeats work by itself.

## Observable contract

- Composition owns one provider lifecycle and caller-supplied persistence ports.
- `execute_one` selects and reconciles at most one unknown operation.
- An empty index returns neutral absence without provider access.
- A committed provider result is recorded only through the existing recorder.
- Execution and composition failures become detail-free runtime unavailability.
- Closing the runtime closes the provider client and is terminal.
- Context exit closes the runtime deterministically.

## Safety boundary

The runtime does not claim candidates, grant promotion authority, initiate a
promotion, or infer success. Provider evidence still crosses every binding and
validation boundary before the supplied recorder may finalize an outcome.

## Deliberate exclusions

LQ-2728 adds no loop, scheduler, worker, polling, retry, timer, concurrency,
startup hook, route, CLI, credential, secret, schema, migration, or deployment
decision. Triggering and concrete persistence wiring remain separate.
