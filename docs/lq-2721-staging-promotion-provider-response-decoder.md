# LQ-2721: Staging promotion provider response decoder

## Decision

LQ-2721 strictly decodes one bounded raw provider response into the explicit
absent, pending, or committed values consumed by LQ-2720. The decoder does not
own networking and receives only status, headers, and bounded raw bytes.

## Observable contract

- A bodyless 404 is neutral absence.
- A 202 JSON response must contain exactly matching operation and `pending`.
- A 200 JSON response must contain the exact committed field set.
- Every non-absent response must use exact `application/json` content type.
- Bodies larger than 16 KiB, duplicate keys, invalid UTF-8, invalid JSON,
  extra fields, substituted operations, and unsupported statuses fail closed.
- Committed observation time must decode as an aware timestamp downstream.
- Raw acquisition failures become detail-free unavailability.

## Safety boundary

Decoding does not establish authority or initiate promotion. Pending remains
non-success. Committed values still pass through LQ-2719 and LQ-2718 for
operation and durable-attempt binding before they can be recorded.

## Deliberate exclusions

LQ-2721 adds no HTTP client, endpoint, authentication, decompression, redirect,
retry, polling loop, scheduler, worker, route, CLI, schema, migration, secret,
or deployment decision. Bounded raw HTTP acquisition remains separate.
