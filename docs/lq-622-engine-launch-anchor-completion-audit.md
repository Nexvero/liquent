# LQ-622 — Engine launch anchor completion audit

## Status

LQ-619 through LQ-622 are complete as one isolated launch-anchor strand.

## Audit result

The engine's observable create, acknowledgement, and observation contract now
binds one container to the immutable identity and canonical SHA-256 of one launch
document. Prepare compares that pair on initial and post-start observations.

The local Docker boundary materializes and decodes exactly six owned labels.
Retry adopts only a complete match; document or digest divergence is a
non-creating conflict. Malformed or technically unavailable observations remain
closed and detail-free through the existing error boundary.

Focused regression covers model validation, HTTP translation, adapter adoption,
divergence, service contracts, persistence composition, and numeric launch
identity behavior: 83 tests pass. The strict full regression passes with 5,225
tests and 108 environment-dependent skips under the DeprecationWarning error
boundary.

## Unchanged boundaries

No schema, migration, SQL, port, command, mount, loader, settings, application
factory, Compose, deployment, release, or production activation changed. Digest
calculation still belongs to the canonical launch-document publication flow.

The next strand may bind the already-published launch file into the wrapper's
read-only container view and loader, while preserving the completed anchor.
