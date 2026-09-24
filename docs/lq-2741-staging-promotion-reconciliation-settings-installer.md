# LQ-2741: Staging promotion reconciliation settings installer

## Implementation

LQ-2741 implements the LQ-2740 installation contract as a transport-layer
function. It accepts exactly four explicit `Path` values and returns only
`INSTALLED` or neutral `PRESENT`; every other failure is detail-free technical
unavailability.

Both sources are read once through non-following, non-inheritable descriptors.
Metadata and size are checked before and after the bounded read. The exact
provider and process projections are then delegated to the existing settings
value validators, and the process provider path must equal the supplied
provider target.

## Publication

Target parents are opened as owner-held directories that are not writable by
group or others. Each target is written to a random owner-private temporary
file, synchronized and hard-linked to its final name without replacement. The
temporary link is removed and the directory is synchronized before the next
stage.

Provider publication occurs first. Process publication occurs last and is the
activation record. Failure during process publication can retain only a
complete private inert provider target; it never exposes a process target that
references an unpublished provider file.

## Boundary

The installer creates no directory, settings value, credential or authority.
It does not open a database connection, create a provider client, perform a
network request, migrate schema or invoke reconciliation. LQ-2741 adds no CLI,
entry point, shell wrapper, default path, environment lookup, retry, cleanup,
rotation, service, timer, worker, route or deployment wiring.

Presentation and operator invocation remain separate.
