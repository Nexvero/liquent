# LQ-2727: Owned staging promotion provider lifecycle

## Decision

LQ-2727 owns one HTTP client for the LQ-2726 settings-backed observer. The
client ignores ambient proxy and certificate environment configuration, does
not follow redirects, and is closed deterministically by the lifecycle bundle.

## Observable contract

- Composition creates exactly one client and one observer.
- Client construction sets `trust_env` and redirect following to false.
- Composition performs no provider request.
- The lifecycle exposes the read-only observer and deterministic close.
- Context exit closes the client; repeated close is neutral.
- A closed lifecycle cannot be entered again.
- Failed composition closes any client already created.
- Lifecycle failures become detail-free unavailability.

## Safety boundary

Owning transport lifetime grants no promotion authority. All requests and
responses still cross LQ-2722 through LQ-2726, and the bundle exposes no
mutation, claim, credential, retry, reload, or polling operation.

## Deliberate exclusions

LQ-2727 adds no startup hook, global singleton, dependency container, trigger,
scheduler, worker, polling loop, route, CLI, credential, secret, schema,
migration, or deployment decision. Application lifecycle wiring remains
separate.
