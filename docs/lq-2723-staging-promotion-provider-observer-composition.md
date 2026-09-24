# LQ-2723: Staging promotion provider observer composition

## Decision

LQ-2723 composes the read-only provider-observation chain implemented by
LQ-2718 through LQ-2722. A supplied HTTP client and trusted endpoint produce
one outcome observer compatible with the reconciliation boundary.

The chain is HTTP acquisition, strict decoding, closed request adaptation,
response classification, and exact durable binding. No validation layer is
bypassed.

## Observable contract

- Composition accepts one existing HTTP client and one trusted endpoint.
- Invalid wiring becomes detail-free composition unavailability.
- One observation performs at most one provider request.
- Provider absence and pending remain neutral.
- An exact committed response becomes one exact observation.
- The supplied client lifecycle remains owned by the caller.
- The observer exposes no mutation, retry, claim, or credential operation.

## Safety boundary

Composition grants no promotion authority and does not convert provider data
into authority. Every response still crosses strict transport, decoding,
operation-binding, and durable-attempt checks before reconciliation can write.

## Deliberate exclusions

LQ-2723 adds no application startup wiring, credential provisioning, scheduler,
worker, polling loop, retry, route, CLI, schema, migration, secret, or
deployment decision. Production lifecycle integration remains separate.
