# LQ-2726: Settings-backed staging promotion provider composition

## Decision

LQ-2726 joins the explicit LQ-2725 settings source to the LQ-2723 provider
observer composition. A caller supplies one existing HTTP client and one
absolute settings path; composition loads settings once and returns the
read-only observer.

## Observable contract

- Settings are loaded exactly once during composition.
- The validated endpoint is passed through the existing LQ-2723 chain.
- Composition itself performs no provider request.
- A later observation performs at most the one request allowed by LQ-2723.
- Settings and wiring failures become detail-free composition unavailability.
- The caller retains ownership of the HTTP client lifecycle.

## Safety boundary

Joining configuration to the observer grants no promotion authority and does
not weaken any provider-response validation. The settings file is not watched
or reloaded, and deleting it after composition does not alter the observer.

## Deliberate exclusions

LQ-2726 adds no client construction, startup hook, default path, environment
lookup, credential, secret, mutation, scheduler, worker, polling loop, retry,
route, CLI, schema, migration, or deployment decision. Runtime lifecycle wiring
remains separate.
