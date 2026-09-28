# LQ-625 — Anchored wrapper launch loader

## Status

Implemented as a closed read-only loader with no Ready or capability effect.

## Input binding

The loader receives one typed expectation containing document ID, canonical
SHA-256, creation ID, handle ID, control-directory ID, image digest, and profile.
These facts represent immutable create configuration; they are not read from the
launch document, caller booleans, roles, environment variables, or filenames.

The loader opens the process-owned launch root and fixed
`launch-binding.json` using no-follow descriptors. It requires a regular,
single-link, non-empty file no larger than 65,536 bytes with exact host-owner,
reader-group, and `0640` facts.

It performs a bounded full read, compares SHA-256 before decode, applies the
canonical duplicate-key and byte-roundtrip codec, and compares every external
self-binding field. Any mismatch or technical problem produces only the existing
detail-free unavailability.

## Evidence

Tests prove exact acceptance, digest divergence, document and handle divergence,
unsafe modes, symlink and hardlink rejection, exact mount generation, and exact
mount inspection. No case publishes Ready, consumes Release, executes a
capability, mutates a file, or performs Docker/network/database I/O.

LQ-626 closes the strand with full regression and unchanged-boundary audit.
