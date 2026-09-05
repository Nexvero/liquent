# LQ-2181 sdist PAX metadata gate

- Unknown PAX keys are not copied into normalized output.
- A path key is accepted only when it exactly equals the member name.
- Long canonical names therefore remain representable without aliases.
- Source mtime is finite, nonnegative, bounded, and then discarded.
- Comments, ownership, and extended attributes are rejected.
- Normalization clears all accepted input PAX metadata before emission.
- Tar generation may recreate only the required canonical path record.
- No caller-controlled metadata becomes release authority.
