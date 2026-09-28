# LQ-2256 shared canonical sdist TAR renderer

- Normalization and verification use one deterministic TAR renderer.
- Entries are ordered by their validated POSIX member names.
- Identity names are empty and numeric owner identifiers are zero.
- Every member receives the requested SOURCE_DATE_EPOCH.
- Incoming PAX headers are cleared before required fields are regenerated.
- Existing modes, types, sizes, and payload bytes remain bound.
- Rendering is in memory and performs no archive extraction.
