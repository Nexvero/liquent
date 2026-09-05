# LQ-623 — Separated wrapper launch mount contract

## Status

Accepted as the constructive mount contract following the completed LQ-619
engine anchor.

## Decision

One private host binding directory has two distinct children. Dynamic gate
artifacts live below `control-artifacts`; the immutable canonical input is the
single sibling file `launch-binding.json`.

Docker exposes only the artifact child at `/run/liquent/control` read-write. It
exposes only the launch file at
`/run/liquent/launch/launch-binding.json` read-only. The parent host directory is
never mounted. The same launch inode is therefore not reachable through the
read-write container capability.

Both binds are adapter-owned. No request, label, environment value, profile, or
document content selects their source suffix, destination, or access mode.

## Admission

Before create, the local client requires an absolute resolved base, a real
artifact directory, and a regular single-link bounded launch file. The launch
file must have the owner-private compatibility mode or the exact configured
owner/reader mode. Invalid or unavailable path facts fail detail-free before
daemon I/O.

Inspection accepts a container only if Docker reports the same two ordered bind
specifications. A changed source, destination, mode, missing bind, or extra bind
is technical unavailability and cannot be adopted.

## Scope

This contract adds no path request, port, schema, migration, settings, Compose,
entrypoint, or production activation. LQ-624 implements the closed mount layout.
