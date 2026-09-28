# LQ-619 — Engine launch document anchor contract

## Status

Accepted as the closed contract for binding one supervisor container to one
already-published launch document.

## Decision

An engine create request carries the launch document's opaque control-artifact
identifier and the lowercase hexadecimal SHA-256 of its canonical bytes.
Both values are immutable correlation facts, not caller authority.

The digest is exactly 64 lowercase hexadecimal characters. It has no `sha256:`
prefix and is excluded from representations. The document identifier remains an
existing control-artifact identifier; this slice creates no second identifier
namespace.

Create acknowledgement and every container observation repeat both facts. A
consumer therefore need not infer the launch input from a creation identifier,
container name, filesystem path, image, profile, or current file contents.

## Reconciliation

The creation identifier remains the bounded lookup key. Adoption is permitted
only when the single found container matches the complete expected binding,
including launch document identifier and digest. Missing, malformed, duplicate,
or divergent facts fail closed. Divergence is a neutral engine conflict and must
not trigger a second create.

Later inspect, start, wait, and terminate observations are accepted only when the
same structurally valid launch anchor is present. Technical inability to inspect
or decode remains detail-free unavailability through the existing boundary.

## Scope boundary

No launch-document publication, loader, mount, command, schema, migration,
settings, application-factory, Compose, deployment, or production activation is
introduced here. LQ-620 implements the closed adapter binding.
