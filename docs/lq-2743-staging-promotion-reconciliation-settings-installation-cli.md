# LQ-2743: Staging promotion reconciliation settings installation CLI

## Implementation

LQ-2743 implements the LQ-2742 presentation contract as a minimal transport
module. `run` accepts exactly four path strings and delegates one validated
tuple of `Path` values to the LQ-2741 installer.

Invalid arity, non-string values, relative paths, root paths and parent
traversal are rejected before delegation. The command performs no path
discovery and reads no environment variable.

## Fixed presentation

- `INSTALLED` emits only `installed` on stdout and returns zero.
- Neutral `PRESENT` emits only `present` on stderr and returns three.
- Every technical failure and unknown outcome emits only `unavailable` on
  stderr and returns one.
- Invalid invocation emits only `invalid_invocation` on stderr and returns two.

The module never presents source content, a supplied path, endpoint, database
URL, metadata or exception detail. `main` passes the four command-line values
to the same closed `run` boundary and exits with its status.

## Boundary

The CLI performs one installation attempt only. It grants no authority, does
not compare an existing target, and does not start reconciliation. It adds no
retry, loop, cleanup, rotation, network, database, schema, migration or
deployment behavior.

LQ-2743 adds no installed entry point or packaging change. Installation of the
command remains a separate slice.
