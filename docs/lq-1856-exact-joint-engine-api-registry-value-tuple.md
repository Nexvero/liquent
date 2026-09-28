# LQ-1856 Exact joint engine API registry value tuple

- Container runtime type must be exactly tuple.
- Empty tuple is a valid empty registry projection.
- Every populated entry has exact acceptance type.
- Tuple subclasses and iterable alternatives are not accepted.
- Entry subclasses and structural lookalikes are rejected.
- Existing acceptance validation remains authoritative.
- No new projection model is introduced.
