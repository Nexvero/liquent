# LQ-620 — Engine launch document anchor binding

## Status

Implemented in the closed supervisor engine model, prepare service, local Docker
adapter, and bounded local Docker HTTP client.

## Implementation

Create requests, acknowledgements, and observations now carry a validated launch
document identifier and digest. Prepare passes its expected pair into create and
requires the observed pair on every reconciliation before release can proceed.

The Docker adapter owns exactly these six labels:

- `liquent.supervisor.creation`
- `liquent.supervisor.handle`
- `liquent.supervisor.control`
- `liquent.supervisor.launch-document`
- `liquent.supervisor.launch-sha256`
- `liquent.supervisor.profile`

The HTTP client accepts exactly that label set when creating or decoding a
container. Unknown, absent, empty, malformed, or duplicated semantic input is not
normalized. The adapter reconstructs typed facts from inspected labels and
compares the complete label map before adopting an existing container.

## Failure behavior

A valid container with another launch identifier or digest is a reconciliation
conflict. Malformed daemon observations and transport failures remain existing
detail-free technical unavailability. Neither case issues a replacement create.

## Scope boundary

This slice does not calculate or publish the digest, alter the launch file,
choose images or commands, add a mount, or activate production wiring. LQ-621
provides executable retry and divergence evidence.
