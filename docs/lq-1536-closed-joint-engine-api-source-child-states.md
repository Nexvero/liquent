# LQ-1536 Closed joint engine API source child states

- Observation construction checks all fourteen child states.
- Directory state cannot masquerade as a source file.
- Permissive mode and foreign ownership fail.
- Hard-linked, empty, and oversized state fail.
- Positional limits remain those used by descriptor reads.
- A single invalid child rejects the whole value.
- Existing capture logic needs no caller input.
