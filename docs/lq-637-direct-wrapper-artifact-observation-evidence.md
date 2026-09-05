# LQ-637 — Direct wrapper artifact observation evidence

## Status

Implemented as focused executable evidence over the real canonical artifact
codec and real domain gate values.

## Evidence

Tests prove exact direct Ready and Consumed decoding, gate-owned IDs, role order,
handle and Release correlations, and preservation of the encoded SHA-256 and byte
count in persistence commands.

Absent roles return `None` and produce zero persistence calls. A canonical
document with a different handle fails detail-free before persistence. Existing
persistent conflict is returned without reinterpretation.

A source-surface guard confirms that the new components contain no control-file
publish, Writer/Recovery execute, engine call, session, permission, allow flag,
or subprocess capability.

Focused coverage retains the canonical file adapter, gate wrapper, and existing
Prepare/Release compatibility contracts. No database, Docker, network,
migration, CLI, or deployment is used.

LQ-638 closes the prerequisite observation strand.
