# LQ-2719: Staging promotion provider response classifier

## Decision

LQ-2719 classifies transport-neutral provider responses behind the trusted
status gateway from LQ-2718. It distinguishes neutral absence or pending state
from an exact committed response without exposing transport details to the
reconciliation flow.

The requested operation identity is bound independently to every non-absent
response. A provider cannot substitute another operation through the status
surface.

## Observable contract

- The transport is called once with one valid opaque operation identity.
- Transport absence returns neutral absence.
- A matching pending response returns neutral absence.
- A matching committed response is converted to a trusted committed status.
- Substituted operation identities and unsupported response types fail closed.
- Malformed values and transport failures become detail-free unavailability.
- The classifier exposes no mutation, polling, retry, or credential surface.

## Safety boundary

Pending is not success and cannot produce a receipt. Committed classification
is not authority to promote or retry. LQ-2718 still binds all receipt fields to
the durable Unknown attempt before LQ-2712 may persist reconciliation.

The transport protocol is read-only and transport-neutral. It does not decide
URL, authentication, timeout, TLS, response decoding, or retry policy.

## Deliberate exclusions

LQ-2719 adds no HTTP client, provider mutation, polling loop, automatic retry,
scheduler, worker, route, CLI, schema, migration, credential, secret, or
deployment decision. Concrete acquisition remains a separate later slice.
