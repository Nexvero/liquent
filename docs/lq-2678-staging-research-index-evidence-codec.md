# LQ-2678 — Staging Research-index evidence codec

## Outcome

This slice defines one canonical bounded evidence representation for the three
sanitized, run-bound stage handoffs established by LQ-2677.

## Canonical representation

The codec emits compact sorted ASCII JSON followed by exactly one newline. The
document carries one version, candidate digest, staging origin, UTC observation
time, derived acceptance outcome, and the three stages in canonical order. Each
stage contains only its name and canonically ordered sanitized check, phase, and
outcome triples.

Encoding first performs the existing complete handoff evaluation. Caller order
therefore has no authority over the resulting bytes. Decoding reconstructs the
closed domain types, repeats handoff validation and final evaluation, and
requires byte-for-byte canonical re-encoding. The recorded final outcome is a
derived cross-check and cannot override the recomputed result.

## Closed rejection

Evidence is rejected when it is empty, oversized, non-ASCII, malformed,
noncanonical, version-unknown, field-extended, incomplete, duplicated, wrongly
phased, cross-run, or inconsistent with its recomputed outcome. Rejection does
not expose parser, transport, response, credential, provider, or operator
detail through a successful evidence value.

## Security boundary

The evidence contains no session, cookie, authorization header, credential,
response body, response header, user identity, workspace identity, membership,
role, capability, diagnostic, request URL, or mutable operator state. It grants
no authority and does not prove that a mutation or deployment occurred.

The codec performs no file access, network access, credential lookup,
revocation, restore, persistence, deployment, or promotion. Owner-private file
creation and reading remain requirements of a later boundary; this slice does
not choose paths, permissions APIs, retention, signing, or storage layout.

## Next slice

A later slice may add an owner-private, no-replace evidence writer around these
canonical bytes. Real staging execution and promotion remain separate.

## Architecture correction

The full-suite verification also moved the opaque session value type to the
application acquisition boundary. The transport adapter now depends inward on
that type; staged application coordination no longer imports transport code.
