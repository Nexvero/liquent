# LQ-2722: Staging promotion provider HTTP acquisition

## Decision

LQ-2722 performs one bounded HTTP GET for one closed provider-status request.
The endpoint prefix is trusted wiring configuration and must be an HTTPS URL
without user information, query, fragment, or an incomplete path boundary.

## Observable contract

- One request produces exactly one GET to endpoint prefix plus operation ID.
- Redirects, client authentication, and retries are disabled.
- Inherited Authorization and Cookie headers are removed.
- The request accepts JSON and requires identity encoding.
- Fixed five-second timeouts apply.
- Declared and streamed bodies are limited to 16 KiB.
- Compressed, malformed-length, oversized, or failed responses become
  detail-free unavailability.
- Status, headers, and bounded raw bytes pass immediately to LQ-2721.

## Safety boundary

HTTP acquisition is read-only and grants no promotion authority. The adapter
has no credential, mutation, retry, polling, or response-acceptance surface.
Provider content remains untrusted until decoded and fully bound downstream.

## Deliberate exclusions

LQ-2722 adds no credential loader, authenticated provider protocol, retry,
polling loop, scheduler, worker, route, CLI, schema, migration, secret, or
deployment wiring. Provider endpoint provisioning remains separate.
