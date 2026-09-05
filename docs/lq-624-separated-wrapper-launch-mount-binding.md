# LQ-624 — Separated wrapper launch mount binding

## Status

Implemented in the bounded local Docker HTTP client.

## Implementation

The existing control-directory resolver identifies one process-owned host base.
The client derives only `control-artifacts` and `launch-binding.json`. It emits
exactly two bind specifications:

- dynamic artifacts to `/run/liquent/control` with `rw`;
- the canonical launch file to
  `/run/liquent/launch/launch-binding.json` with `ro`.

Create validates source type, launch size, single-link status, expected file
mode, and—when the numeric policy is active—owner UID and reader GID. Colons and
newlines cannot enter a bind source.

Inspect independently reconstructs the expected paths from the typed directory
label and requires Docker's bind list to match exactly. Adoption therefore
preserves both the completed six-label anchor and this mount capability profile.

## Boundary

The client does not create directories, publish launch bytes, change ownership,
or repair modes. It performs no fallback mount. Wrapper consumption remains
closed until LQ-625.
