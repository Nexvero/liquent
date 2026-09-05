# LQ-2337 Candidate artifact-size binding gate

- Candidate facts bind the measured byte sizes of the sealed bundle and the
  canonical verification-evidence file.
- Both sizes are included in the canonical bytes hashed as candidate identity.
- A size change therefore changes or invalidates the descriptor even when other
  identifying facts remain unchanged.
- Inventory checking independently requires those current file sizes.
- No inferred, rounded, or caller-supplied size is authoritative.
