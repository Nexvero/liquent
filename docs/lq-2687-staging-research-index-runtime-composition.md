# LQ-2687 — Staging Research-index runtime composition

## Outcome

This slice connects the persistent LQ-2686 fixture control and the existing
bounded staging HTTP acquisition to the controlled LQ-2685 execution.

One externally owned database engine and one externally owned HTTP client are
accepted at construction. Composition performs neither database nor network
I/O. It starts no process and assumes no ownership of either resource.

## Explicit execution

The returned capability executes only when called with a validated acceptance
run, explicit evidence path, opaque fixture handle, expected active revision,
and the exact per-stage opaque session inventory. Those values are passed to
the existing controlled execution without reinterpretation.

The same persistent controller is used for revocation and restoration. The
same bounded HTTP acquisition is used for every planned request. This avoids a
second authority path, mutation path, or HTTP implementation.

The runtime stores no session inventory, reads no environment variable or
secret file, and exposes no credential-loading capability. Its representation
contains neither client details nor fixture-control material.

## Exclusions

LQ-2687 adds no schema, migration, fixture provisioning, credential source,
login automation, CLI, scheduler, retry, deployment, or promotion. A controlled
operator and explicit secure session handoff remain separate.
