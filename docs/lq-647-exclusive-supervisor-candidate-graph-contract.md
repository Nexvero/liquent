# LQ-647 — Exclusive supervisor candidate graph contract

## Status

Accepted as the composition contract for one complete currently available,
unselected supervisor candidate.

## Required graph

The parent side contains the persistent launch prefix, direct Ready completion,
observation-only Release, and read-only crash reconciliation. The child side
contains the anchored launch loader, file-backed gate wrapper, and exactly one
profile-specific capability executor.

Both sides share the same canonical artifact codec and bound control-artifact
store. The parent observer reads child artifacts; it never receives the child's
executor. The child receives no journal, runtime registry, database, engine, or
parent service.

## Exclusivity

The candidate imports neither compatibility Prepare nor compatibility Release.
It has no fallback to the existing aggregate service. Exactly one constructor
argument is an execution capability, named for and passed only to the child.

The parent may publish the Release token through its observation-only Release
service. No parent component may publish Ready, Consumed, or Terminal or execute
Writer/Recovery capability work.

## Incomplete terminal boundary

Direct parent Terminal observation/persistence has not yet replaced the old
terminal compatibility service. The candidate must expose this fact as immutable
`false` and must likewise expose Production readiness as immutable `false`.

No settings or caller may override these facts. LQ-648 implements the inert
candidate bundle.
