# LQ-2724: Staging promotion provider endpoint settings

## Decision

LQ-2724 defines one closed settings value for the provider status endpoint used
by the LQ-2723 observer composition. Settings are built only from a complete
mapping containing exactly one endpoint; there is no implicit default.

## Observable contract

- The mapping contains exactly the `endpoint` key and one string value.
- The endpoint is HTTPS, bounded, and ends at a path boundary.
- User information, query, fragment, missing slash, extra keys, and non-string
  values fail closed.
- The endpoint is hidden from representation.
- Invalid settings become detail-free unavailability.
- Settings carry no credential, authority, retry, or mutation capability.

## Safety boundary

An endpoint is routing configuration, not trust in response content and not
promotion authority. Every acquired response still crosses all LQ-2718 through
LQ-2723 checks. The endpoint cannot embed credentials.

## Deliberate exclusions

LQ-2724 adds no environment-variable name, file source, secret, credential,
default endpoint, startup wiring, scheduler, worker, retry, route, CLI, schema,
migration, or deployment decision. Settings sourcing remains separate.
